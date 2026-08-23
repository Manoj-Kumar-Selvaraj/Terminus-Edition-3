package io.jenkins.plugins.insights.json;

import java.io.IOException;
import java.io.Reader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Dependency-free deterministic JSON for the offline operational core. */
public final class Json {
    private Json() {}

    public static String write(Object value) {
        StringBuilder output = new StringBuilder();
        append(output, value);
        return output.toString();
    }

    public static void write(Path path, Object value) throws IOException {
        Files.createDirectories(path.toAbsolutePath().getParent());
        Files.writeString(path, write(value) + "\n", StandardCharsets.UTF_8);
    }

    public static Object parse(Path path) throws IOException {
        try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            return new Parser(reader).parse();
        }
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> object(Path path) throws IOException {
        Object value = parse(path);
        if (!(value instanceof Map<?, ?>)) throw new IOException("expected JSON object: " + path);
        return (Map<String, Object>) value;
    }

    private static void append(StringBuilder output, Object value) {
        if (value == null) { output.append("null"); return; }
        if (value instanceof String text) { string(output, text); return; }
        if (value instanceof Number || value instanceof Boolean) { output.append(value); return; }
        if (value instanceof Enum<?> enumeration) { string(output, enumeration.name()); return; }
        if (value instanceof Map<?, ?> map) {
            output.append('{');
            List<Map.Entry<?, ?>> entries = new ArrayList<>(map.entrySet());
            entries.sort(Comparator.comparing(entry -> String.valueOf(entry.getKey())));
            boolean first = true;
            for (Map.Entry<?, ?> entry : entries) {
                if (!first) output.append(',');
                first = false;
                string(output, String.valueOf(entry.getKey())); output.append(':'); append(output, entry.getValue());
            }
            output.append('}'); return;
        }
        if (value instanceof Collection<?> collection) {
            output.append('['); boolean first = true;
            for (Object item : collection) { if (!first) output.append(','); first = false; append(output, item); }
            output.append(']'); return;
        }
        if (value.getClass().isArray()) {
            output.append('['); int length = java.lang.reflect.Array.getLength(value);
            for (int index = 0; index < length; index++) { if (index > 0) output.append(','); append(output, java.lang.reflect.Array.get(value, index)); }
            output.append(']'); return;
        }
        throw new IllegalArgumentException("unsupported JSON value: " + value.getClass().getName());
    }

    private static void string(StringBuilder output, String value) {
        output.append('"');
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            switch (character) {
                case '"' -> output.append("\\\"");
                case '\\' -> output.append("\\\\");
                case '\b' -> output.append("\\b");
                case '\f' -> output.append("\\f");
                case '\n' -> output.append("\\n");
                case '\r' -> output.append("\\r");
                case '\t' -> output.append("\\t");
                default -> {
                    if (character < 0x20) output.append(String.format("\\u%04x", (int) character));
                    else output.append(character);
                }
            }
        }
        output.append('"');
    }

    private static final class Parser {
        private final Reader reader;
        private int next = -2;
        private Parser(Reader reader) { this.reader = reader; }

        private Object parse() throws IOException {
            Object value = value();
            whitespace();
            if (peek() != -1) throw error("trailing content");
            return value;
        }

        private Object value() throws IOException {
            whitespace();
            return switch (peek()) {
                case '{' -> object();
                case '[' -> array();
                case '"' -> text();
                case 't' -> literal("true", Boolean.TRUE);
                case 'f' -> literal("false", Boolean.FALSE);
                case 'n' -> literal("null", null);
                default -> number();
            };
        }

        private Map<String, Object> object() throws IOException {
            expect('{'); whitespace(); Map<String, Object> result = new LinkedHashMap<>();
            if (peek() == '}') { read(); return result; }
            while (true) {
                if (peek() != '"') throw error("object key must be a string");
                String key = text(); whitespace(); expect(':');
                if (result.put(key, value()) != null) throw error("duplicate object key: " + key);
                whitespace(); int delimiter = read();
                if (delimiter == '}') return result;
                if (delimiter != ',') throw error("expected comma or closing brace");
                whitespace();
            }
        }

        private List<Object> array() throws IOException {
            expect('['); whitespace(); List<Object> result = new ArrayList<>();
            if (peek() == ']') { read(); return result; }
            while (true) {
                result.add(value()); whitespace(); int delimiter = read();
                if (delimiter == ']') return result;
                if (delimiter != ',') throw error("expected comma or closing bracket");
                whitespace();
            }
        }

        private String text() throws IOException {
            expect('"'); StringBuilder result = new StringBuilder();
            while (true) {
                int character = read();
                if (character < 0) throw error("unterminated string");
                if (character == '"') return result.toString();
                if (character != '\\') { result.append((char) character); continue; }
                int escaped = read();
                switch (escaped) {
                    case '"', '\\', '/' -> result.append((char) escaped);
                    case 'b' -> result.append('\b'); case 'f' -> result.append('\f');
                    case 'n' -> result.append('\n'); case 'r' -> result.append('\r'); case 't' -> result.append('\t');
                    case 'u' -> result.append((char) Integer.parseInt(readChars(4), 16));
                    default -> throw error("invalid escape");
                }
            }
        }

        private Object number() throws IOException {
            StringBuilder token = new StringBuilder();
            while (peek() == '-' || peek() == '+' || peek() == '.' || peek() == 'e' || peek() == 'E' || Character.isDigit(peek())) token.append((char) read());
            if (token.isEmpty()) throw error("expected value");
            try {
                BigDecimal decimal = new BigDecimal(token.toString());
                return decimal.scale() <= 0 ? decimal.longValueExact() : decimal;
            } catch (ArithmeticException | NumberFormatException invalid) {
                throw error("invalid number: " + token);
            }
        }

        private Object literal(String expected, Object value) throws IOException {
            if (!readChars(expected.length()).equals(expected)) throw error("invalid literal");
            return value;
        }

        private String readChars(int count) throws IOException {
            StringBuilder result = new StringBuilder(count);
            for (int index = 0; index < count; index++) {
                int character = read(); if (character < 0) throw error("unexpected end"); result.append((char) character);
            }
            return result.toString();
        }

        private void expect(int expected) throws IOException { if (read() != expected) throw error("expected " + (char) expected); }
        private void whitespace() throws IOException { while (Character.isWhitespace(peek())) read(); }
        private int peek() throws IOException { if (next == -2) next = reader.read(); return next; }
        private int read() throws IOException { int value = peek(); next = -2; return value; }
        private IOException error(String message) { return new IOException("invalid JSON: " + message); }
    }
}