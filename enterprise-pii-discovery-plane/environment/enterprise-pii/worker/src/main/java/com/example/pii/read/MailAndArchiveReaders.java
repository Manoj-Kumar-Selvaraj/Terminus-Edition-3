package com.example.pii.read;

import com.example.pii.source.SourceWalker;
import com.example.pii.source.SourceWalker.SourceFile;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

public final class MailAndArchiveReaders {
    public static final class EmailReader implements RecordReader {
        @Override
        public boolean supports(SourceFile file) {
            return file.extension().equals(".eml");
        }

        @Override
        public Result read(SourceFile file, ReadBudgets budgets) throws IOException {
            byte[] content = Files.readAllBytes(file.realPath());
            budgets.consumeBytes(content.length);
            return readMessage(file.sourceId(), file.canonicalIdentity(), "", content, budgets);
        }

        Result readMessage(String sourceId, String path, String member, byte[] content, ReadBudgets budgets) throws IOException {
            ArrayList<Field> fields = new ArrayList<>();
            ArrayList<ReadIssue> issues = new ArrayList<>();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(new ByteArrayInputStream(content), StandardCharsets.UTF_8))) {
                Map<String, StringBuilder> headers = new LinkedHashMap<>();
                String current = "";
                String line;
                long lineNumber = 0;
                long offset = 0;
                while ((line = reader.readLine()) != null) {
                    lineNumber++;
                    if (line.isEmpty()) break;
                    if ((line.startsWith(" ") || line.startsWith("\t")) && !current.isEmpty()) {
                        headers.get(current).append(' ').append(line.strip());
                    } else {
                        int colon = line.indexOf(':');
                        if (colon <= 0) {
                            if (budgets.allowError()) issues.add(issue(sourceId, path, member, lineNumber, "MALFORMED_HEADER", "header omitted"));
                            continue;
                        }
                        current = line.substring(0, colon).strip().toLowerCase(Locale.ROOT);
                        headers.computeIfAbsent(current, ignored -> new StringBuilder()).append(line.substring(colon + 1).strip());
                    }
                    offset += line.getBytes(StandardCharsets.UTF_8).length + 1L;
                }
                for (Map.Entry<String, StringBuilder> header : headers.entrySet()) {
                    budgets.consumeRecord();
                    Provenance provenance = new Provenance(sourceId, path, member, "headers", "$email.header." + header.getKey(), 1, 0, offset);
                    fields.add(new Field(provenance, header.getValue().toString(), "message/rfc822"));
                }
                StringBuilder body = new StringBuilder();
                while ((line = reader.readLine()) != null) {
                    lineNumber++;
                    body.append(line).append('\n');
                }
                String transfer = value(headers, "content-transfer-encoding").toLowerCase(Locale.ROOT);
                String decoded = decodeBody(body.toString(), transfer, issues, sourceId, path, member, lineNumber);
                budgets.consumeRecord();
                fields.add(new Field(new Provenance(sourceId, path, member, "body", "$email.body", lineNumber, offset, content.length), decoded, "message/rfc822"));
            } catch (ReadBudgets.BudgetExceeded exceeded) {
                issues.add(issue(sourceId, path, member, 0, "BUDGET", exceeded.getMessage()));
                return new Result(List.copyOf(fields), List.copyOf(issues), true, Integer.toString(fields.size()));
            }
            return new Result(List.copyOf(fields), List.copyOf(issues), false, Integer.toString(fields.size()));
        }

        private String value(Map<String, StringBuilder> headers, String name) {
            StringBuilder value = headers.get(name);
            return value == null ? "" : value.toString();
        }

        private String decodeBody(String body, String transfer, List<ReadIssue> issues, String source, String path, String member, long line) {
            try {
                if (transfer.equals("base64")) return new String(Base64.getMimeDecoder().decode(body), StandardCharsets.UTF_8);
                if (transfer.equals("quoted-printable")) return quotedPrintable(body);
                return body;
            } catch (IllegalArgumentException malformed) {
                issues.add(issue(source, path, member, line, "MALFORMED_BODY_ENCODING", "encoded body omitted"));
                return "";
            }
        }

        private String quotedPrintable(String input) {
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            for (int index = 0; index < input.length(); index++) {
                char character = input.charAt(index);
                if (character == '=' && index + 2 < input.length()) {
                    if (input.charAt(index + 1) == '\r' || input.charAt(index + 1) == '\n') {
                        while (index + 1 < input.length() && (input.charAt(index + 1) == '\r' || input.charAt(index + 1) == '\n')) index++;
                        continue;
                    }
                    int high = Character.digit(input.charAt(index + 1), 16);
                    int low = Character.digit(input.charAt(index + 2), 16);
                    if (high >= 0 && low >= 0) {
                        output.write((high << 4) | low);
                        index += 2;
                        continue;
                    }
                }
                output.writeBytes(String.valueOf(character).getBytes(StandardCharsets.UTF_8));
            }
            return output.toString(StandardCharsets.UTF_8);
        }
    }

    public static final class ZipReader implements RecordReader {
        private final List<RecordReader> memberReaders;

        public ZipReader(List<RecordReader> memberReaders) {
            this.memberReaders = List.copyOf(memberReaders);
        }

        @Override
        public boolean supports(SourceFile file) {
            return file.extension().equals(".zip");
        }

        @Override
        public Result read(SourceFile file, ReadBudgets budgets) throws IOException {
            ArrayList<Field> fields = new ArrayList<>();
            ArrayList<ReadIssue> issues = new ArrayList<>();
            boolean truncated = false;
            try (ZipInputStream input = new ZipInputStream(new BufferedInputStream(Files.newInputStream(file.realPath())), StandardCharsets.UTF_8)) {
                ZipEntry entry;
                while ((entry = input.getNextEntry()) != null) {
                    if (entry.isDirectory()) continue;
                    String identity;
                    try {
                        identity = SourceWalker.archiveIdentity(file.canonicalIdentity(), entry.getName());
                    } catch (IOException escape) {
                        if (budgets.allowError()) issues.add(issue(file.sourceId(), file.canonicalIdentity(), entry.getName(), 0, "ARCHIVE_ESCAPE", "member skipped"));
                        continue;
                    }
                    byte[] body;
                    try {
                        body = boundedEntry(input, budgets);
                        budgets.consumeArchiveEntry(body.length);
                    } catch (ReadBudgets.BudgetExceeded exceeded) {
                        issues.add(issue(file.sourceId(), file.canonicalIdentity(), entry.getName(), 0, "BUDGET", exceeded.getMessage()));
                        truncated = true;
                        break;
                    }
                    String extension = extension(entry.getName());
                    if (extension.equals(".txt") || extension.equals(".properties") || extension.equals(".csv") || extension.equals(".json") || extension.equals(".ndjson") || extension.equals(".xml")) {
                        extractPlain(file, identity, entry.getName(), extension, body, budgets, fields, issues);
                    } else if (extension.equals(".eml")) {
                        Result nested = new EmailReader().readMessage(file.sourceId(), file.canonicalIdentity(), entry.getName(), body, budgets);
                        fields.addAll(nested.fields());
                        issues.addAll(nested.issues());
                        truncated |= nested.truncated();
                    } else if (budgets.allowError()) {
                        issues.add(issue(file.sourceId(), file.canonicalIdentity(), entry.getName(), 0, "UNSUPPORTED_ARCHIVE_MEMBER", "member skipped"));
                    }
                }
            }
            return new Result(List.copyOf(fields), List.copyOf(issues), truncated, Integer.toString(fields.size()));
        }

        private byte[] boundedEntry(ZipInputStream input, ReadBudgets budgets) throws IOException {
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) >= 0) {
                output.write(buffer, 0, count);
                if (output.size() > 67_108_864) throw new ReadBudgets.BudgetExceeded("archive_member_bytes", 67_108_864, output.size());
                budgets.checkTime();
            }
            return output.toByteArray();
        }

        private void extractPlain(SourceFile source, String identity, String member, String extension, byte[] body, ReadBudgets budgets, List<Field> fields, List<ReadIssue> issues) {
            String text = new String(body, StandardCharsets.UTF_8);
            String[] lines = text.split("\\R", -1);
            long offset = 0;
            for (int index = 0; index < lines.length; index++) {
                try {
                    budgets.consumeRecord();
                    byte[] encoded = lines[index].getBytes(StandardCharsets.UTF_8);
                    fields.add(new Field(new Provenance(source.sourceId(), source.canonicalIdentity(), member, Integer.toString(index + 1), "$archive" + extension, index + 1L, offset, offset + encoded.length), lines[index], media(extension)));
                    offset += encoded.length + 1L;
                } catch (ReadBudgets.BudgetExceeded exceeded) {
                    issues.add(issue(source.sourceId(), identity, member, index + 1L, "BUDGET", exceeded.getMessage()));
                    return;
                }
            }
        }

        private String media(String extension) {
            return switch (extension) {
                case ".csv" -> "text/csv";
                case ".json", ".ndjson" -> "application/json";
                case ".xml" -> "application/xml";
                default -> "text/plain";
            };
        }

        private String extension(String name) {
            int dot = name.lastIndexOf('.');
            return dot < 0 ? "" : name.substring(dot).toLowerCase(Locale.ROOT);
        }
    }

    private static RecordReader.ReadIssue issue(String source, String path, String member, long line, String kind, String detail) {
        return new RecordReader.ReadIssue(kind, new RecordReader.Provenance(source, path, member, Long.toString(line), "", line, -1, -1), detail, true);
    }

    private MailAndArchiveReaders() {}
}