package com.freight.norm;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Ordered catalogue of normalizers. */
public final class NormalizerRegistry {

    private NormalizerRegistry() {
    }

    public static List<Normalizer> all() {
        List<Normalizer> registry = new ArrayList<Normalizer>();
        registry.add(new UpperAscii());
        registry.add(new LowerAscii());
        registry.add(new TrimEdges());
        registry.add(new CollapseSpaces());
        registry.add(new StripNonAlnum());
        registry.add(new DashToUnderscore());
        registry.add(new PadLeftEight());
        registry.add(new ReverseBytes());
        registry.add(new Rot13Letters());
        registry.add(new DigitsOnly());
        return Collections.unmodifiableList(registry);
    }
}
