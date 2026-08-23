package io.jenkins.plugins.insights.jenkins;

import hudson.Extension;
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
import io.jenkins.plugins.insights.config.InsightsConfig;
import io.jenkins.plugins.insights.journal.EventJournal.Hint;
import io.jenkins.plugins.insights.json.Json;
import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.EventOperation;
import io.jenkins.plugins.insights.model.Domain.JobRecord;
import io.jenkins.plugins.insights.model.Domain.SourceKind;
import io.jenkins.plugins.insights.query.QueryService.Principal;
import io.jenkins.plugins.insights.query.QueryService.Request;
import io.jenkins.plugins.insights.query.QueryService.SortDirection;
import io.jenkins.plugins.insights.query.QueryService.View;
import io.jenkins.plugins.insights.runtime.BackgroundCoordinator;
import io.jenkins.plugins.insights.runtime.InsightsRuntime;
import jenkins.model.Jenkins;
import org.kohsuke.args4j.Option;
import org.kohsuke.stapler.HttpResponse;
import org.kohsuke.stapler.HttpResponses;
import org.kohsuke.stapler.StaplerRequest2;

import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;

public final class OperationalInsightsPlugin {
    private static final Logger LOGGER = Logger.getLogger(OperationalInsightsPlugin.class.getName());
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
        String eventId = source.name().toLowerCase(Locale.ROOT) + ":" + operation.name().toLowerCase(Locale.ROOT)
                + ":" + key + ":" + Domain.sha256(Json.write(payload)).substring(0, 24);
        active.submit(new Hint(eventId, source, operation, key, payload));
    }
    private static String canonicalJobKey(String fullName) {
        InsightsRuntime active = runtime;
        if (active != null) for (JobRecord job : active.snapshot().jobs().values()) if (job.fullName().equals(fullName)) return job.key();
        return fullName;
    }

    @Extension public static final class Items extends ItemListener {
        @Override public void onCreated(Item item) { item(item, item.getFullName(), EventOperation.UPSERT); }
        @Override public void onUpdated(Item item) { item(item, item.getFullName(), EventOperation.UPSERT); }
        @Override public void onDeleted(Item item) { item(item, item.getFullName(), EventOperation.DELETE); }
        @Override public void onLocationChanged(Item item, String oldFullName, String newFullName) { item(item, oldFullName, EventOperation.UPSERT); }
        private void item(Item item, String identityName, EventOperation operation) {
            String key = canonicalJobKey(identityName);
            hint(SourceKind.JOB, operation, key, Map.of("id", key, "fullName", item.getFullName(),
                    "displayName", item.getDisplayName()));
        }
    }

    @Extension public static final class Runs extends RunListener<Run<?, ?>> {
        @Override public void onStarted(Run<?, ?> run, TaskListener listener) { run(run, EventOperation.UPSERT); }
        @Override public void onCompleted(Run<?, ?> run, TaskListener listener) { run(run, EventOperation.UPSERT); }
        @Override public void onDeleted(Run<?, ?> run) { run(run, EventOperation.DELETE); }
        private void run(Run<?, ?> run, EventOperation operation) {
            String jobKey = canonicalJobKey(run.getParent().getFullName()); String key = jobKey + "#" + run.getNumber();
            hint(SourceKind.BUILD, operation, key, Map.of("id", key, "jobKey", jobKey, "number", run.getNumber(),
                    "startedMillis", run.getStartTimeInMillis(), "durationMillis", run.getDuration(),
                    "result", run.isBuilding() ? "RUNNING" : String.valueOf(run.getResult())));
        }
    }

    @Extension public static final class QueueEvents extends QueueListener {
        @Override public void onEnterWaiting(Queue.WaitingItem item) { queue(item, EventOperation.UPSERT); }
        @Override public void onLeft(LeftItem item) { queue(item, EventOperation.DELETE); }
        private void queue(Queue.Item item, EventOperation operation) {
            String key = Long.toString(item.getId()); String task = item.task instanceof Item owned
                    ? canonicalJobKey(owned.getFullName()) : item.task.getFullDisplayName();
            hint(SourceKind.QUEUE, operation, key, Map.of("id", key, "taskKey", task,
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
                            "busyExecutors", computer.countBusy(), "online", computer.isOnline(),
                            "acceptingTasks", computer.isAcceptingTasks()));
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
        @Option(name = "--view") private String view = "records";
        @Option(name = "--kind") private List<String> kinds = new ArrayList<>();
        @Option(name = "--contains") private String contains = "";
        @Option(name = "--sort") private String sort = "key";
        @Option(name = "--direction") private String direction = "asc";
        @Option(name = "--limit") private int limit = 100;
        @Option(name = "--cursor") private String cursor = "";
        @Override public String getShortDescription() { return "Query the read-only operational insight index"; }
        @Override protected int run() {
            Jenkins.get().checkPermission(Jenkins.SYSTEM_READ); InsightsRuntime active = requireRuntime();
            stdout.println(Json.write(active.query(principal(), request(view, kinds, contains, sort, direction, limit, cursor)).toMap()));
            return 0;
        }
    }

    @Extension public static final class Root implements hudson.model.RootAction {
        public String getIconFileName() { return null; }
        public String getDisplayName() { return "Operational Insights"; }
        public String getUrlName() { return "operational-insights"; }
        public HttpResponse doHealth() {
            Jenkins.get().checkPermission(Jenkins.SYSTEM_READ); return HttpResponses.okJSON(requireRuntime().health().toMap());
        }
        public HttpResponse doQuery(StaplerRequest2 request) {
            Jenkins.get().checkPermission(Jenkins.SYSTEM_READ);
            String[] kindValues = request.getParameterValues("kind");
            List<String> kinds = kindValues == null ? List.of() : List.of(kindValues);
            Request query = request(value(request, "view", "records"), kinds, value(request, "contains", ""),
                    value(request, "sort", "key"), value(request, "direction", "asc"),
                    integer(request, "limit", 100), value(request, "cursor", ""));
            return HttpResponses.okJSON(requireRuntime().query(principal(), query).toMap());
        }
    }

    private static InsightsRuntime requireRuntime() {
        InsightsRuntime active = runtime; if (active == null) throw new IllegalStateException("operational insights is not initialized"); return active;
    }
    private static Principal principal() {
        Jenkins jenkins = Jenkins.get(); Set<String> readable = new LinkedHashSet<>();
        InsightsRuntime active = requireRuntime();
        for (JobRecord job : active.snapshot().jobs().values()) {
            Item item = jenkins.getItemByFullName(job.fullName()); if (item != null && item.hasPermission(Item.READ)) readable.add(job.key());
        }
        return new Principal(Jenkins.getAuthentication2().getName(), true, true, readable);
    }
    private static Request request(String view, List<String> kinds, String contains, String sort,
                                   String direction, int limit, String cursor) {
        Set<SourceKind> parsedKinds = new LinkedHashSet<>();
        for (String kind : kinds) parsedKinds.add(SourceKind.valueOf(kind.toUpperCase(Locale.ROOT)));
        return new Request(View.valueOf(view.toUpperCase(Locale.ROOT)), parsedKinds, contains, sort,
                SortDirection.valueOf(direction.toUpperCase(Locale.ROOT)), limit, cursor);
    }
    private static String value(StaplerRequest2 request, String name, String fallback) {
        String value = request.getParameter(name); return value == null ? fallback : value;
    }
    private static int integer(StaplerRequest2 request, String name, int fallback) {
        return Integer.parseInt(value(request, name, Integer.toString(fallback)));
    }
}