package com.freight.codec;

/** Reversible byte codec used by the freight wire formats. */
public interface Codec {

    String name();

    byte[] encode(byte[] data);

    byte[] decode(byte[] data);

}
