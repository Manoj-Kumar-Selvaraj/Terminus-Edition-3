package com.example.pii.read;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

final class MiniJson {
    private final String input;
    private final ReadBudgets budgets;
    private int offset;

    MiniJson(String input, ReadBudgets budgets) {
        this.input = input;
        this.budgets = budgets;
    }

    Object parse() {
        Object value = value(0);
        whitespace();
        if (offset != input.length()) throw error("trailing content");
        return value;
    }

    private Object value(int depth) {
        try { budgets.checkNesting(depth); } catch (IOException exception) { throw error("nesting budget"); }
        whitespace();
        if (offset >= input.length()) throw error("expected value");
        char character = input.charAt(offset);
        return switch (character) {
            case '{' -> object(depth + 1);
            case '[' -> array(depth + 1);
            case '"' -> string();
            case 't' -> literal("true", Boolean.TRUE);
            case 'f' -> literal("false", Boolean.FALSE);
            case 'n' -> literal("null", null);
            default -> number();
        };
    }

    private Map<String, Object> object(int depth) {
        LinkedHashMap<String, Object> output = new LinkedHashMap<>();
        offset++;
        whitespace();
        if (take('}')) return output;
        while (true) {
            whitespace();
            if (peek() != '"') throw error("object key expected");
            String key = string();
            whitespace();
            require(':');
            if (output.putIfAbsent(key, value(depth)) != null) throw error("duplicate key");
            whitespace();
            if (take('}')) return output;
            require(',');
        }
    }

    private List<Object> array(int depth) {
        ArrayList<Object> output = new ArrayList<>();
        offset++;
        whitespace();
        if (take(']')) return output;
        while (true) {
            output.add(value(depth));
            whitespace();
            if (take(']')) return output;
            require(',');
        }
    }

    private String string() {
        require('"');
        StringBuilder output = new StringBuilder();
        while (offset < input.length()) {
            char character = input.charAt(offset++);
            if (character == '"') return output.toString();
            if (character != '\\') {
                if (character < 0x20) throw error("control character in string");
                output.append(character);
                continue;
            }
            if (offset >= input.length()) throw error("unterminated escape");
            char escaped = input.charAt(offset++);
            switch (escaped) {
                case '"', '\\', '/' -> output.append(escaped);
                case 'b' -> output.append('\b');
                case 'f' -> output.append('\f');
                case 'n' -> output.append('\n');
                case 'r' -> output.append('\r');
                case 't' -> output.append('\t');
                case 'u' -> output.append(unicode());
                default -> throw error("invalid escape");
            }
        }
        throw error("unterminated string");
    }

    private char unicode() {
        if (offset + 4 > input.length()) throw error("short unicode escape");
        try {
            char value = (char) Integer.parseInt(input.substring(offset, offset + 4), 16);
            offset += 4;
            return value;
        } catch (NumberFormatException exception) {
            throw error("invalid unicode escape");
        }
    }

    private Number number() {
        int start = offset;
        if (take('-')) {}
        digits();
        boolean decimal = false;
        if (take('.')) { decimal = true; digits(); }
        if (take('e') || take('E')) {
            decimal = true;
            if (take('+') || take('-')) {}
            digits();
        }
        String token = input.substring(start, offset);
        try { return decimal ? Double.parseDouble(token) : Long.parseLong(token); }
        catch (NumberFormatException exception) { throw error("invalid number"); }
    }

    private void digits() {
        int start = offset;
        while (offset < input.length() && Character.isDigit(input.charAt(offset))) offset++;
        if (start == offset) throw error("digit expected");
    }

    private Object literal(String token, Object value) {
        if (!input.startsWith(token, offset)) throw error("invalid literal");
        offset += token.length();
        return value;
    }

    private void whitespace() {
        while (offset < input.length() && Character.isWhitespace(input.charAt(offset))) offset++;
    }

    private char peek() { return offset < input.length() ? input.charAt(offset) : '\0'; }
    private boolean take(char wanted) { if (peek() != wanted) return false; offset++; return true; }
    private void require(char wanted) { if (!take(wanted)) throw error("expected " + wanted); }
    private IllegalArgumentException error(String message) { return new IllegalArgumentException(message + " at " + offset); }
}