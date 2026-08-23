package com.example.pii.read;

import com.example.pii.source.SourceWalker.SourceFile;

import java.io.IOException;
import java.util.List;

public interface RecordReader {
    record Provenance(
            String sourceId,
            String canonicalPath,
            String archiveMember,
            String recordId,
            String fieldPath,
            long line,
            long byteStart,
            long byteEnd) {}

    record Field(
            Provenance provenance,
            String text,
            String mediaType) {}

    record ReadIssue(
            String kind,
            Provenance provenance,
            String detail,
            boolean recoverable) {}

    record Result(
            List<Field> fields,
            List<ReadIssue> issues,
            boolean truncated,
            String checkpoint) {}

    boolean supports(SourceFile file);

    Result read(SourceFile file, ReadBudgets budgets) throws IOException;
}