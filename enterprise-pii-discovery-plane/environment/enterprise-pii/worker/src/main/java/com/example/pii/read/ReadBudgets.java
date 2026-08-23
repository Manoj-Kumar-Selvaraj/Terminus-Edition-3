package com.example.pii.read;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;

public final class ReadBudgets {
    private final long maximumBytes;
    private final int maximumRecords;
    private final int maximumNesting;
    private final int maximumArchiveEntries;
    private final long maximumArchiveBytes;
    private final int maximumErrors;
    private final Instant deadline;
    private long bytes;
    private int records;
    private int archiveEntries;
    private long archiveBytes;
    private int errors;

    public ReadBudgets(
            long maximumBytes,
            int maximumRecords,
            int maximumNesting,
            int maximumArchiveEntries,
            long maximumArchiveBytes,
            int maximumErrors,
            Duration duration) {
        this.maximumBytes = maximumBytes;
        this.maximumRecords = maximumRecords;
        this.maximumNesting = maximumNesting;
        this.maximumArchiveEntries = maximumArchiveEntries;
        this.maximumArchiveBytes = maximumArchiveBytes;
        this.maximumErrors = maximumErrors;
        this.deadline = Instant.now().plus(duration);
    }

    public void consumeBytes(long count) throws BudgetExceeded {
        bytes = Math.addExact(bytes, count);
        if (bytes > maximumBytes) throw new BudgetExceeded("bytes", maximumBytes, bytes);
        checkTime();
    }

    public void consumeRecord() throws BudgetExceeded {
        records++;
        if (records > maximumRecords) throw new BudgetExceeded("records", maximumRecords, records);
        checkTime();
    }

    public void checkNesting(int depth) throws BudgetExceeded {
        if (depth > maximumNesting) throw new BudgetExceeded("nesting", maximumNesting, depth);
    }

    public void consumeArchiveEntry(long expandedBytes) throws BudgetExceeded {
        archiveEntries++;
        archiveBytes = Math.addExact(archiveBytes, expandedBytes);
        if (archiveEntries > maximumArchiveEntries) throw new BudgetExceeded("archive_entries", maximumArchiveEntries, archiveEntries);
        if (archiveBytes > maximumArchiveBytes) throw new BudgetExceeded("archive_bytes", maximumArchiveBytes, archiveBytes);
        checkTime();
    }

    public boolean allowError() {
        errors++;
        return errors <= maximumErrors;
    }

    public void checkTime() throws BudgetExceeded {
        if (Instant.now().isAfter(deadline)) throw new BudgetExceeded("time", deadline.toEpochMilli(), Instant.now().toEpochMilli());
    }

    public long bytes() { return bytes; }
    public int records() { return records; }
    public int errors() { return errors; }

    public static final class BudgetExceeded extends IOException {
        private final String budget;
        private final long limit;
        private final long observed;

        public BudgetExceeded(String budget, long limit, long observed) {
            super("budget exceeded: " + budget);
            this.budget = budget;
            this.limit = limit;
            this.observed = observed;
        }

        public String budget() { return budget; }
        public long limit() { return limit; }
        public long observed() { return observed; }
    }
}