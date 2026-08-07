package com.freight.json;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Dependency free JSON value with a recursive descent parser and a canonical
 * writer. Object members are always emitted in ascending key order.
 */
public final class JsonValue {

    public enum Kind { NULL, BOOL, LONG, DOUBLE, STRING, ARRAY, OBJECT }

    private final Kind kind;
    private final boolean boolValue;
    private final long longValue;
    private final double doubleValue;
    private final String stringValue;
    private final List<JsonValue> arrayValue;
    private final Map<String, JsonValue> objectValue;

    private JsonValue(Kind kind, boolean boolValue, long longValue, double doubleValue,
                      String stringValue, List<JsonValue> arrayValue,
                      Map<String, JsonValue> objectValue) {
        this.kind = kind;
        this.boolValue = boolValue;
        this.longValue = longValue;
        this.doubleValue = doubleValue;
        this.stringValue = stringValue;
        this.arrayValue = arrayValue;
        this.objectValue = objectValue;
    }

    public static JsonValue ofNull() {
        return new JsonValue(Kind.NULL, false, 0L, 0.0, null, null, null);
    }

    public static JsonValue of(boolean value) {
        return new JsonValue(Kind.BOOL, value, 0L, 0.0, null, null, null);
    }

    public static JsonValue of(long value) {
        return new JsonValue(Kind.LONG, false, value, 0.0, null, null, null);
    }

    public static JsonValue of(double value) {
        return new JsonValue(Kind.DOUBLE, false, 0L, value, null, null, null);
    }

    public static JsonValue of(String value) {
        return new JsonValue(Kind.STRING, false, 0L, 0.0, value == null ? "" : value, null, null);
    }

    public static JsonValue array() {
        return new JsonValue(Kind.ARRAY, false, 0L, 0.0, null, new ArrayList<JsonValue>(), null);
    }

    public static JsonValue object() {
        return new JsonValue(Kind.OBJECT, false, 0L, 0.0, null, null, new TreeMap<String, JsonValue>());
    }

    public Kind kind() {
        return kind;
    }

    public boolean isNull() {
        return kind == Kind.NULL;
    }

    public boolean asBoolean(boolean fallback) {
        if (kind == Kind.BOOL) {
            return boolValue;
        }
        if (kind == Kind.LONG) {
            return longValue != 0L;
        }
        return fallback;
    }

    public long asLong(long fallback) {
        if (kind == Kind.LONG) {
            return longValue;
        }
        if (kind == Kind.DOUBLE) {
            return (long) doubleValue;
        }
        if (kind == Kind.BOOL) {
            return boolValue ? 1L : 0L;
        }
        return fallback;
    }

    public String asString(String fallback) {
        if (kind == Kind.STRING) {
            return stringValue;
        }
        return fallback;
    }

    public List<JsonValue> items() {
        if (kind != Kind.ARRAY) {
            return Collections.emptyList();
        }
        return arrayValue;
    }

    public Map<String, JsonValue> fields() {
        if (kind != Kind.OBJECT) {
            return Collections.emptyMap();
        }
        return objectValue;
    }

    public JsonValue get(String key) {
        if (kind != Kind.OBJECT) {
            return ofNull();
        }
        JsonValue value = objectValue.get(key);
        return value == null ? ofNull() : value;
    }

    public JsonValue put(String key, JsonValue value) {
        objectValue.put(key, value);
        return this;
    }

    public JsonValue put(String key, String value) {
        return put(key, of(value));
    }

    public JsonValue put(String key, long value) {
        return put(key, of(value));
    }

    public JsonValue put(String key, boolean value) {
        return put(key, of(value));
    }

    public JsonValue add(JsonValue value) {
        arrayValue.add(value);
        return this;
    }

    public String toPretty(int indent) {
        StringBuilder out = new StringBuilder();
        render(out, indent, 0);
        return out.toString();
    }

    public String toCompact() {
        StringBuilder out = new StringBuilder();
        render(out, 0, 0);
        return out.toString();
    }

    private void render(StringBuilder out, int indent, int depth) {
        String newline = indent > 0 ? "\n" : "";
        switch (kind) {
            case NULL:
                out.append("null");
                return;
            case BOOL:
                out.append(boolValue ? "true" : "false");
                return;
            case LONG:
                out.append(Long.toString(longValue));
                return;
            case DOUBLE:
                out.append(String.format(java.util.Locale.ROOT, "%.6f", doubleValue));
                return;
            case STRING:
                out.append('"').append(escape(stringValue)).append('"');
                return;
            case ARRAY: {
                if (arrayValue.isEmpty()) {
                    out.append("[]");
                    return;
                }
                out.append('[').append(newline);
                for (int i = 0; i < arrayValue.size(); i++) {
                    pad(out, indent, depth + 1);
                    arrayValue.get(i).render(out, indent, depth + 1);
                    if (i + 1 < arrayValue.size()) {
                        out.append(',');
                    }
                    out.append(newline);
                }
                pad(out, indent, depth);
                out.append(']');
                return;
            }
            case OBJECT: {
                if (objectValue.isEmpty()) {
                    out.append("{}");
                    return;
                }
                out.append('{').append(newline);
                int index = 0;
                int size = objectValue.size();
                for (Map.Entry<String, JsonValue> entry : objectValue.entrySet()) {
                    pad(out, indent, depth + 1);
                    out.append('"').append(escape(entry.getKey())).append("\": ");
                    entry.getValue().render(out, indent, depth + 1);
                    if (index + 1 < size) {
                        out.append(',');
                    }
                    out.append(newline);
                    index++;
                }
                pad(out, indent, depth);
                out.append('}');
                return;
            }
            default:
                out.append("null");
        }
    }

