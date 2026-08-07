package com.freight.norm;

/** Normalizer: reverse bytes. */
public final class ReverseBytes implements Normalizer {

    @Override
    public String name() {
        return "reverse_bytes";
    }

    @Override
    public String apply(String text) {
        return new StringBuilder(text).reverse().toString();
    }
}
