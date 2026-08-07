package com.freight.hash;

/** One checksum or hash algorithm over raw bytes. */
public interface HashAlgorithm {

    String name();

    long apply(byte[] data);

}
