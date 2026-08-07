package com.freight.intake.http;

import com.freight.json.JsonValue;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/** Shared plumbing for the JSON endpoints exposed by the intake service. */
public abstract class JsonHandler implements HttpHandler {

    protected abstract JsonValue respond(String method, JsonValue body) throws IOException;

    protected boolean requiresPost() {
        return true;
    }

    @Override
    public final void handle(HttpExchange exchange) throws IOException {
        try {
            String method = exchange.getRequestMethod();
            if (requiresPost() && !"POST".equals(method)) {
                write(exchange, 405, error("METHOD_NOT_ALLOWED", method));
                return;
            }
            JsonValue body = JsonValue.ofNull();
            String raw = readBody(exchange.getRequestBody());
            if (!raw.trim().isEmpty()) {
                body = JsonValue.parse(raw);
            }
            JsonValue reply = respond(method, body);
            write(exchange, 200, reply);
        } catch (RuntimeException error) {
            write(exchange, 400, error("BAD_REQUEST", String.valueOf(error.getMessage())));
        } finally {
            exchange.close();
        }
    }

    private static JsonValue error(String code, String detail) {
        JsonValue out = JsonValue.object();
        out.put("accepted", false);
        out.put("code", code);
        out.put("detail", detail == null ? "" : detail);
        return out;
    }

    private static String readBody(InputStream stream) throws IOException {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int read;
        while ((read = stream.read(chunk)) > 0) {
            buffer.write(chunk, 0, read);
        }
        return new String(buffer.toByteArray(), StandardCharsets.UTF_8);
    }

    private static void write(HttpExchange exchange, int status, JsonValue payload)
            throws IOException {
        byte[] body = (payload.toCompact() + "\n").getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().add("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, body.length);
        OutputStream out = exchange.getResponseBody();
        out.write(body);
        out.flush();
    }
}
