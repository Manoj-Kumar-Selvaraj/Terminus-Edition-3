package com.example.pii.detect;

import com.example.pii.read.RecordReader.Field;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class Detection {
    public record Candidate(
            String category,
            String rawValue,
            String normalizedValue,
            int start,
            int end,
            double confidence,
            String revision,
            Map<String, String> context) {}

    public interface Detector {
        String category();
        String revision();
        List<Candidate> detect(Field field, DetectionContext context);
    }

    public record DetectionContext(
            String region,
            double minimumConfidence,
            Set<String> positiveLabels,
            Set<String> negativeLabels) {
        public double contextualScore(String text, int start, int end, double base) {
            int from = Math.max(0, start - 48);
            int to = Math.min(text.length(), end + 48);
            String window = text.substring(from, to).toLowerCase(Locale.ROOT);
            double score = base;
            for (String label : positiveLabels) if (window.contains(label.toLowerCase(Locale.ROOT))) score += 0.08;
            for (String label : negativeLabels) if (window.contains(label.toLowerCase(Locale.ROOT))) score -= 0.20;
            return Math.max(0.0, Math.min(1.0, score));
        }
    }

    public abstract static class PatternDetector implements Detector {
        private final String category;
        private final String revision;
        private final Pattern pattern;
        private final double baseConfidence;

        protected PatternDetector(String category, String revision, String regex, double baseConfidence) {
            this.category = category;
            this.revision = revision;
            this.pattern = Pattern.compile(regex, Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);
            this.baseConfidence = baseConfidence;
        }

        @Override public String category() { return category; }
        @Override public String revision() { return revision; }

        @Override
        public List<Candidate> detect(Field field, DetectionContext context) {
            ArrayList<Candidate> output = new ArrayList<>();
            Matcher matcher = pattern.matcher(field.text());
            while (matcher.find()) {
                String raw = matcher.group();
                String normalized = normalize(raw);
                if (!validate(raw, normalized, context)) continue;
                double confidence = context.contextualScore(field.text(), matcher.start(), matcher.end(), baseConfidence);
                if (confidence < context.minimumConfidence()) continue;
                output.add(new Candidate(category, raw, normalized, matcher.start(), matcher.end(), confidence, revision, Map.of("field", field.provenance().fieldPath())));
            }
            return output;
        }

        protected String normalize(String raw) {
            return Normalizer.normalize(raw, Normalizer.Form.NFKC).strip();
        }

        protected boolean validate(String raw, String normalized, DetectionContext context) { return true; }
    }

    public static final class EmailDetector extends PatternDetector {
        public EmailDetector() { super("EMAIL", "email-3", "(?<![\\p{L}\\p{N}._%+-])[\\p{L}\\p{N}._%+-]+@[\\p{L}\\p{N}.-]+\\.[\\p{L}]{2,24}(?![\\p{L}\\p{N}._%+-])", 0.92); }
        @Override protected String normalize(String raw) { return super.normalize(raw).toLowerCase(Locale.ROOT); }
        @Override protected boolean validate(String raw, String normalized, DetectionContext context) {
            int at = normalized.lastIndexOf('@');
            return at > 0 && at < normalized.length() - 3 && !normalized.contains("..") && !normalized.endsWith(".invalid");
        }
    }

    public static final class PhoneDetector extends PatternDetector {
        public PhoneDetector() { super("PHONE", "phone-4", "(?<!\\d)\\+?[1-9](?:[ .()-]*\\d){7,14}(?!\\d)", 0.76); }
        @Override protected String normalize(String raw) { String digits = raw.replaceAll("\\D", ""); return raw.strip().startsWith("+") ? "+" + digits : digits; }
        @Override protected boolean validate(String raw, String normalized, DetectionContext context) {
            int digits = normalized.replace("+", "").length();
            if (digits < 8 || digits > 15) return false;
            return normalized.startsWith("+") || context.region().equalsIgnoreCase("na");
        }
    }

    public static final class SsnDetector extends PatternDetector {
        public SsnDetector() { super("US_SSN", "ssn-5", "(?<!\\d)(?:\\d{3}[- ]?\\d{2}[- ]?\\d{4})(?!\\d)", 0.82); }
        @Override protected String normalize(String raw) { return raw.replaceAll("\\D", ""); }
        @Override protected boolean validate(String raw, String value, DetectionContext context) {
            if (!context.region().equalsIgnoreCase("na") || value.length() != 9) return false;
            int area = Integer.parseInt(value.substring(0, 3));
            int group = Integer.parseInt(value.substring(3, 5));
            int serial = Integer.parseInt(value.substring(5));
            return area != 0 && area != 666 && area < 900 && group != 0 && serial != 0;
        }
    }

    public static final class CardDetector extends PatternDetector {
        public CardDetector() { super("PAYMENT_CARD", "card-6", "(?<!\\d)(?:\\d[ -]?){13,19}(?!\\d)", 0.84); }
        @Override protected String normalize(String raw) { return raw.replaceAll("\\D", ""); }
        @Override protected boolean validate(String raw, String value, DetectionContext context) {
            if (value.length() < 13 || value.length() > 19 || !issuer(value)) return false;
            int sum = 0;
            boolean doubleDigit = false;
            for (int index = value.length() - 1; index >= 0; index--) {
                int digit = value.charAt(index) - '0';
                if (doubleDigit) { digit *= 2; if (digit > 9) digit -= 9; }
                sum += digit;
                doubleDigit = !doubleDigit;
            }
            return sum % 10 == 0;
        }
        private boolean issuer(String value) {
            return value.startsWith("4") || value.matches("5[1-5].*") || value.matches("3[47].*") || value.matches("6(?:011|5).*" );
        }
    }

    public static final class IbanDetector extends PatternDetector {
        public IbanDetector() { super("IBAN", "iban-4", "(?<![A-Z0-9])[A-Z]{2}\\d{2}(?:[ ]?[A-Z0-9]){11,30}(?![A-Z0-9])", 0.87); }
        @Override protected String normalize(String raw) { return raw.replaceAll("\\s", "").toUpperCase(Locale.ROOT); }
        @Override protected boolean validate(String raw, String value, DetectionContext context) {
            if (value.length() < 15 || value.length() > 34) return false;
            String rearranged = value.substring(4) + value.substring(0, 4);
            int remainder = 0;
            for (char character : rearranged.toCharArray()) {
                String digits = Character.isLetter(character) ? Integer.toString(character - 'A' + 10) : String.valueOf(character);
                for (char digit : digits.toCharArray()) remainder = (remainder * 10 + digit - '0') % 97;
            }
            return remainder == 1;
        }
    }

    public static final class ContextIdDetector extends PatternDetector {
        private final Set<String> required;
        public ContextIdDetector(String category, String revision, String regex, Set<String> required) {
            super(category, revision, regex, 0.68);
            this.required = required;
        }
        @Override protected String normalize(String raw) { return raw.replaceAll("[^\\p{L}\\p{N}]", "").toUpperCase(Locale.ROOT); }
        @Override protected boolean validate(String raw, String value, DetectionContext context) { return value.length() >= 6 && context.positiveLabels().stream().anyMatch(required::contains); }
    }

    public static final class DateOfBirthDetector extends PatternDetector {
        public DateOfBirthDetector() { super("DOB", "dob-3", "(?<!\\d)(?:19|20)\\d{2}[-/](?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\\d|3[01])(?!\\d)", 0.66); }
    }

    public static final class AddressDetector extends PatternDetector {
        public AddressDetector() { super("ADDRESS", "address-3", "(?<!\\w)\\d{1,6}\\s+[\\p{L}0-9 .'-]{2,50}\\s+(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Boulevard|Blvd)(?!\\w)", 0.78); }
    }

    public static final class PersonNameDetector extends PatternDetector {
        public PersonNameDetector() { super("PERSON_NAME", "name-2", "(?<!\\p{L})\\p{Lu}[\\p{Ll}'-]{1,30}\\s+\\p{Lu}[\\p{Ll}'-]{1,30}(?!\\p{L})", 0.62); }
    }

    public static final class Registry {
        private final Map<String, Detector> detectors = new LinkedHashMap<>();

        public Registry register(Detector detector) {
            if (detectors.putIfAbsent(detector.category(), detector) != null) throw new IllegalArgumentException("duplicate detector category");
            return this;
        }

        public List<Candidate> detect(Field field, DetectionContext context, Set<String> enabled) {
            ArrayList<Candidate> candidates = new ArrayList<>();
            for (Detector detector : detectors.values()) if (enabled.contains(detector.category())) candidates.addAll(detector.detect(field, context));
            return resolve(candidates);
        }

        private List<Candidate> resolve(List<Candidate> candidates) {
            candidates.sort(Comparator.comparingInt(Candidate::start)
                    .thenComparing(Comparator.comparingDouble(Candidate::confidence).reversed())
                    .thenComparingInt(candidate -> candidate.end() - candidate.start())
                    .thenComparing(Candidate::category));
            ArrayList<Candidate> accepted = new ArrayList<>();
            for (Candidate candidate : candidates) {
                boolean overlaps = accepted.stream().anyMatch(existing -> existing.start() < candidate.end() && candidate.start() < existing.end());
                if (!overlaps) accepted.add(candidate);
            }
            accepted.sort(Comparator.comparingInt(Candidate::start).thenComparing(Candidate::category));
            return List.copyOf(accepted);
        }

        public static Registry builtins() {
            return new Registry()
                    .register(new EmailDetector())
                    .register(new PhoneDetector())
                    .register(new SsnDetector())
                    .register(new CardDetector())
                    .register(new IbanDetector())
                    .register(new ContextIdDetector("PASSPORT", "passport-3", "(?<![A-Z0-9])[A-Z]{1,2}[0-9]{6,9}(?![A-Z0-9])", Set.of("passport")))
                    .register(new ContextIdDetector("TAX_ID", "tax-3", "(?<![A-Z0-9])[A-Z0-9-]{8,15}(?![A-Z0-9])", Set.of("tax", "tin", "vat")))
                    .register(new DateOfBirthDetector())
                    .register(new AddressDetector())
                    .register(new PersonNameDetector());
        }
    }

    private Detection() {}
}