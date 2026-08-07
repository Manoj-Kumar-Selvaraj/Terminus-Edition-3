package com.freight.format;

/** Display formatter used on dock sheets and audit exports. */
public interface Formatter {

    String name();

    String apply(long value);

}
