package io.jenkins.plugins.insights.config;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Properties;

/** Validated operational configuration with bounded resource controls. */
public record InsightsConfig(int schemaVersion, int scanBatchSize, int eventQueueCapacity,
                             int eventFlushRecords, int retainedGenerations,
                             int tombstoneCycles, int defaultQueryLimit, int maximumQueryLimit,
                             double queuePressureThreshold, long generatorSeed,
                             Duration periodicInterval, Duration shutdownTimeout) {
    public InsightsConfig {
        positive(schemaVersion, "schemaVersion"); positive(scanBatchSize, "scanBatchSize");
        positive(eventQueueCapacity, "eventQueueCapacity"); positive(eventFlushRecords, "eventFlushRecords");
        positive(retainedGenerations, "retainedGenerations"); positive(tombstoneCycles, "tombstoneCycles");
        positive(defaultQueryLimit, "defaultQueryLimit"); positive(maximumQueryLimit, "maximumQueryLimit");
        if (defaultQueryLimit > maximumQueryLimit) throw new IllegalArgumentException("default query limit exceeds maximum");
        if (maximumQueryLimit > 10_000) throw new IllegalArgumentException("maximum query limit is unsafe");
        if (!Double.isFinite(queuePressureThreshold) || queuePressureThreshold <= 0) throw new IllegalArgumentException("invalid pressure threshold");
        Objects.requireNonNull(periodicInterval); Objects.requireNonNull(shutdownTimeout);
        if (periodicInterval.isNegative() || periodicInterval.isZero()) throw new IllegalArgumentException("periodic interval must be positive");
        if (shutdownTimeout.isNegative() || shutdownTimeout.isZero()) throw new IllegalArgumentException("shutdown timeout must be positive");
    }

    public static InsightsConfig defaults() {
        return new InsightsConfig(2, 256, 1024, 32, 4, 3, 100, 1000, 1.25, 731927L,
                Duration.ofMinutes(15), Duration.ofSeconds(20));
    }

    public static InsightsConfig load(Path path) throws IOException {
        if (!Files.exists(path)) return defaults();
        Properties values = new Properties();
        try (InputStream input = Files.newInputStream(path)) { values.load(input); }
        InsightsConfig defaults = defaults(); List<String> errors = new ArrayList<>();
        int schema = integer(values, "schema.version", defaults.schemaVersion(), errors);
        int batch = integer(values, "scan.batch.size", defaults.scanBatchSize(), errors);
        int capacity = integer(values, "events.queue.capacity", defaults.eventQueueCapacity(), errors);
        int flush = integer(values, "events.flush.records", defaults.eventFlushRecords(), errors);
        int retained = integer(values, "retention.generations", defaults.retainedGenerations(), errors);
        int tombstones = integer(values, "retention.tombstone.cycles", defaults.tombstoneCycles(), errors);
        int queryDefault = integer(values, "query.default.limit", defaults.defaultQueryLimit(), errors);
        int queryMaximum = integer(values, "query.max.limit", defaults.maximumQueryLimit(), errors);
        double pressure = decimal(values, "queue.pressure.threshold", defaults.queuePressureThreshold(), errors);
        long seed = longNumber(values, "home.generator.seed", defaults.generatorSeed(), errors);
        long period = longNumber(values, "scan.period.seconds", defaults.periodicInterval().toSeconds(), errors);
        long shutdown = longNumber(values, "shutdown.timeout.seconds", defaults.shutdownTimeout().toSeconds(), errors);
        if (!errors.isEmpty()) throw new IllegalArgumentException("invalid configuration: " + String.join("; ", errors));
        return new InsightsConfig(schema, batch, capacity, flush, retained, tombstones, queryDefault,
                queryMaximum, pressure, seed, Duration.ofSeconds(period), Duration.ofSeconds(shutdown));
    }

    private static int integer(Properties values, String key, int fallback, List<String> errors) {
        try { return Integer.parseInt(values.getProperty(key, Integer.toString(fallback)).trim()); }
        catch (NumberFormatException invalid) { errors.add(key + " must be an integer"); return fallback; }
    }
    private static long longNumber(Properties values, String key, long fallback, List<String> errors) {
        try { return Long.parseLong(values.getProperty(key, Long.toString(fallback)).trim()); }
        catch (NumberFormatException invalid) { errors.add(key + " must be an integer"); return fallback; }
    }
    private static double decimal(Properties values, String key, double fallback, List<String> errors) {
        try { return Double.parseDouble(values.getProperty(key, Double.toString(fallback)).trim()); }
        catch (NumberFormatException invalid) { errors.add(key + " must be numeric"); return fallback; }
    }
    private static void positive(int value, String name) { if (value < 1) throw new IllegalArgumentException(name + " must be positive"); }
}
