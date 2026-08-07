package com.freight.norm;

/** Normalizer: dash to underscore. */
public final class DashToUnderscore implements Normalizer {

    @Override
    public String name() {
        return "dash_to_underscore";
    }

    @Override
    public String apply(String text) {
        return text.replace('-', '_');
    }
}
