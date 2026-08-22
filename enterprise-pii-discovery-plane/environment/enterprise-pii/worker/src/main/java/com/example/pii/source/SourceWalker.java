package com.example.pii.source;

import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

public final class SourceWalker {
    private static final Set<String> SUPPORTED = Set.of(
            ".txt",
            ".csv",
            ".json",
            ".ndjson",
            ".xml",
            ".properties",
            ".eml",
            ".zip");

    public record SourceFile(
            String sourceId,
            Path approvedRoot,
            Path realPath,
            String canonicalIdentity,
            long bytes,
            String extension) {}

    public record WalkIssue(
            String kind,
            String path,
            String detail) {}

    public record WalkResult(
            List<SourceFile> files,
            List<WalkIssue> issues) {}

    private final long maximumFileBytes;
    private final int maximumFiles;

    public SourceWalker(long maximumFileBytes, int maximumFiles) {
        if (maximumFileBytes <= 0 || maximumFiles <= 0) throw new IllegalArgumentException("positive bounds required");
        this.maximumFileBytes = maximumFileBytes;
        this.maximumFiles = maximumFiles;
    }

    public WalkResult walk(String sourceId, Path configuredRoot) throws IOException {
        Path approved = configuredRoot.toRealPath(LinkOption.NOFOLLOW_LINKS);
        if (!Files.isDirectory(approved, LinkOption.NOFOLLOW_LINKS)) throw new IOException("source root is not a directory");
        ArrayList<SourceFile> files = new ArrayList<>();
        ArrayList<WalkIssue> issues = new ArrayList<>();
        HashSet<Object> visitedDirectories = new HashSet<>();
        Files.walkFileTree(approved, new SimpleFileVisitor<>() {
            @Override
            public FileVisitResult preVisitDirectory(Path directory, BasicFileAttributes attributes) throws IOException {
                if (Files.isSymbolicLink(directory)) {
                    issues.add(new WalkIssue("SYMLINK_DIRECTORY", identity(approved, directory), "symbolic directory skipped"));
                    return FileVisitResult.SKIP_SUBTREE;
                }
                Object key = attributes.fileKey();
                if (key != null && !visitedDirectories.add(key)) {
                    issues.add(new WalkIssue("DIRECTORY_CYCLE", identity(approved, directory), "directory identity repeated"));
                    return FileVisitResult.SKIP_SUBTREE;
                }
                return FileVisitResult.CONTINUE;
            }

            @Override
            public FileVisitResult visitFile(Path file, BasicFileAttributes attributes) throws IOException {
                if (files.size() >= maximumFiles) {
                    issues.add(new WalkIssue("FILE_COUNT_BUDGET", identity(approved, file), "source file budget reached"));
                    return FileVisitResult.TERMINATE;
                }
                if (Files.isSymbolicLink(file)) {
                    Path resolved = file.toRealPath();
                    if (!resolved.startsWith(approved)) issues.add(new WalkIssue("SYMLINK_ESCAPE", identity(approved, file), "target outside approved root"));
                    else issues.add(new WalkIssue("SYMLINK_FILE", identity(approved, file), "symbolic file skipped"));
                    return FileVisitResult.CONTINUE;
                }
                Path real = file.toRealPath(LinkOption.NOFOLLOW_LINKS);
                if (!real.startsWith(approved)) {
                    issues.add(new WalkIssue("PATH_ESCAPE", file.toString(), "canonical file outside approved root"));
                    return FileVisitResult.CONTINUE;
                }
                String extension = extension(file);
                if (!SUPPORTED.contains(extension)) {
                    issues.add(new WalkIssue("UNSUPPORTED_TYPE", identity(approved, file), extension));
                    return FileVisitResult.CONTINUE;
                }
                if (attributes.size() > maximumFileBytes) {
                    issues.add(new WalkIssue("FILE_BYTE_BUDGET", identity(approved, file), Long.toString(attributes.size())));
                    return FileVisitResult.CONTINUE;
                }
                files.add(new SourceFile(sourceId, approved, real, identity(approved, real), attributes.size(), extension));
                return FileVisitResult.CONTINUE;
            }

            @Override
            public FileVisitResult visitFileFailed(Path file, IOException exception) {
                issues.add(new WalkIssue("READ_FAILURE", identity(approved, file), exception.getClass().getSimpleName()));
                return FileVisitResult.CONTINUE;
            }
        });
        files.sort(Comparator.comparing(SourceFile::canonicalIdentity));
        issues.sort(Comparator.comparing(WalkIssue::path).thenComparing(WalkIssue::kind));
        return new WalkResult(List.copyOf(files), List.copyOf(issues));
    }

    public static String archiveIdentity(String fileIdentity, String memberName) throws IOException {
        String normalized = memberName.replace('\\', '/');
        Path member = Path.of(normalized).normalize();
        if (member.isAbsolute() || normalized.startsWith("../") || normalized.contains("/../")) throw new IOException("archive member escape");
        return fileIdentity + "!/" + member.toString().replace('\\', '/');
    }

    private static String identity(Path root, Path path) {
        try {
            Path normalized = path.toAbsolutePath().normalize();
            if (!normalized.startsWith(root)) return normalized.toString().replace('\\', '/');
            return root.relativize(normalized).toString().replace('\\', '/');
        } catch (RuntimeException exception) {
            return path.toString().replace('\\', '/');
        }
    }

    private static String extension(Path path) {
        String name = path.getFileName().toString().toLowerCase(Locale.ROOT);
        int dot = name.lastIndexOf('.');
        return dot < 0 ? "" : name.substring(dot);
    }
}