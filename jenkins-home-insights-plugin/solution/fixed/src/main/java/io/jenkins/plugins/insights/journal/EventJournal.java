package io.jenkins.plugins.insights.journal;

import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.Event;
import io.jenkins.plugins.insights.model.Domain.EventOperation;
import io.jenkins.plugins.insights.model.Domain.SourceKind;

import java.io.BufferedReader;
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
import java.util.Set;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;

public final class EventJournal implements Closeable {
    public enum AppendStatus { APPENDED, DUPLICATE, CONFLICT, CLOSED }
    public record AppendResult(AppendStatus status, long sequence, String message) {}
    public record Recovery(List<Event> events, long lastGoodSequence, boolean tornTail, List<String> diagnostics) {}

    private final Path path;
    private final FileChannel channel;
    private final Map<String, String> identities = new HashMap<>();
    private final AtomicLong nextSequence;
    private final AtomicBoolean closed = new AtomicBoolean();

    public EventJournal(Path stateDirectory) throws IOException {
        Files.createDirectories(stateDirectory.resolve("journal"));
        path = stateDirectory.resolve("journal/events.ndjson");
        Recovery recovery = recover(path, -1);
        for (Event event : recovery.events()) identities.put(event.eventId(), signature(event));
        nextSequence = new AtomicLong(recovery.lastGoodSequence() + 1);
        channel = FileChannel.open(path, StandardOpenOption.CREATE, StandardOpenOption.WRITE, StandardOpenOption.APPEND);
    }

    public synchronized AppendResult append(String eventId, SourceKind source, EventOperation operation,
                                            String recordKey, Map<String, Object> payload) throws IOException {
        if (closed.get()) return new AppendResult(AppendStatus.CLOSED, -1, "journal is closed");
        String payloadHash = Domain.sha256(Json.write(payload));
        String candidate = signature(source, operation, recordKey, payloadHash);
        String existing = identities.get(eventId);
        if (existing != null) {
            return existing.equals(candidate)
                    ? new AppendResult(AppendStatus.DUPLICATE, -1, "event identity already represented")
                    : new AppendResult(AppendStatus.CONFLICT, -1, "event identity has conflicting content");
        }
        long sequence = nextSequence.get();
        Event event = new Event(sequence, eventId, source, operation, recordKey, payloadHash, payload);
        Map<String, Object> envelope = new LinkedHashMap<>(event.toMap());
        envelope.put("checksum", Domain.sha256(Json.write(event.toMap())));
        ByteBuffer bytes = ByteBuffer.wrap((Json.write(envelope) + "\n").getBytes(StandardCharsets.UTF_8));
        while (bytes.hasRemaining()) channel.write(bytes);
        channel.force(true);
        identities.put(eventId, candidate);
        nextSequence.incrementAndGet();
        return new AppendResult(AppendStatus.APPENDED, sequence, "accepted and durable");
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
            String line; long lineNumber = 0; long expected = -1;
            while ((line = reader.readLine()) != null) {
                lineNumber++; if (line.isBlank()) continue;
                try {
                    Map<String, Object> envelope = parseLine(line);
                    String checksum = text(envelope, "checksum");
                    Map<String, Object> eventMap = new LinkedHashMap<>(envelope); eventMap.remove("checksum");
                    if (!Domain.sha256(Json.write(eventMap)).equals(checksum)) throw new IOException("checksum mismatch");
                    Event event = event(eventMap);
                    if (expected < 0) expected = event.sequence();
                    if (event.sequence() != expected) throw new IOException("non-contiguous sequence");
                    if (!Domain.sha256(Json.write(event.payload())).equals(event.payloadHash())) throw new IOException("payload hash mismatch");
                    expected++; last = event.sequence();
                    if (event.sequence() > afterSequence) events.add(event);
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
    private static String signature(Event event) {
        return signature(event.source(), event.operation(), event.recordKey(), event.payloadHash());
    }
    private static String signature(SourceKind source, EventOperation operation, String recordKey, String payloadHash) {
        return Domain.sha256(Json.write(Domain.ordered("source", source.name(), "operation", operation.name(),
                "recordKey", recordKey, "payloadHash", payloadHash)));
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
            if (!accepted) {
                dropped.incrementAndGet();
                synchronized (dirty) { dirty.add(hint.source()); }
            }
            return accepted;
        }

        public List<Hint> drain(int maximum, long waitMillis) throws InterruptedException {
            List<Hint> result = new ArrayList<>(maximum);
            Hint first = queue.poll(waitMillis, TimeUnit.MILLISECONDS);
            if (first != null) { result.add(first); queue.drainTo(result, maximum - 1); }
            return result;
        }

        public Set<SourceKind> consumeDirtySources() {
            synchronized (dirty) {
                Set<SourceKind> result = dirty.isEmpty() ? Set.of() : EnumSet.copyOf(dirty);
                dirty.clear(); return result;
            }
        }
        public void restoreDirtySources(Set<SourceKind> sources) { synchronized (dirty) { dirty.addAll(sources); } }
        public void clearDropped() { dropped.set(0); }
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