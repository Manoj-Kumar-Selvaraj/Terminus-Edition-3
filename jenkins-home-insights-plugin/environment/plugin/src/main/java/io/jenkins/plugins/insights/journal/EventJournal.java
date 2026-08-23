package io.jenkins.plugins.insights.journal;

import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.Event;
import io.jenkins.plugins.insights.model.Domain.EventOperation;
import io.jenkins.plugins.insights.model.Domain.SourceKind;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.Closeable;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

/** Append-only checksummed event hints plus bounded listener ingress. */
public final class EventJournal implements Closeable {
    public enum AppendStatus { APPENDED, DUPLICATE, CONFLICT, CLOSED }
    public record AppendResult(AppendStatus status, long sequence, String message) {}
    public record Recovery(List<Event> events, long lastGoodSequence, boolean tornTail,
                           List<String> diagnostics) {}

    private final Path path;
    private final FileChannel channel;
    private final Map<String, String> identities = new HashMap<>();
    private final AtomicLong nextSequence;
    private final AtomicBoolean closed = new AtomicBoolean();

    public EventJournal(Path stateDirectory) throws IOException {
        Files.createDirectories(stateDirectory.resolve("journal"));
        this.path = stateDirectory.resolve("journal/events.ndjson");
        Recovery recovery = recover(path, 0);
        for (Event event : recovery.events()) identities.put(event.eventId(), event.payloadHash());
        nextSequence = new AtomicLong(recovery.lastGoodSequence() + 1);
        channel = FileChannel.open(path, StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.APPEND);
    }

    public synchronized AppendResult append(String eventId, SourceKind source, EventOperation operation,
                                            String recordKey, Map<String, Object> payload) throws IOException {
        if (closed.get()) return new AppendResult(AppendStatus.CLOSED, -1, "journal is closed");
        String payloadJson = Json.write(payload); String hash = Domain.sha256(payloadJson);
        String existing = identities.get(eventId);
        if (existing != null) return new AppendResult(AppendStatus.DUPLICATE, -1, "event identity already represented");
        long sequence = nextSequence.getAndIncrement();
        Event event = new Event(sequence, eventId, source, operation, recordKey, hash, payload);
        Map<String, Object> envelope = new LinkedHashMap<>(event.toMap());
        envelope.put("checksum", Domain.sha256(Json.write(event.toMap())));
        byte[] bytes = (Json.write(envelope) + "\n").getBytes(StandardCharsets.UTF_8);
        identities.put(eventId, hash);
        channel.write(ByteBuffer.wrap(bytes));
        if (sequence % 32 == 0) channel.force(true);
        return new AppendResult(AppendStatus.APPENDED, sequence, "accepted");
    }

    public synchronized void flush() throws IOException { if (!closed.get()) channel.force(true); }
    public Path path() { return path; }
    public long nextSequence() { return nextSequence.get(); }

    @Override public synchronized void close() throws IOException {
        if (closed.compareAndSet(false, true)) { channel.force(true); channel.close(); }
    }

    public static Recovery recover(Path path, long afterSequence) throws IOException {
        if (!Files.exists(path)) return new Recovery(List.of(), 0, false, List.of());
        List<Event> events = new ArrayList<>(); List<String> diagnostics = new ArrayList<>();
        long last = 0; boolean torn = false;
        try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            String line; long lineNumber = 0;
            while ((line = reader.readLine()) != null) {
                lineNumber++; if (line.isBlank()) continue;
                try {
                    Map<String, Object> envelope = parseLine(line);
                    String checksum = text(envelope, "checksum");
                    Map<String, Object> eventMap = new LinkedHashMap<>(envelope); eventMap.remove("checksum");
                    if (!Domain.sha256(Json.write(eventMap)).equals(checksum)) throw new IOException("checksum mismatch");
                    Event event = event(eventMap); last = Math.max(last, event.sequence());
                    if (event.sequence() >= afterSequence) events.add(event);
                } catch (RuntimeException | IOException invalid) {
                    torn = true; diagnostics.add("journal stopped at line " + lineNumber + ": " + invalid.getMessage()); break;
                }
            }
        }
        return new Recovery(List.copyOf(events), last, torn, List.copyOf(diagnostics));
    }

    @SuppressWarnings("unchecked")
    private static Event event(Map<String, Object> row) {
        return new Event(number(row, "sequence"), text(row, "eventId"), SourceKind.valueOf(text(row, "source")),
                EventOperation.valueOf(text(row, "operation")), text(row, "recordKey"), text(row, "payloadHash"),
                row.get("payload") instanceof Map<?, ?> payload ? (Map<String, Object>) payload : Map.of());
    }

    private static Map<String, Object> parseLine(String line) throws IOException {
        Path temporary = Files.createTempFile("journal-record-", ".json");
        try { Files.writeString(temporary, line, StandardCharsets.UTF_8); return Json.object(temporary); }
        finally { Files.deleteIfExists(temporary); }
    }
    private static String text(Map<String, Object> row, String key) {
        Object value = row.get(key); if (value == null) throw new IllegalArgumentException("missing " + key); return String.valueOf(value);
    }
    private static long number(Map<String, Object> row, String key) {
        Object value = row.get(key); return value instanceof Number number ? number.longValue() : Long.parseLong(text(row, key));
    }

    /** Listener-facing queue. Dropped hints are represented by dirty source families. */
    public static final class Ingress {
        private final ArrayBlockingQueue<Hint> queue;
        private final Set<SourceKind> dirty = EnumSet.noneOf(SourceKind.class);
        private final AtomicBoolean accepting = new AtomicBoolean(true);
        private final AtomicLong offered = new AtomicLong();
        private final AtomicLong dropped = new AtomicLong();

        public Ingress(int capacity) { queue = new ArrayBlockingQueue<>(capacity); }

        public boolean offer(Hint hint) {
            Objects.requireNonNull(hint, "hint"); offered.incrementAndGet();
            if (!accepting.get()) return false;
            boolean accepted = queue.offer(hint);
            if (!accepted) dropped.incrementAndGet();
            return accepted;
        }

        public List<Hint> drain(int maximum, long waitMillis) throws InterruptedException {
            List<Hint> result = new ArrayList<>(maximum);
            Hint first = queue.poll(waitMillis, TimeUnit.MILLISECONDS);
            if (first != null) { result.add(first); queue.drainTo(result, maximum - 1); }
            return result;
        }

        public synchronized Set<SourceKind> consumeDirtySources() {
            Set<SourceKind> result = dirty.isEmpty() ? Set.of() : EnumSet.copyOf(dirty); dirty.clear(); return result;
        }
        public void stop() { accepting.set(false); }
        public int depth() { return queue.size(); }
        public long offeredCount() { return offered.get(); }
        public long droppedCount() { return dropped.get(); }
    }

    public record Hint(String eventId, SourceKind source, EventOperation operation,
                       String recordKey, Map<String, Object> payload) {
        public Hint {
            Domain.requireText(eventId, "eventId"); Objects.requireNonNull(source, "source");
            Objects.requireNonNull(operation, "operation"); Domain.requireText(recordKey, "recordKey");
            payload = Domain.immutableMap(payload);
        }
    }
}
