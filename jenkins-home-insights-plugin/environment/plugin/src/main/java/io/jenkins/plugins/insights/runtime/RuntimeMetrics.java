package io.jenkins.plugins.insights.runtime;

import io.jenkins.plugins.insights.model.Domain;

import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

/** Lock-free counters for operator-visible runtime activity. */
public final class RuntimeMetrics {
    public record Snapshot(long recoveryAttempts, long recoverySuccesses,
                           long fullReconciliations, long incrementalBatches, long appliedEvents,
                           long publishedGenerations, long queries, long failures,
                           String lastOperation, String lastFailure) {
        public Map<String, Object> toMap() {
                return Domain.ordered("recoveryAttempts", recoveryAttempts, "recoverySuccesses", recoverySuccesses,
                    "fullReconciliations", fullReconciliations,
                    "incrementalBatches", incrementalBatches, "appliedEvents", appliedEvents,
                    "publishedGenerations", publishedGenerations, "queries", queries,
                    "failures", failures, "lastOperation", lastOperation, "lastFailure", lastFailure);
        }
    }

    private final AtomicLong recoveryAttempts = new AtomicLong();
    private final AtomicLong recoverySuccesses = new AtomicLong();
    private final AtomicLong fullReconciliations = new AtomicLong();
    private final AtomicLong incrementalBatches = new AtomicLong();
    private final AtomicLong appliedEvents = new AtomicLong();
    private final AtomicLong publishedGenerations = new AtomicLong();
    private final AtomicLong queries = new AtomicLong();
    private final AtomicLong failures = new AtomicLong();
    private final AtomicReference<String> lastOperation = new AtomicReference<>("startup");
    private final AtomicReference<String> lastFailure = new AtomicReference<>("");

    public void recoveryStarted() { recoveryAttempts.incrementAndGet(); lastOperation.set("recovery"); }
    public void recoveryCompleted() { recoverySuccesses.incrementAndGet(); success("recovery"); }
    public void fullPublished() {
        fullReconciliations.incrementAndGet(); publishedGenerations.incrementAndGet(); success("full-reconcile");
    }
    public void incrementalPublished(int events) {
        incrementalBatches.incrementAndGet(); appliedEvents.addAndGet(events);
        publishedGenerations.incrementAndGet(); success("incremental-reconcile");
    }
    public void queryCompleted() { queries.incrementAndGet(); success("query"); }
    public void failure(String operation, Throwable failure) {
        failures.incrementAndGet(); lastOperation.set(operation);
        String message = failure.getMessage(); lastFailure.set(message == null ? failure.getClass().getSimpleName() : message);
    }
    public Snapshot snapshot() {
        return new Snapshot(recoveryAttempts.get(), recoverySuccesses.get(), fullReconciliations.get(),
            incrementalBatches.get(), appliedEvents.get(),
                publishedGenerations.get(), queries.get(), failures.get(), lastOperation.get(), lastFailure.get());
    }
    private void success(String operation) { lastOperation.set(operation); lastFailure.set(""); }
}
