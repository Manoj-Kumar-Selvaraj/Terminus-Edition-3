package com.freight.norm;

/** ASCII normalization applied to freight reference strings. */
public interface Normalizer {

    String name();

    String apply(String text);

}
