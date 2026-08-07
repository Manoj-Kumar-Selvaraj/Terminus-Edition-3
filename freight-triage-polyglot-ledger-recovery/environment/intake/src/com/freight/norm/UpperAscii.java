package com.freight.norm;

/** Normalizer: upper ascii. */
public final class UpperAscii implements Normalizer {

    @Override
    public String name() {
        return "upper_ascii";
    }

    @Override
    public String apply(String text) {
        StringBuilder out = new StringBuilder(text.length());
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            out.append((c >= 'a' && c <= 'z') ? (char) (c - 32) : c);
        }
        return out.toString();
    }
}
