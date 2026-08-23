package io.jenkins.plugins.insights.operator;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import io.jenkins.plugins.insights.generator.HomeGenerator;
import io.jenkins.plugins.insights.journal.EventJournal.Hint;
import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.EventOperation;
import io.jenkins.plugins.insights.model.Domain.SourceKind;
import io.jenkins.plugins.insights.query.QueryService.Principal;
import io.jenkins.plugins.insights.query.QueryService.Request;
import io.jenkins.plugins.insights.query.QueryService.SortDirection;
import io.jenkins.plugins.insights.query.QueryService.View;
import io.jenkins.plugins.insights.runtime.InsightsRuntime;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.Executors;

/** Standalone operator entrypoint mirroring Jenkins CLI and read-only HTTP behavior. */
public final class InsightsMain {
    private InsightsMain() {}

    public static void main(String[] arguments) {
        try { System.out.println(Json.write(run(arguments))); }
        catch (Exception failure) {
            System.err.println(Json.write(Domain.ordered("error", failure.getClass().getSimpleName(), "message", failure.getMessage())));
            System.exit(2);
        }
    }

    public static Map<String, Object> run(String[] arguments) throws Exception {
        Arguments args = Arguments.parse(arguments); String command = args.command();
        if (command.equals("generate")) {
            Path home = args.path("home", Path.of("/var/lib/jenkins-sanitized"));
            int records = args.integer("records", HomeGenerator.DEFAULT_RECORDS); long seed = args.longValue("seed", HomeGenerator.DEFAULT_SEED);
            return Domain.ordered("command", command, "home", home.toString(), "summary", new HomeGenerator().generate(home, records, seed).toMap());
        }
        Path home = args.path("home", envPath("JENKINS_HOME", "/var/lib/jenkins-sanitized"));
        Path state = args.path("state", envPath("INSIGHTS_STATE", "/var/lib/insights"));
        try (InsightsRuntime runtime = new InsightsRuntime(home, state)) {
            return switch (command) {
                case "reconcile" -> reconcile(runtime);
                case "query" -> query(runtime, args, false);
                case "event" -> event(runtime, args);
                case "restart" -> restart(home, state);
                case "compact" -> compact(runtime, args);
                case "health" -> Domain.ordered("command", command, "health", runtime.health().toMap());
                case "serve" -> serve(runtime, args);
                default -> throw new IllegalArgumentException("unknown command: " + command);
            };
        }
    }

    private static Map<String, Object> reconcile(InsightsRuntime runtime) throws IOException {
        var published = runtime.reconcileFull();
        return Domain.ordered("command", "reconcile", "generationId", published.generationId(),
                "records", published.snapshot().recordCount(), "manifest", published.manifest().toMap(),
                "health", runtime.health().toMap());
    }

    private static Map<String, Object> query(InsightsRuntime runtime, Arguments args, boolean http) {
        View view = enumValue(View.class, args.value("view", "records"));
        Set<SourceKind> kinds = new LinkedHashSet<>();
        for (String value : args.values("kind")) kinds.add(enumValue(SourceKind.class, value));
        int defaultLimit = 100;
        Request request = new Request(view, kinds, args.value("contains", ""), args.value("sort", "key"),
                enumValue(SortDirection.class, args.value("direction", "asc")), args.integer("limit", defaultLimit),
                args.value("cursor", ""));
        Principal principal = principal(args);
        return Domain.ordered("command", "query", "response", runtime.query(principal, request).toMap());
    }

    private static Principal principal(Arguments args) {
        String name = args.value("principal", "operator"); boolean system = args.bool("system-read", true);
        boolean overall = args.bool("overall-read", true); Set<String> items = new LinkedHashSet<>(args.values("item"));
        if (items.isEmpty() && system && overall) items.add("*"); return new Principal(name, system, overall, items);
    }

    private static Map<String, Object> event(InsightsRuntime runtime, Arguments args) throws Exception {
        SourceKind source = enumValue(SourceKind.class, args.required("source"));
        EventOperation operation = enumValue(EventOperation.class, args.value("operation", "upsert"));
        String key = args.required("key"); Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("key", key); payload.put("id", key); payload.put("displayName", args.value("display", key));
        payload.put("state", args.value("record-state", "ACTIVE"));
        for (String field : args.values("field")) {
            int separator = field.indexOf('='); if (separator < 1) throw new IllegalArgumentException("field must be key=value");
            payload.put(field.substring(0, separator), scalar(field.substring(separator + 1)));
        }
        String eventId = args.value("event-id", source.name().toLowerCase(Locale.ROOT) + ":" + key + ":1");
        boolean accepted = runtime.offer(new Hint(eventId, source, operation, key, payload));
        int applied = runtime.drainEvents();
        return Domain.ordered("command", "event", "accepted", accepted, "applied", applied,
                "health", runtime.health().toMap());
    }

