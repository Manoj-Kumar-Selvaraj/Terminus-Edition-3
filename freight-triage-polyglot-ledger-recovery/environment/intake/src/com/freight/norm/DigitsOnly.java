package com.freight.norm;

/** Normalizer: digits only. */
public final class DigitsOnly implements Normalizer {

    @Override
    public String name() {
        return "digits_only";
    }

    @Override
    public String apply(String text) {
        StringBuilder out = new StringBuilder(text.length());
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c >= '0' && c <= '9') {
                out.append(c);
            }
        }
        return out.toString();
    }
}