    private static void pad(StringBuilder out, int indent, int depth) {
        for (int i = 0; i < indent * depth; i++) {
            out.append(' ');
        }
    }

    public static String escape(String raw) {
        StringBuilder out = new StringBuilder(raw.length() + 8);
        for (int i = 0; i < raw.length(); i++) {
            char c = raw.charAt(i);
            switch (c) {
                case '"': out.append("\\\""); break;
                case '\\': out.append("\\\\"); break;
                case '\b': out.append("\\b"); break;
                case '\f': out.append("\\f"); break;
                case '\n': out.append("\\n"); break;
                case '\r': out.append("\\r"); break;
                case '\t': out.append("\\t"); break;
                default:
                    if (c < 0x20) {
                        out.append(String.format(java.util.Locale.ROOT, "\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
            }
        }
        return out.toString();
    }

    public static JsonValue parse(String text) {
        Parser parser = new Parser(text);
        JsonValue value = parser.parseValue();
        parser.skipWhitespace();
        return value;
    }

    public static JsonValue parseFile(Path path) throws IOException {
        return parse(new String(Files.readAllBytes(path), StandardCharsets.UTF_8));
    }

    private static final class Parser {
        private final String text;
        private int pos;

        Parser(String text) {
            this.text = text;
        }

        void skipWhitespace() {
            while (pos < text.length()) {
                char c = text.charAt(pos);
                if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
                    pos++;
                    continue;
                }
                break;
            }
        }

        JsonValue parseValue() {
            skipWhitespace();
            if (pos >= text.length()) {
                throw new IllegalArgumentException("unexpected end of json input");
            }
            char c = text.charAt(pos);
            switch (c) {
                case '{': return parseObject();
                case '[': return parseArray();
                case '"': return JsonValue.of(parseString());
                case 't': expect("true"); return JsonValue.of(true);
                case 'f': expect("false"); return JsonValue.of(false);
                case 'n': expect("null"); return JsonValue.ofNull();
                default: return parseNumber();
            }
        }

        private void expect(String literal) {
            if (!text.startsWith(literal, pos)) {
                throw new IllegalArgumentException("invalid literal at offset " + pos);
            }
            pos += literal.length();
        }

        private JsonValue parseNumber() {
            int start = pos;
            boolean real = false;
            if (pos < text.length() && (text.charAt(pos) == '-' || text.charAt(pos) == '+')) {
                pos++;
            }
            while (pos < text.length()) {
                char c = text.charAt(pos);
                if (c >= '0' && c <= '9') {
                    pos++;
                    continue;
                }
                if (c == '.' || c == 'e' || c == 'E' || c == '+' || c == '-') {
                    real = true;
                    pos++;
                    continue;
                }
                break;
            }
            if (start == pos) {
                throw new IllegalArgumentException("invalid number at offset " + pos);
            }
            String token = text.substring(start, pos);
            if (real) {
                return JsonValue.of(Double.parseDouble(token));
            }
            return JsonValue.of(Long.parseLong(token));
        }

        private String parseString() {
            if (text.charAt(pos) != '"') {
                throw new IllegalArgumentException("expected string at offset " + pos);
            }
            pos++;
            StringBuilder out = new StringBuilder();
            while (pos < text.length()) {
                char c = text.charAt(pos++);
                if (c == '"') {
                    return out.toString();
                }
                if (c != '\\') {
                    out.append(c);
                    continue;
                }
                char esc = text.charAt(pos++);
                switch (esc) {
                    case '"': out.append('"'); break;
                    case '\\': out.append('\\'); break;
                    case '/': out.append('/'); break;
                    case 'b': out.append('\b'); break;
                    case 'f': out.append('\f'); break;
                    case 'n': out.append('\n'); break;
                    case 'r': out.append('\r'); break;
                    case 't': out.append('\t'); break;
                    case 'u':
                        out.append((char) Integer.parseInt(text.substring(pos, pos + 4), 16));
                        pos += 4;
                        break;
                    default:
                        throw new IllegalArgumentException("unknown escape at offset " + pos);
                }
            }
            throw new IllegalArgumentException("unterminated string");
        }

        private JsonValue parseArray() {
            pos++;
            JsonValue result = JsonValue.array();
            skipWhitespace();
            if (pos < text.length() && text.charAt(pos) == ']') {
                pos++;
                return result;
            }
            while (true) {
                result.add(parseValue());
                skipWhitespace();
                if (pos >= text.length()) {
                    throw new IllegalArgumentException("unterminated array");
                }
                char c = text.charAt(pos++);
                if (c == ',') {
                    continue;
                }
                if (c == ']') {
                    return result;
                }
                throw new IllegalArgumentException("expected , or ] at offset " + pos);
            }
        }

        private JsonValue parseObject() {
            pos++;
            JsonValue result = JsonValue.object();
            skipWhitespace();
            if (pos < text.length() && text.charAt(pos) == '}') {
                pos++;
                return result;
            }
            while (true) {
                skipWhitespace();
                String key = parseString();
                skipWhitespace();
                if (pos >= text.length() || text.charAt(pos) != ':') {
                    throw new IllegalArgumentException("expected : at offset " + pos);
                }
                pos++;
                result.put(key, parseValue());
                skipWhitespace();
                if (pos >= text.length()) {
                    throw new IllegalArgumentException("unterminated object");
                }
                char c = text.charAt(pos++);
                if (c == ',') {
                    continue;
                }
                if (c == '}') {
                    return result;
                }
                throw new IllegalArgumentException("expected , or } at offset " + pos);
            }
        }
    }
}
