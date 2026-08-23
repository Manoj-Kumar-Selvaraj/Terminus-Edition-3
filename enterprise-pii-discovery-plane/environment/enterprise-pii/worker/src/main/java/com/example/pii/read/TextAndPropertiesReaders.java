package com.example.pii.read;

import com.example.pii.source.SourceWalker.SourceFile;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

public final class TextAndPropertiesReaders {
    public static final class TextReader implements RecordReader {
        @Override
        public boolean supports(SourceFile file) {
            return file.extension().equals(".txt");
        }

        @Override
        public Result read(SourceFile file, ReadBudgets budgets) throws IOException {
            ArrayList<Field> fields = new ArrayList<>();
            ArrayList<ReadIssue> issues = new ArrayList<>();
            long byteOffset = 0;
            long lineNumber = 0;
            var decoder = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT);
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(Files.newInputStream(file.realPath()), decoder))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    lineNumber++;
                    byte[] encoded = line.getBytes(StandardCharsets.UTF_8);
                    budgets.consumeBytes(encoded.length + 1L);
                    budgets.consumeRecord();
                    Provenance provenance = new Provenance(file.sourceId(), file.canonicalIdentity(), "", Long.toString(lineNumber), "$line", lineNumber, byteOffset, byteOffset + encoded.length);
                    fields.add(new Field(provenance, line, "text/plain"));
                    byteOffset += encoded.length + 1L;
                }
            } catch (ReadBudgets.BudgetExceeded exceeded) {
                issues.add(issue(file, lineNumber, byteOffset, "BUDGET", exceeded.getMessage()));
                return new Result(List.copyOf(fields), List.copyOf(issues), true, Long.toString(lineNumber));
            } catch (java.nio.charset.CharacterCodingException malformed) {
                issues.add(issue(file, lineNumber, byteOffset, "INVALID_UTF8", "malformed UTF-8 input"));
            }
            return new Result(List.copyOf(fields), List.copyOf(issues), false, Long.toString(lineNumber));
        }
    }

    public static final class PropertiesReader implements RecordReader {
        @Override
        public boolean supports(SourceFile file) {
            return file.extension().equals(".properties");
        }

        @Override
        public Result read(SourceFile file, ReadBudgets budgets) throws IOException {
            ArrayList<Field> fields = new ArrayList<>();
            ArrayList<ReadIssue> issues = new ArrayList<>();
            List<String> lines = Files.readAllLines(file.realPath(), StandardCharsets.UTF_8);
            long offset = 0;
            int record = 0;
            for (String line : lines) {
                record++;
                byte[] encoded = line.getBytes(StandardCharsets.UTF_8);
                try {
                    budgets.consumeBytes(encoded.length + 1L);
                    if (line.isBlank() || line.stripLeading().startsWith("#") || line.stripLeading().startsWith("!")) {
                        offset += encoded.length + 1L;
                        continue;
                    }
                    budgets.consumeRecord();
                    int separator = separator(line);
                    String key = separator < 0 ? line.strip() : line.substring(0, separator).strip();
                    String value = separator < 0 ? "" : line.substring(separator + 1).strip();
                    Provenance provenance = new Provenance(file.sourceId(), file.canonicalIdentity(), "", Integer.toString(record), "$property." + key, record, offset, offset + encoded.length);
                    fields.add(new Field(provenance, unescape(value), "text/x-java-properties"));
                } catch (ReadBudgets.BudgetExceeded exceeded) {
                    issues.add(issue(file, record, offset, "BUDGET", exceeded.getMessage()));
                    return new Result(List.copyOf(fields), List.copyOf(issues), true, Integer.toString(record));
                } catch (IllegalArgumentException malformed) {
                    if (budgets.allowError()) issues.add(issue(file, record, offset, "MALFORMED_PROPERTY", "invalid escape"));
                }
                offset += encoded.length + 1L;
            }
            return new Result(List.copyOf(fields), List.copyOf(issues), false, Integer.toString(record));
        }

        private int separator(String line) {
            boolean escaped = false;
            for (int index = 0; index < line.length(); index++) {
                char character = line.charAt(index);
                if (!escaped && (character == '=' || character == ':')) return index;
                escaped = character == '\\' && !escaped;
                if (character != '\\') escaped = false;
            }
            return -1;
        }

        private String unescape(String value) {
            return value.replace("\\n", "\n").replace("\\t", "\t").replace("\\:", ":").replace("\\=", "=").replace("\\\\", "\\");
        }
    }

    private static RecordReader.ReadIssue issue(SourceFile file, long line, long offset, String kind, String detail) {
        RecordReader.Provenance provenance = new RecordReader.Provenance(file.sourceId(), file.canonicalIdentity(), "", Long.toString(line), "", line, offset, offset);
        return new RecordReader.ReadIssue(kind, provenance, detail, true);
    }

    private TextAndPropertiesReaders() {}
}