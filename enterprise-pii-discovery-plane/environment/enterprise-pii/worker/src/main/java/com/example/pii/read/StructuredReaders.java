package com.example.pii.read;

import com.example.pii.source.SourceWalker.SourceFile;

import javax.xml.XMLConstants;
import javax.xml.parsers.SAXParserFactory;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.Map;
import org.xml.sax.Attributes;
import org.xml.sax.SAXException;
import org.xml.sax.helpers.DefaultHandler;

public final class StructuredReaders {
    public static final class CsvReader implements RecordReader {
        @Override
        public boolean supports(SourceFile file) { return file.extension().equals(".csv"); }

        @Override
        public Result read(SourceFile file, ReadBudgets budgets) throws IOException {
            ArrayList<Field> fields = new ArrayList<>();
            ArrayList<ReadIssue> issues = new ArrayList<>();
            try (BufferedReader input = Files.newBufferedReader(file.realPath(), StandardCharsets.UTF_8)) {
                CsvTokenizer tokenizer = new CsvTokenizer(input);
                List<String> headers = tokenizer.next();
                if (headers == null) return new Result(List.of(), List.of(), false, "0");
                int record = 0;
                List<String> row;
                while ((row = tokenizer.next()) != null) {
                    record++;
                    try {
                        budgets.consumeRecord();
                        budgets.consumeBytes(tokenizer.lastBytes());
                        if (row.size() != headers.size()) throw new IllegalArgumentException("column count mismatch");
                        for (int column = 0; column < row.size(); column++) {
                            Provenance provenance = new Provenance(file.sourceId(), file.canonicalIdentity(), "", Integer.toString(record), "$csv." + headers.get(column), tokenizer.lastLine(), tokenizer.lastStart(), tokenizer.lastEnd());
                            fields.add(new Field(provenance, row.get(column), "text/csv"));
                        }
                    } catch (IllegalArgumentException malformed) {
                        if (budgets.allowError()) issues.add(issue(file, record, "$row", "MALFORMED_CSV", malformed.getMessage()));
                    } catch (ReadBudgets.BudgetExceeded exceeded) {
                        issues.add(issue(file, record, "$row", "BUDGET", exceeded.getMessage()));
                        return new Result(List.copyOf(fields), List.copyOf(issues), true, Integer.toString(record));
                    }
                }
                return new Result(List.copyOf(fields), List.copyOf(issues), false, Integer.toString(record));
            }
        }
    }

    public static final class JsonReader implements RecordReader {
        @Override
        public boolean supports(SourceFile file) { return file.extension().equals(".json") || file.extension().equals(".ndjson"); }

        @Override
        public Result read(SourceFile file, ReadBudgets budgets) throws IOException {
            ArrayList<Field> fields = new ArrayList<>();
            ArrayList<ReadIssue> issues = new ArrayList<>();
            if (file.extension().equals(".ndjson")) {
                try (BufferedReader input = Files.newBufferedReader(file.realPath(), StandardCharsets.UTF_8)) {
                    String line;
                    int record = 0;
                    while ((line = input.readLine()) != null) {
                        record++;
                        try {
                            budgets.consumeRecord();
                            budgets.consumeBytes(line.getBytes(StandardCharsets.UTF_8).length + 1L);
                            Object value = new MiniJson(line, budgets).parse();
                            flatten(value, "$", file, Integer.toString(record), record, fields);
                        } catch (RuntimeException malformed) {
                            if (budgets.allowError()) issues.add(issue(file, record, "$", "MALFORMED_NDJSON", "record rejected"));
                        } catch (ReadBudgets.BudgetExceeded exceeded) {
                            issues.add(issue(file, record, "$", "BUDGET", exceeded.getMessage()));
                            return new Result(List.copyOf(fields), List.copyOf(issues), true, Integer.toString(record));
                        }
                    }
                    return new Result(List.copyOf(fields), List.copyOf(issues), false, Integer.toString(record));
                }
            }
            String content = Files.readString(file.realPath(), StandardCharsets.UTF_8);
            try {
                budgets.consumeBytes(content.getBytes(StandardCharsets.UTF_8).length);
                budgets.consumeRecord();
                flatten(new MiniJson(content, budgets).parse(), "$", file, "1", 1, fields);
            } catch (RuntimeException malformed) {
                issues.add(issue(file, 1, "$", "MALFORMED_JSON", "document rejected"));
            } catch (ReadBudgets.BudgetExceeded exceeded) {
                issues.add(issue(file, 1, "$", "BUDGET", exceeded.getMessage()));
                return new Result(List.copyOf(fields), List.copyOf(issues), true, "1");
            }
            return new Result(List.copyOf(fields), List.copyOf(issues), false, "1");
        }

