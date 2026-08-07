package com.freight.norm;

/** Normalizer: collapse spaces. */
public final class CollapseSpaces implements Normalizer {

    @Override
    public String name() {
        return "collapse_spaces";
    }

    @Override
    public String apply(String text) {
        StringBuilder out = new StringBuilder(text.length());
        boolean pending = false;
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c == ' ') {
                pending = true;
                continue;
            }
            if (pending && out.length() > 0) {
                out.append(' ');
            }
            pending = false;
            out.append(c);
        }
        return out.toString();
    }
}