    private static Map<String, Object> restart(Path home, Path state) throws IOException {
        try (InsightsRuntime restarted = new InsightsRuntime(home, state)) {
            return Domain.ordered("command", "restart", "health", restarted.health().toMap(),
                    "records", restarted.snapshot().recordCount(), "generations", restarted.generations());
        }
    }

    private static Map<String, Object> compact(InsightsRuntime runtime, Arguments args) throws IOException {
        var result = runtime.compact(args.integer("retain", 4));
        return Domain.ordered("command", "compact", "retained", result.retained(), "deleted", result.deleted(),
                "leased", result.leased(), "health", runtime.health().toMap());
    }

    private static Map<String, Object> serve(InsightsRuntime runtime, Arguments args) throws Exception {
        int port = args.integer("port", 8080); HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 16);
        server.createContext("/operational-insights/api/v1/health", exchange -> respond(exchange, 200, runtime.health().toMap()));
        server.createContext("/operational-insights/api/v1/query", exchange -> {
            try {
                Arguments request = Arguments.fromQuery(exchange.getRequestURI());
                respond(exchange, 200, query(runtime, request, true));
            } catch (SecurityException forbidden) { respond(exchange, 403, Domain.ordered("error", "forbidden")); }
            catch (IllegalArgumentException invalid) { respond(exchange, 400, Domain.ordered("error", "bad_request", "message", invalid.getMessage())); }
        });
        server.setExecutor(Executors.newFixedThreadPool(4)); server.start();
        Runtime.getRuntime().addShutdownHook(new Thread(() -> server.stop(1), "insights-http-shutdown"));
        Thread.currentThread().join(); return Domain.ordered("command", "serve", "port", port);
    }

    private static void respond(HttpExchange exchange, int status, Object value) throws IOException {
        byte[] bytes = (Json.write(value) + "\n").getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length); exchange.getResponseBody().write(bytes); exchange.close();
    }

    private static Object scalar(String value) {
        if (value.equalsIgnoreCase("true") || value.equalsIgnoreCase("false")) return Boolean.parseBoolean(value);
        try { return Long.parseLong(value); } catch (NumberFormatException ignored) { return value; }
    }
    private static Path envPath(String key, String fallback) { String value = System.getenv(key); return Path.of(value == null || value.isBlank() ? fallback : value); }
    private static <E extends Enum<E>> E enumValue(Class<E> type, String value) { return Enum.valueOf(type, value.toUpperCase(Locale.ROOT).replace('-', '_')); }

    static final class Arguments {
        private final String command; private final Map<String, List<String>> options;
        private Arguments(String command, Map<String, List<String>> options) { this.command = command; this.options = options; }
        String command() { return command; }
        String value(String key, String fallback) { List<String> values = options.get(key); return values == null || values.isEmpty() ? fallback : values.get(values.size() - 1); }
        String required(String key) { String value = value(key, ""); if (value.isBlank()) throw new IllegalArgumentException("--" + key + " is required"); return value; }
        List<String> values(String key) { return options.getOrDefault(key, List.of()); }
        int integer(String key, int fallback) { return Integer.parseInt(value(key, Integer.toString(fallback))); }
        long longValue(String key, long fallback) { return Long.parseLong(value(key, Long.toString(fallback))); }
        boolean bool(String key, boolean fallback) { return Boolean.parseBoolean(value(key, Boolean.toString(fallback))); }
        Path path(String key, Path fallback) { return Path.of(value(key, fallback.toString())); }

        static Arguments parse(String[] arguments) {
            if (arguments.length == 0) throw new IllegalArgumentException("command is required");
            Map<String, List<String>> options = new LinkedHashMap<>();
            for (int index = 1; index < arguments.length; index++) {
                String token = arguments[index]; if (!token.startsWith("--")) throw new IllegalArgumentException("unexpected argument: " + token);
                String key = token.substring(2); if (key.isBlank()) throw new IllegalArgumentException("empty option");
                String value = index + 1 < arguments.length && !arguments[index + 1].startsWith("--") ? arguments[++index] : "true";
                options.computeIfAbsent(key, ignored -> new ArrayList<>()).add(value);
            }
            return new Arguments(arguments[0].toLowerCase(Locale.ROOT), options);
        }

        static Arguments fromQuery(URI uri) {
            Map<String, List<String>> options = new LinkedHashMap<>(); String query = uri.getRawQuery();
            if (query != null && !query.isBlank()) for (String pair : query.split("&")) {
                String[] parts = pair.split("=", 2); String key = decode(parts[0]); String value = parts.length == 1 ? "true" : decode(parts[1]);
                options.computeIfAbsent(key, ignored -> new ArrayList<>()).add(value);
            }
            return new Arguments("query", options);
        }
        private static String decode(String value) { return java.net.URLDecoder.decode(value, StandardCharsets.UTF_8); }
    }
}
