package io.jenkins.plugins.insights.storage;

import io.jenkins.plugins.insights.model.Domain;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Produces an auditable plan before generation directories are removed. */
public final class RetentionPlanner {
    public enum Reason {
        CURRENT,
        LEASED,
        RECENT,
        RECOVERY_FALLBACK,
        REFERENCED,
        EXPIRED
    }

    public record Decision(String generationId, boolean retain, Set<Reason> reasons) {
        public Decision {
            reasons = Set.copyOf(reasons);
        }

        public Map<String, Object> toMap() {
            return Domain.ordered(
                    "generationId", generationId,
                    "retain", retain,
                    "reasons", reasons.stream().map(Enum::name).sorted().toList());
        }
    }

    public record Plan(List<Decision> decisions, List<String> retained, List<String> removable) {
        public Plan {
            decisions = List.copyOf(decisions);
            retained = List.copyOf(retained);
            removable = List.copyOf(removable);
        }

        public Map<String, Object> toMap() {
            return Domain.ordered(
                    "decisions", decisions.stream().map(Decision::toMap).toList(),
                    "retained", retained,
                    "removable", removable);
        }
    }

    public Plan plan(
            List<Path> generations,
            String current,
            Set<String> leased,
            int retainCount,
            Map<String, Set<String>> references) {
        if (retainCount < 1) {
            throw new IllegalArgumentException("retain count must be positive");
        }

        List<Path> ordered = generations.stream()
                .sorted(Comparator.comparing(path -> path.getFileName().toString()))
                .toList();
        Set<String> recent = new HashSet<>();
        int recentStart = Math.max(0, ordered.size() - retainCount);
        for (int index = recentStart; index < ordered.size(); index++) {
            recent.add(id(ordered.get(index)));
        }

        String fallback = "";
        for (int index = ordered.size() - 1; index >= 0; index--) {
            String candidate = id(ordered.get(index));
            if (!candidate.equals(current)) {
                fallback = candidate;
                break;
            }
        }

        List<Decision> decisions = new ArrayList<>();
        List<String> retained = new ArrayList<>();
        List<String> removable = new ArrayList<>();
        for (Path directory : ordered) {
            String generation = id(directory);
            Set<Reason> reasons = new HashSet<>();
            if (generation.equals(current)) {
                reasons.add(Reason.CURRENT);
            }
            if (leased.contains(generation)) {
                reasons.add(Reason.LEASED);
            }
            if (recent.contains(generation)) {
                reasons.add(Reason.RECENT);
            }
            if (generation.equals(fallback)) {
                reasons.add(Reason.RECOVERY_FALLBACK);
            }
            if (referenced(generation, references)) {
                reasons.add(Reason.REFERENCED);
            }
            boolean keep = !reasons.isEmpty();
            if (!keep) {
                reasons.add(Reason.EXPIRED);
                removable.add(generation);
            } else {
                retained.add(generation);
            }
            decisions.add(new Decision(generation, keep, reasons));
        }
        return new Plan(decisions, retained, removable);
    }

    public Map<String, Set<String>> readReferences(List<Path> generations) throws IOException {
        Map<String, Set<String>> references = new HashMap<>();
        for (Path directory : generations) {
            Path file = directory.resolve("references.json");
            if (!Files.isRegularFile(file)) {
                continue;
            }
            Object parsed = io.jenkins.plugins.insights.json.Json.parse(file);
            if (!(parsed instanceof Map<?, ?> map)) {
                continue;
            }
            Set<String> targets = new HashSet<>();
            Object rawTargets = map.get("generationIds");
            if (rawTargets instanceof Iterable<?> values) {
                for (Object value : values) {
                    targets.add(String.valueOf(value));
                }
            }
            references.put(id(directory), Set.copyOf(targets));
        }
        return Map.copyOf(references);
    }

    private boolean referenced(String generation, Map<String, Set<String>> references) {
        for (Set<String> targets : references.values()) {
            if (targets.contains(generation)) {
                return true;
            }
        }
        return false;
    }

    private String id(Path directory) {
        return directory.getFileName().toString();
    }
}
