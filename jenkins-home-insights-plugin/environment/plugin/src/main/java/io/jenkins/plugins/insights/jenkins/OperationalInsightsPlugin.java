package io.jenkins.plugins.insights.jenkins;

import hudson.Extension;
import hudson.ExtensionList;
import hudson.cli.CLICommand;
import hudson.init.InitMilestone;
import hudson.init.Initializer;
import hudson.init.Terminator;
import hudson.model.AsyncPeriodicWork;
import hudson.model.Computer;
import hudson.model.Item;
import hudson.model.Queue;
import hudson.model.Run;
import hudson.model.TaskListener;
import hudson.model.listeners.ItemListener;
import hudson.model.listeners.RunListener;
import hudson.model.Queue.LeftItem;
import hudson.model.queue.QueueListener;
import hudson.slaves.ComputerListener;
import hudson.util.FormValidation;
import io.jenkins.plugins.insights.config.InsightsConfig;
import io.jenkins.plugins.insights.journal.EventJournal.Hint;
import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain.EventOperation;
import io.jenkins.plugins.insights.model.Domain.SourceKind;
import io.jenkins.plugins.insights.operator.InsightsMain;
import io.jenkins.plugins.insights.runtime.BackgroundCoordinator;
import io.jenkins.plugins.insights.runtime.InsightsRuntime;
import jenkins.model.Jenkins;
import org.kohsuke.stapler.HttpResponse;
import org.kohsuke.stapler.HttpResponses;
import org.kohsuke.stapler.QueryParameter;
import org.kohsuke.stapler.StaplerRequest2;
import org.kohsuke.stapler.StaplerResponse2;
import org.kohsuke.stapler.interceptor.RequirePOST;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.logging.Level;
import java.util.logging.Logger;

/** Jenkins extension bindings; business logic remains in the offline core. */
public final class OperationalInsightsPlugin {
    private static final Logger LOGGER = Logger.getLogger(OperationalInsightsPlugin.class.getName());
    private static final AtomicLong EVENTS = new AtomicLong();
    private static volatile InsightsRuntime runtime;
    private static volatile BackgroundCoordinator coordinator;
    private OperationalInsightsPlugin() {}

    @Initializer(after = InitMilestone.JOB_LOADED)
    public static synchronized void start() throws IOException {
        if (runtime != null) return;
        Jenkins jenkins = Jenkins.get(); Path home = jenkins.getRootDir().toPath();
        InsightsConfig config = InsightsConfig.load(home.resolve("operational-insights.properties"));
        runtime = new InsightsRuntime(home, home.resolve("operational-insights"));
        coordinator = new BackgroundCoordinator(runtime, config); coordinator.start();
    }

    @Terminator
    public static synchronized void stop() {
        if (coordinator == null) return;
        try { coordinator.close(); } catch (IOException failure) { LOGGER.log(Level.WARNING, "Failed to stop operational insights", failure); }
        finally { coordinator = null; runtime = null; }
    }

    private static void hint(SourceKind source, EventOperation operation, String key, Map<String, Object> payload) {
        BackgroundCoordinator active = coordinator; if (active == null) return;
        String eventId = source.name() + ":" + EVENTS.incrementAndGet();
        active.submit(new Hint(eventId, source, operation, key, payload));
    }

    @Extension public static final class Items extends ItemListener {
        @Override public void onCreated(Item item) { item(item, EventOperation.UPSERT); }
        @Override public void onUpdated(Item item) { item(item, EventOperation.UPSERT); }
        @Override public void onDeleted(Item item) { item(item, EventOperation.DELETE); }
        @Override public void onLocationChanged(Item item, String oldFullName, String newFullName) { item(item, EventOperation.UPSERT); }
        private void item(Item item, EventOperation operation) {
            hint(SourceKind.JOB, operation, item.getFullName(), Map.of("id", item.getFullName(),
                    "fullName", item.getFullName(), "displayName", item.getDisplayName()));
        }
    }

    @Extension public static final class Runs extends RunListener<Run<?, ?>> {
        @Override public void onStarted(Run<?, ?> run, TaskListener listener) { run(run, EventOperation.UPSERT); }
        @Override public void onCompleted(Run<?, ?> run, TaskListener listener) { run(run, EventOperation.UPSERT); }
        @Override public void onDeleted(Run<?, ?> run) { run(run, EventOperation.DELETE); }
        private void run(Run<?, ?> run, EventOperation operation) {
            String key = run.getParent().getFullName() + "#" + run.getNumber();
            hint(SourceKind.BUILD, operation, key, Map.of("id", key, "jobKey", run.getParent().getFullName(),
                    "number", run.getNumber(), "startedMillis", run.getStartTimeInMillis(),
                    "durationMillis", run.getDuration(), "result", run.isBuilding() ? "RUNNING" : String.valueOf(run.getResult())));
        }
    }

    @Extension public static final class QueueEvents extends QueueListener {
        @Override public void onEnterWaiting(Queue.WaitingItem item) { queue(item, EventOperation.UPSERT); }
        @Override public void onLeft(LeftItem item) { queue(item, EventOperation.DELETE); }
        private void queue(Queue.Item item, EventOperation operation) {
            String key = Long.toString(item.getId());
            hint(SourceKind.QUEUE, operation, key, Map.of("id", key, "taskKey", item.task.getFullDisplayName(),
                    "enqueuedMillis", item.getInQueueSince(), "cancelled", item.isCancelled()));
        }
    }

    @Extension public static final class Computers extends ComputerListener {
        @Override public void onOnline(Computer computer, TaskListener listener) { computer(computer); }
        @Override public void onOffline(Computer computer, hudson.slaves.OfflineCause cause) { computer(computer); }
        @Override public void onConfigurationChange() { hint(SourceKind.NODE, EventOperation.DIRTY, "nodes", Map.of()); }
        private void computer(Computer computer) {
            String name = computer.getName(); hint(SourceKind.NODE, EventOperation.UPSERT, name,
                    Map.of("id", name, "displayName", computer.getDisplayName(), "executors", computer.countExecutors(),
                            "busyExecutors", computer.countBusy(), "online", computer.isOnline(), "acceptingTasks", computer.isAcceptingTasks()));
        }
    }

    @Extension public static final class PeriodicReconciliation extends AsyncPeriodicWork {
        public PeriodicReconciliation() { super("Operational insights reconciliation"); }
        @Override public long getRecurrencePeriod() { return 15L * 60L * 1000L; }
        @Override protected void execute(TaskListener listener) throws IOException, InterruptedException {
            InsightsRuntime active = runtime; if (active != null) active.reconcileFull();
        }
    }

    @Extension public static final class Command extends CLICommand {
        @Override public String getShortDescription() { return "Query or operate the read-only operational insight index"; }
        @Override protected int run() throws Exception {
            stderr.println("Use the packaged /app/plugin/bin/insights command for the complete offline command surface."); return 0;
        }
    }

    @Extension public static final class Root implements hudson.model.RootAction {
        public String getIconFileName() { return null; }
        public String getDisplayName() { return "Operational Insights"; }
        public String getUrlName() { return "operational-insights"; }
        public HttpResponse doHealth() {
            Jenkins.get().checkPermission(Jenkins.SYSTEM_READ); InsightsRuntime active = runtime;
            if (active == null) return HttpResponses.errorJSON("not initialized");
            return HttpResponses.okJSON(Json.write(active.health().toMap()));
        }
    }
}