package com.freight.norm;

/** Normalizer: pad left eight. */
public final class PadLeftEight implements Normalizer {

    @Override
    public String name() {
        return "pad_left_eight";
    }

    @Override
    public String apply(String text) {
        if (text.length() >= 8) {
            return text;
        }
        StringBuilder out = new StringBuilder();
        for (int i = text.length(); i < 8; i++) {
            out.append('0');
        }
        return out.append(text).toString();
    }
}
