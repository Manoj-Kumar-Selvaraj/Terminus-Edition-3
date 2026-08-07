package com.freight.hash;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Ordered catalogue of every hash algorithm in the freight stack. */
public final class HashRegistry {

    private HashRegistry() {
    }

    public static List<HashAlgorithm> all() {
        List<HashAlgorithm> registry = new ArrayList<HashAlgorithm>();
        registry.add(new Fnv1a32());
        registry.add(new Fnv1a64());
        registry.add(new Djb2());
        registry.add(new Sdbm());
        registry.add(new ElfHash());
        registry.add(new Adler32());
        registry.add(new Fletcher16());
        registry.add(new Fletcher32());
        registry.add(new Crc32Ieee());
        registry.add(new Crc32c());
        registry.add(new Crc16Ccitt());
        registry.add(new Crc8Atm());
        registry.add(new JenkinsOaat());
        registry.add(new Murmur332());
        registry.add(new XorRotate());
        registry.add(new BsdSum16());
        return Collections.unmodifiableList(registry);
    }
}
