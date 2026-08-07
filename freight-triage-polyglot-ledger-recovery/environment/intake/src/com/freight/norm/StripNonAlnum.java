package com.freight.norm;

/** Normalizer: strip non alnum. */
public final class StripNonAlnum implements Normalizer {

    @Override
    public String name() {
        return "strip_non_alnum";
    }

    @Override
    public String apply(String text) {
        StringBuilder out = new StringBuilder(text.length());
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if ((c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
                out.append(c);
            }
        }
        return out.toString();
    }
}
