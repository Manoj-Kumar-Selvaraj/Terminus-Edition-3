package com.freight.intake;

import com.freight.json.JsonValue;
import com.freight.selftest.SelftestReport;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Entry point for the freight intake service. */
public final class IntakeMain {

    private static void usage() {
        System.out.println("freight-intake - manifest hold and release intake API");
        System.out.println();
        System.out.println("usage:");
        System.out.println("  intake replay [--root DIR] [--events FILE] [--out FILE]");
        System.out.println("  intake serve [--port N]");
        System.out.println("  intake selftest [--out FILE]");
        System.out.println("  intake version");
    }

    private static Map<String, String> parseArgs(String[] argv, int start) {
        Map<String, String> options = new HashMap<String, String>();
        for (int i = start; i < argv.length; i++) {
            if (!argv[i].startsWith("--")) {
                continue;
            }
            String key = argv[i].substring(2);
            String value = (i + 1 < argv.length && !argv[i + 1].startsWith("--")) ? argv[++i] : "";
            options.put(key, value);
        }
        return options;
    }

    private static void writeText(Path path, String body) throws IOException {
        if (path.getParent() != null) {
            Files.createDirectories(path.getParent());
        }
        Files.write(path, body.getBytes(StandardCharsets.UTF_8));
    }

    private static int runReplay(String[] argv) throws IOException {
        Map<String, String> options = parseArgs(argv, 1);
        String root = options.getOrDefault("root", "/app");
        String eventsPath = options.getOrDefault("events", "");
        if (eventsPath.isEmpty()) {
            eventsPath = root + "/environment/data/intake-events.ndjson";
        }
        String outPath = options.getOrDefault("out", "");
        if (outPath.isEmpty()) {
            outPath = root + "/output/intake-journal.json";
        }

        HoldStore store = new HoldStore();
        IntakeServer server = new IntakeServer(store, 0);
        server.start();
        try {
            ReplayClient client = new ReplayClient(server.baseUrl());
            client.get("/v2/healthz");
            List<IntakeEvent> events = ReplayClient.readEvents(Paths.get(eventsPath));
            int applied = client.replay(events);
            JsonValue journal = client.fetchJournal();
            writeText(Paths.get(outPath), journal.toPretty(2) + "\n");
            System.out.println("intake: replayed " + applied + " events -> " + outPath
                    + " digest=" + journal.get("journal_digest").asString(""));
        } finally {
            server.stop();
        }
        return 0;
    }

    private static int runServe(String[] argv) throws IOException {
        Map<String, String> options = parseArgs(argv, 1);
        int port = Integer.parseInt(options.getOrDefault("port", "8088"));
        HoldStore store = new HoldStore();
        IntakeServer server = new IntakeServer(store, port);
        server.start();
        System.out.println("intake: listening on " + server.baseUrl());
        return 0;
    }

    private static int runSelftest(String[] argv) throws IOException {
        Map<String, String> options = parseArgs(argv, 1);
        String root = options.getOrDefault("root", "/app");
        String outPath = options.getOrDefault("out", "");
        if (outPath.isEmpty()) {
            outPath = root + "/output/selftest-java.json";
        }
        JsonValue report = SelftestReport.build();
        writeText(Paths.get(outPath), report.toPretty(2) + "\n");
        System.out.println("intake: selftest digest=" + report.get("digest").asString(""));
        return 0;
    }

    public static void main(String[] argv) throws Exception {
        if (argv.length == 0) {
            usage();
            System.exit(1);
        }
        String command = argv[0];
        int code;
        if ("replay".equals(command)) {
            code = runReplay(argv);
        } else if ("serve".equals(command)) {
            code = runServe(argv);
        } else if ("selftest".equals(command)) {
            code = runSelftest(argv);
        } else if ("version".equals(command)) {
            System.out.println("freight-intake freight-intake/2");
            code = 0;
        } else {
            usage();
            code = 1;
        }
        if (!"serve".equals(command)) {
            System.exit(code);
        }
    }
}
