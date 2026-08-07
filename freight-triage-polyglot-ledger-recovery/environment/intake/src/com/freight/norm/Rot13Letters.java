package com.freight.norm;

/** Normalizer: rot13 letters. */
public final class Rot13Letters implements Normalizer {

    @Override
    public String name() {
        return "rot13_letters";
    }

    @Override
    public String apply(String text) {
        StringBuilder out = new StringBuilder(text.length());
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c >= 'a' && c <= 'z') {
                c = (char) ('a' + (c - 'a' + 13) % 26);
            } else if (c >= 'A' && c <= 'Z') {
                c = (char) ('A' + (c - 'A' + 13) % 26);
            }
            out.append(c);
        }
        return out.toString();
    }
}
