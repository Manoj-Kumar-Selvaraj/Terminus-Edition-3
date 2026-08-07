package com.freight.norm;

/** Normalizer: trim edges. */
public final class TrimEdges implements Normalizer {

    @Override
    public String name() {
        return "trim_edges";
    }

    @Override
    public String apply(String text) {
        int begin = 0;
        int end = text.length();
        while (begin < end && (text.charAt(begin) == ' ' || text.charAt(begin) == '\t')) {
            begin++;
        }
        while (end > begin && (text.charAt(end - 1) == ' ' || text.charAt(end - 1) == '\t')) {
            end--;
        }
        return text.substring(begin, end);
    }
}
