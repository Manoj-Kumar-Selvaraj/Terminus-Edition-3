package io.jenkins.plugins.insights.query;

import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.BuildRecord;
import io.jenkins.plugins.insights.model.Domain.CanonicalRecord;
import io.jenkins.plugins.insights.model.Domain.FingerprintRecord;
import io.jenkins.plugins.insights.model.Domain.JobRecord;
import io.jenkins.plugins.insights.model.Domain.QueueRecord;
import io.jenkins.plugins.insights.query.QueryService.AccessPolicy;
import io.jenkins.plugins.insights.query.QueryService.Principal;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/** Materializes caller-visible records and relationship endpoint decisions. */
public final class VisibilityProjection {
    public record Decision(String key, boolean visible, String owner, String reason) {
        public Map<String, Object> toMap() {
            return Domain.ordered("key", key, "visible", visible, "owner", owner, "reason", reason);
        }
    }
    public record Projection(List<CanonicalRecord> records, List<Decision> decisions,
                             Set<String> visibleJobs, Map<String, Long> visibleKinds) {
        public Map<String, Object> auditMap() {
            return Domain.ordered("visibleRecords", records.size(), "visibleJobs", visibleJobs.stream().sorted().toList(),
                    "visibleKinds", visibleKinds, "decisions", decisions.stream().map(Decision::toMap).toList());
        }
    }

    private final AccessPolicy policy;
    public VisibilityProjection(AccessPolicy policy) { this.policy = policy; }

    public Projection project(Principal principal, Collection<? extends CanonicalRecord> candidates) {
        List<CanonicalRecord> visible = new ArrayList<>(); List<Decision> decisions = new ArrayList<>();
        Set<String> visibleJobs = new HashSet<>(); Map<String, Long> kinds = new TreeMap<>();
        for (CanonicalRecord record : candidates) {
            boolean allowed = policy.mayReadRecord(principal, record); String owner = owner(record);
            decisions.add(new Decision(record.kind().name() + ":" + record.key(), allowed, owner,
                    allowed ? "readable" : "item permission denied"));
            if (!allowed) continue;
            visible.add(record); kinds.merge(record.kind().name().toLowerCase(), 1L, Long::sum);
            if (record instanceof JobRecord job) visibleJobs.add(job.key());
            else if (record instanceof BuildRecord build) visibleJobs.add(build.jobKey());
            else if (record instanceof QueueRecord queue) visibleJobs.add(queue.taskKey());
        }
        return new Projection(List.copyOf(visible), List.copyOf(decisions), Set.copyOf(visibleJobs), Map.copyOf(kinds));
    }

    public boolean lineageEndpointVisible(Projection projection, FingerprintRecord fingerprint,
                                          Map<String, BuildRecord> builds) {
        BuildRecord producer = builds.get(fingerprint.producerBuildKey());
        if (producer == null || !projection.visibleJobs().contains(producer.jobKey())) return false;
        for (String consumerKey : fingerprint.consumerBuildKeys()) {
            BuildRecord consumer = builds.get(consumerKey);
            if (consumer == null || !projection.visibleJobs().contains(consumer.jobKey())) return false;
        }
        return true;
    }

    private String owner(CanonicalRecord record) {
        if (record instanceof JobRecord job) return job.key();
        if (record instanceof BuildRecord build) return build.jobKey();
        if (record instanceof QueueRecord queue) return queue.taskKey();
        if (record instanceof FingerprintRecord fingerprint) return fingerprint.producerBuildKey();
        return "controller";
    }
}
