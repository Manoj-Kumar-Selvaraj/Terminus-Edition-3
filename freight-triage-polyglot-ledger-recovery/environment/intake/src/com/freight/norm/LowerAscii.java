package com.freight.norm;

/** Normalizer: lower ascii. */
public final class LowerAscii implements Normalizer {

    @Override
    public String name() {
        return "lower_ascii";
    }

    @Override
    public String apply(String text) {
        StringBuilder out = new StringBuilder(text.length());
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            out.append((c >= 'A' && c <= 'Z') ? (char) (c + 32) : c);
        }
        return out.toString();
    }
}
