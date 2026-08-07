package com.freight.codec;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Ordered catalogue of every codec in the freight stack. */
public final class CodecRegistry {

    private CodecRegistry() {
    }

    public static List<Codec> all() {
        List<Codec> registry = new ArrayList<Codec>();
        registry.add(new HexLower());
        registry.add(new Base32Rfc4648());
        registry.add(new Base64Std());
        registry.add(new RunLength());
        registry.add(new DeltaByte());
        registry.add(new ZigzagByte());
        registry.add(new Uleb128Tagged());
        registry.add(new EscapeHigh());
        registry.add(new QuotedFreight());
        registry.add(new NibbleSplit());
        registry.add(new XorPad8());
        registry.add(new Chunk16Framed());
        return Collections.unmodifiableList(registry);
    }
}
