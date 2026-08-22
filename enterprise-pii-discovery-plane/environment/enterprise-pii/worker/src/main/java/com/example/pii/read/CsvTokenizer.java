package com.example.pii.read;

import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

final class CsvTokenizer {
    private final Reader input;
    private long offset;
    private long line = 1;
    private long lastStart;
    private long lastEnd;
    private long lastLine;
    private long lastBytes;
    private int pending = Integer.MIN_VALUE;

    CsvTokenizer(Reader input) { this.input = input; }

    List<String> next() throws IOException {
        ArrayList<String> fields = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean quoted = false;
        boolean any = false;
        lastStart = offset;
        lastLine = line;
        while (true) {
            int raw = read();
            if (raw < 0) {
                if (quoted) throw new IllegalArgumentException("unterminated quoted field");
                if (!any && fields.isEmpty() && field.isEmpty()) return null;
                fields.add(field.toString());
                finish();
                return fields;
            }
            any = true;
            char character = (char) raw;
            if (quoted) {
                if (character == '"') {
                    int next = read();
                    if (next == '"') field.append('"');
                    else {
                        quoted = false;
                        unread(next);
                    }
                } else {
                    field.append(character);
                    if (character == '\n') line++;
                }
                continue;
            }
            if (character == '"' && field.isEmpty()) {
                quoted = true;
            } else if (character == ',') {
                fields.add(field.toString());
                field.setLength(0);
            } else if (character == '\n') {
                fields.add(field.toString());
                line++;
                finish();
                return fields;
            } else if (character == '\r') {
                int next = read();
                if (next != '\n') unread(next);
                fields.add(field.toString());
                line++;
                finish();
                return fields;
            } else {
                field.append(character);
            }
        }
    }

    private int read() throws IOException {
        int value;
        if (pending != Integer.MIN_VALUE) {
            value = pending;
            pending = Integer.MIN_VALUE;
        } else {
            value = input.read();
        }
        if (value >= 0) offset += String.valueOf((char) value).getBytes(StandardCharsets.UTF_8).length;
        return value;
    }

    private void unread(int value) {
        pending = value;
        if (value >= 0) offset -= String.valueOf((char) value).getBytes(StandardCharsets.UTF_8).length;
    }

    private void finish() {
        lastEnd = offset;
        lastBytes = lastEnd - lastStart;
    }

    long lastStart() { return lastStart; }
    long lastEnd() { return lastEnd; }
    long lastLine() { return lastLine; }
    long lastBytes() { return lastBytes; }
}