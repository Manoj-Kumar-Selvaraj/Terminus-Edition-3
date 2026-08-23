package io.jenkins.plugins.insights.storage;

import io.jenkins.plugins.insights.model.Domain;
import io.jenkins.plugins.insights.model.Domain.GenerationManifest;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/** Classifies generation candidates and records deterministic recovery decisions. */
public final class RecoveryPlanner {
    public enum CandidateState { COMPLETE, INCOMPLETE, CORRUPT, LEGACY, STAGING }
    public record Candidate(String generationId, Path directory, CandidateState state,
                            int schemaVersion, long lastSequence, int recordCount,
                            boolean pointed, List<String> diagnostics) {
        public Map<String, Object> toMap() {
            return Domain.ordered("generationId", generationId, "directory", directory.toString(),
                    "state", state.name(), "schemaVersion", schemaVersion, "lastSequence", lastSequence,
                    "recordCount", recordCount, "pointed", pointed, "diagnostics", diagnostics);
        }
    }
    public record Plan(List<Candidate> candidates, Candidate selected, String reason) {
        public Map<String, Object> toMap() {
            return Domain.ordered("candidates", candidates.stream().map(Candidate::toMap).toList(),
                    "selected", selected == null ? null : selected.toMap(), "reason", reason);
        }
    }

    public Plan plan(List<Path> directories, String currentId, GenerationStore store) throws IOException {
        List<Candidate> candidates = new ArrayList<>();
        for (Path directory : directories) candidates.add(inspect(directory, currentId, store));
        candidates.sort(Comparator.comparing(Candidate::generationId));
        Candidate selected = candidates.isEmpty() ? null : candidates.get(candidates.size() - 1);
        return new Plan(List.copyOf(candidates), selected,
                selected == null ? "no generation candidates" : "highest generation identifier");
    }

    private Candidate inspect(Path directory, String currentId, GenerationStore store) throws IOException {
        String id = directory.getFileName().toString(); List<String> diagnostics = new ArrayList<>();
        if (id.startsWith(".")) return new Candidate(id, directory, CandidateState.STAGING, 0, 0, 0,
                id.equals(currentId), List.of("staging directory"));
        GenerationStore.Verification verification;
        try { verification = store.verify(directory); }
        catch (IOException failure) {
            return new Candidate(id, directory, CandidateState.CORRUPT, 0, 0, 0, id.equals(currentId), List.of(failure.getMessage()));
        }
        diagnostics.addAll(verification.errors()); GenerationManifest manifest = verification.manifest();
        if (manifest == null) return new Candidate(id, directory, CandidateState.INCOMPLETE, 0, 0, 0,
                id.equals(currentId), List.copyOf(diagnostics));
        CandidateState state = verification.valid() ? manifest.schemaVersion() < GenerationStore.CURRENT_SCHEMA
                ? CandidateState.LEGACY : CandidateState.COMPLETE : CandidateState.CORRUPT;
        return new Candidate(id, directory, state, manifest.schemaVersion(), manifest.lastSequence(),
                manifest.recordCount(), id.equals(currentId), List.copyOf(diagnostics));
    }

    public Optional<Candidate> highestComplete(Plan plan) {
        return plan.candidates().stream().filter(candidate -> candidate.state() == CandidateState.COMPLETE)
                .max(Comparator.comparingLong(Candidate::lastSequence).thenComparing(Candidate::generationId));
    }

    public Optional<Candidate> pointed(Plan plan) {
        return plan.candidates().stream().filter(Candidate::pointed).findFirst();
    }

    public List<Candidate> replayCompatible(Plan plan, long journalTail) {
        return plan.candidates().stream().filter(candidate -> candidate.state() == CandidateState.COMPLETE)
                .filter(candidate -> candidate.lastSequence() <= journalTail)
                .sorted(Comparator.comparingLong(Candidate::lastSequence).reversed()).toList();
    }
}
