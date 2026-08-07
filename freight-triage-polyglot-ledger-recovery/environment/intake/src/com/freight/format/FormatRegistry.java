package com.freight.format;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Ordered catalogue of display formatters. */
public final class FormatRegistry {

    private FormatRegistry() {
    }

    public static List<Formatter> all() {
        List<Formatter> registry = new ArrayList<Formatter>();
        registry.add(new KgToTonnes());
        registry.add(new CentsToAmount());
        registry.add(new LaneLabel());
        registry.add(new WindowLabel());
        registry.add(new DurationHms());
        registry.add(new HexDump8());
        registry.add(new PercentBasis());
        registry.add(new OrdinalSuffix());
        registry.add(new ThousandsGroup());
        registry.add(new SignPrefix());
        registry.add(new SlotLabel());
        registry.add(new Base36Upper());
        return Collections.unmodifiableList(registry);
    }
}