        private void flatten(Object value, String path, SourceFile file, String record, long line, List<Field> fields) {
            if (value instanceof Map<?, ?> map) {
                map.entrySet().stream().sorted(java.util.Comparator.comparing(entry -> String.valueOf(entry.getKey()))).forEach(entry -> flatten(entry.getValue(), path + "." + entry.getKey(), file, record, line, fields));
            } else if (value instanceof List<?> list) {
                for (int index = 0; index < list.size(); index++) flatten(list.get(index), path + "[" + index + "]", file, record, line, fields);
            } else if (value instanceof String text) {
                fields.add(new Field(new Provenance(file.sourceId(), file.canonicalIdentity(), "", record, path, line, -1, -1), text, "application/json"));
            }
        }
    }

    public static final class XmlReader implements RecordReader {
        @Override
        public boolean supports(SourceFile file) { return file.extension().equals(".xml"); }

        @Override
        public Result read(SourceFile file, ReadBudgets budgets) throws IOException {
            ArrayList<Field> fields = new ArrayList<>();
            ArrayList<ReadIssue> issues = new ArrayList<>();
            try (InputStream input = Files.newInputStream(file.realPath())) {
                budgets.consumeBytes(file.bytes());
                SAXParserFactory factory = SAXParserFactory.newInstance();
                factory.setNamespaceAware(true);
                factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
                factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
                factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
                factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
                factory.newSAXParser().parse(input, new DefaultHandler() {
                    private final Deque<String> path = new ArrayDeque<>();
                    private final StringBuilder text = new StringBuilder();
                    private int record;

                    @Override
                    public void startElement(String uri, String local, String name, Attributes attributes) throws SAXException {
                        path.addLast(local.isEmpty() ? name : local);
                        text.setLength(0);
                        try { budgets.checkNesting(path.size()); } catch (ReadBudgets.BudgetExceeded exception) { throw new SAXException(exception); }
                        for (int index = 0; index < attributes.getLength(); index++) {
                            String field = "$xml." + String.join(".", path) + ".@" + attributes.getQName(index);
                            fields.add(new Field(new Provenance(file.sourceId(), file.canonicalIdentity(), "", Integer.toString(record), field, -1, -1, -1), attributes.getValue(index), "application/xml"));
                        }
                    }

                    @Override
                    public void characters(char[] characters, int start, int length) { text.append(characters, start, length); }

                    @Override
                    public void endElement(String uri, String local, String name) throws SAXException {
                        String value = text.toString().strip();
                        if (!value.isEmpty()) {
                            record++;
                            try { budgets.consumeRecord(); } catch (ReadBudgets.BudgetExceeded exception) { throw new SAXException(exception); }
                            String field = "$xml." + String.join(".", path);
                            fields.add(new Field(new Provenance(file.sourceId(), file.canonicalIdentity(), "", Integer.toString(record), field, -1, -1, -1), value, "application/xml"));
                        }
                        path.removeLast();
                        text.setLength(0);
                    }
                });
            } catch (ReadBudgets.BudgetExceeded exceeded) {
                issues.add(issue(file, 0, "$", "BUDGET", exceeded.getMessage()));
                return new Result(List.copyOf(fields), List.copyOf(issues), true, Integer.toString(fields.size()));
            } catch (Exception malformed) {
                issues.add(issue(file, 0, "$", "MALFORMED_XML", "document rejected"));
            }
            return new Result(List.copyOf(fields), List.copyOf(issues), false, Integer.toString(fields.size()));
        }
    }

    private static RecordReader.ReadIssue issue(SourceFile file, long record, String field, String kind, String detail) {
        return new RecordReader.ReadIssue(kind, new RecordReader.Provenance(file.sourceId(), file.canonicalIdentity(), "", Long.toString(record), field, record, -1, -1), detail, true);
    }

    private StructuredReaders() {}
}