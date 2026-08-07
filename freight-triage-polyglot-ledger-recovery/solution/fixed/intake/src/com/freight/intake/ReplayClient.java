package com.freight.intake;

import com.freight.json.JsonValue;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/** Replays a newline delimited event file against a running intake service. */
public final class ReplayClient {

    private final String baseUrl;

    public ReplayClient(String baseUrl) {
        this.baseUrl = baseUrl;
    }

    public static List<IntakeEvent> readEvents(Path path) throws IOException {
        List<IntakeEvent> events = new ArrayList<IntakeEvent>();
        for (String line : Files.readAllLines(path, StandardCharsets.UTF_8)) {
            String trimmed = line.trim();
            if (trimmed.isEmpty()) {
                continue;
            }
            events.add(IntakeEvent.fromJson(JsonValue.parse(trimmed)));
        }
        return events;
    }

    /** Intake applies events in ascending sequence order. */
    public static List<IntakeEvent> ordered(List<IntakeEvent> input) {
        List<IntakeEvent> events = new ArrayList<IntakeEvent>(input);
        events.sort(new Comparator<IntakeEvent>() {
            @Override
            public int compare(IntakeEvent left, IntakeEvent right) {
                return Long.compare(left.seq, right.seq);
            }
        });
        return events;
    }

    public int replay(List<IntakeEvent> events) throws IOException {
        int applied = 0;
        for (IntakeEvent event : ordered(events)) {
            post(event.endpoint(), event.toJson().toCompact());
            applied++;
        }
        return applied;
    }

    public JsonValue fetchJournal() throws IOException {
        return JsonValue.parse(get("/v2/journal"));
    }

    public String post(String path, String body) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(baseUrl + path).openConnection();
        connection.setRequestMethod("POST");
        connection.setDoOutput(true);
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(20000);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        byte[] payload = body.getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(payload.length);
        OutputStream out = connection.getOutputStream();
        out.write(payload);
        out.flush();
        out.close();
        return drain(connection);
    }

    public String get(String path) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(baseUrl + path).openConnection();
        connection.setRequestMethod("GET");
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(20000);
        return drain(connection);
    }

    private static String drain(HttpURLConnection connection) throws IOException {
        int status = connection.getResponseCode();
        InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
        if (stream == null) {
            return "";
        }
        StringBuilder out = new StringBuilder();
        BufferedReader reader =
                new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) {
            out.append(line).append('\n');
        }
        reader.close();
        connection.disconnect();
        return out.toString();
    }
}
