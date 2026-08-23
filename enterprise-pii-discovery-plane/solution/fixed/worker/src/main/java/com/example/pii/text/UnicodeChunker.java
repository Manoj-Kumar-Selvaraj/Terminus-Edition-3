package com.example.pii.text;

import com.example.pii.read.RecordReader;

import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.List;

public final class UnicodeChunker {
    public record Chunk(
            String text,
            int characterStart,
            int characterEnd,
            long byteStart,
            long byteEnd,
            boolean leadingOverlap,
            boolean trailingOverlap) {}

    private final int targetCodePoints;
    private final int overlapCodePoints;

    public UnicodeChunker(int targetCodePoints, int overlapCodePoints) {
        if (targetCodePoints < 64) throw new IllegalArgumentException("chunk target is too small");
        if (overlapCodePoints < 0 || overlapCodePoints >= targetCodePoints / 2) throw new IllegalArgumentException("invalid chunk overlap");
        this.targetCodePoints = targetCodePoints;
        this.overlapCodePoints = overlapCodePoints;
    }

    public List<Chunk> chunks(RecordReader.Field field) {
        String normalized = normalize(field.text());
        int codePoints = normalized.codePointCount(0, normalized.length());
        if (codePoints <= targetCodePoints) {
            return List.of(chunk(normalized, 0, normalized.length(), field.provenance().byteStart(), false, false));
        }
        ArrayList<Chunk> output = new ArrayList<>();
        int startCodePoint = 0;
        while (startCodePoint < codePoints) {
            int nominalEnd = Math.min(codePoints, startCodePoint + targetCodePoints);
            int startCharacter = normalized.offsetByCodePoints(0, startCodePoint);
            int endCharacter = normalized.offsetByCodePoints(0, nominalEnd);
            if (nominalEnd < codePoints) endCharacter = boundary(normalized, startCharacter, endCharacter);
            boolean leading = startCodePoint > 0;
            boolean trailing = endCharacter < normalized.length();
            output.add(chunk(normalized, startCharacter, endCharacter, field.provenance().byteStart(), leading, trailing));
            if (!trailing) break;
            int endCodePoint = normalized.codePointCount(0, endCharacter);
            int next = Math.max(startCodePoint + 1, endCodePoint - overlapCodePoints);
            startCodePoint = next;
        }
        return List.copyOf(output);
    }

    public List<Span> project(List<Span> spans) {
        ArrayList<Span> sorted = new ArrayList<>(spans);
        sorted.sort(java.util.Comparator.comparingLong(Span::byteStart)
                .thenComparingLong(Span::byteEnd)
                .thenComparing(Span::category)
                .thenComparing(Span::identity));
        ArrayList<Span> output = new ArrayList<>();
        for (Span span : sorted) {
            if (!output.isEmpty()) {
                Span prior = output.getLast();
                if (prior.byteStart() == span.byteStart()
                        && prior.byteEnd() == span.byteEnd()
                        && prior.category().equals(span.category())
                        && prior.identity().equals(span.identity())) continue;
            }
            output.add(span);
        }
        return List.copyOf(output);
    }

    private Chunk chunk(String text, int characterStart, int characterEnd, long baseByte, boolean leading, boolean trailing) {
        String segment = text.substring(characterStart, characterEnd);
        String prefix = characterStart == 0 ? "" : text.substring(0, characterStart);
        long byteStart = baseByte < 0 ? -1 : baseByte + prefix.getBytes(StandardCharsets.UTF_8).length;
        long byteEnd = byteStart < 0 ? -1 : byteStart + segment.getBytes(StandardCharsets.UTF_8).length;
        return new Chunk(segment, characterStart, characterEnd, byteStart, byteEnd, leading, trailing);
    }

    private int boundary(String text, int start, int proposed) {
        int lower = Math.max(start + 1, proposed - 64);
        for (int index = proposed; index > lower; index--) {
            int codePoint = text.codePointBefore(index);
            if (Character.isWhitespace(codePoint) || isBoundaryPunctuation(codePoint)) return index;
        }
        return proposed;
    }

    private boolean isBoundaryPunctuation(int codePoint) {
        int type = Character.getType(codePoint);
        return type == Character.END_PUNCTUATION
                || type == Character.FINAL_QUOTE_PUNCTUATION
                || type == Character.LINE_SEPARATOR
                || type == Character.PARAGRAPH_SEPARATOR;
    }

    public static String normalize(String text) {
        String normalized = Normalizer.normalize(text, Normalizer.Form.NFKC);
        StringBuilder output = new StringBuilder(normalized.length());
        normalized.codePoints().forEach(codePoint -> {
            if (codePoint == '\r') return;
            if (Character.getType(codePoint) == Character.FORMAT && codePoint != 0x200C && codePoint != 0x200D) return;
            output.appendCodePoint(codePoint);
        });
        return output.toString();
    }

    public record Span(
            long byteStart,
            long byteEnd,
            String category,
            String identity) {}
}
