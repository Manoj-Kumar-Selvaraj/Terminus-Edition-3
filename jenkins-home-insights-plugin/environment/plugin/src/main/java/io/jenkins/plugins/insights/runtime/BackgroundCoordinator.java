package io.jenkins.plugins.insights.runtime;

import io.jenkins.plugins.insights.config.InsightsConfig;
import io.jenkins.plugins.insights.journal.EventJournal.Hint;

import java.io.Closeable;
import java.io.IOException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

/** Bounded single-owner scheduling around the runtime's state transitions. */
public final class BackgroundCoordinator implements Closeable {
    public enum WorkKind { FULL_RECONCILE, EVENT_DRAIN, RETENTION }
    public record WorkStatus(WorkKind kind, long started, long completed, long failed,
                             String lastFailure, boolean running) {}

    private final InsightsRuntime runtime;
    private final InsightsConfig config;
    private final ScheduledExecutorService executor;
    private final AtomicBoolean accepting = new AtomicBoolean(true);
    private final AtomicBoolean reconciling = new AtomicBoolean();
    private final AtomicLong fullStarted = new AtomicLong();
    private final AtomicLong fullCompleted = new AtomicLong();
    private final AtomicLong fullFailed = new AtomicLong();
    private final AtomicLong drainsStarted = new AtomicLong();
    private final AtomicLong drainsCompleted = new AtomicLong();
    private final AtomicLong drainsFailed = new AtomicLong();
    private final AtomicLong retentionStarted = new AtomicLong();
    private final AtomicLong retentionCompleted = new AtomicLong();
    private final AtomicLong retentionFailed = new AtomicLong();
    private final AtomicReference<String> lastFullFailure = new AtomicReference<>("");
    private final AtomicReference<String> lastDrainFailure = new AtomicReference<>("");
    private final AtomicReference<String> lastRetentionFailure = new AtomicReference<>("");
    private final List<ScheduledFuture<?>> schedules = new ArrayList<>();

    public BackgroundCoordinator(InsightsRuntime runtime, InsightsConfig config) {
        this.runtime = Objects.requireNonNull(runtime); this.config = Objects.requireNonNull(config);
        this.executor = Executors.newScheduledThreadPool(2, runnable -> {
            Thread thread = new Thread(runnable, "operational-insights-worker"); thread.setDaemon(true); return thread;
        });
    }

    public synchronized void start() {
        if (!schedules.isEmpty()) return;
        long period = config.periodicInterval().toSeconds();
        schedules.add(executor.scheduleWithFixedDelay(this::safeDrain, 1, 1, TimeUnit.SECONDS));
        schedules.add(executor.scheduleWithFixedDelay(this::safeFull, period, period, TimeUnit.SECONDS));
        schedules.add(executor.scheduleWithFixedDelay(this::safeRetention, period * 2, period * 2, TimeUnit.SECONDS));
    }

    public boolean submit(Hint hint) { return accepting.get() && runtime.offer(hint); }

    public List<WorkStatus> status() {
        return List.of(new WorkStatus(WorkKind.FULL_RECONCILE, fullStarted.get(), fullCompleted.get(), fullFailed.get(),
                        lastFullFailure.get(), reconciling.get()),
                new WorkStatus(WorkKind.EVENT_DRAIN, drainsStarted.get(), drainsCompleted.get(), drainsFailed.get(),
                        lastDrainFailure.get(), false),
                new WorkStatus(WorkKind.RETENTION, retentionStarted.get(), retentionCompleted.get(), retentionFailed.get(),
                        lastRetentionFailure.get(), false));
    }

    private void safeFull() {
        if (!accepting.get() || !reconciling.compareAndSet(false, true)) return;
        fullStarted.incrementAndGet();
        try { runtime.reconcileFull(); fullCompleted.incrementAndGet(); lastFullFailure.set(""); }
        catch (Exception failure) { fullFailed.incrementAndGet(); lastFullFailure.set(message(failure)); }
        finally { reconciling.set(false); }
    }

    private void safeDrain() {
        if (!accepting.get() || reconciling.get()) return; drainsStarted.incrementAndGet();
        try { runtime.drainEvents(); drainsCompleted.incrementAndGet(); lastDrainFailure.set(""); }
        catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); lastDrainFailure.set("interrupted"); }
        catch (Exception failure) { drainsFailed.incrementAndGet(); lastDrainFailure.set(message(failure)); }
    }

    private void safeRetention() {
        if (!accepting.get() || reconciling.get()) return; retentionStarted.incrementAndGet();
        try { runtime.compact(config.retainedGenerations()); retentionCompleted.incrementAndGet(); lastRetentionFailure.set(""); }
        catch (Exception failure) { retentionFailed.incrementAndGet(); lastRetentionFailure.set(message(failure)); }
    }

    private String message(Exception failure) { return failure.getMessage() == null ? failure.getClass().getSimpleName() : failure.getMessage(); }

    @Override public synchronized void close() throws IOException {
        if (!accepting.compareAndSet(true, false)) return;
        schedules.forEach(schedule -> schedule.cancel(true)); executor.shutdownNow();
        try { executor.awaitTermination(config.shutdownTimeout().toMillis(), TimeUnit.MILLISECONDS); }
        catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
        runtime.close();
    }
}
