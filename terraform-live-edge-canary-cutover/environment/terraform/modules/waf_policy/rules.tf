locals {
  rule_catalog = {
    "owasp-sqli-union" = {
      id              = "owasp-sqli-union"
      action          = "block"
      match           = "(?i)(union\\s+select|select.+from)"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-sqli-union in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-sqli-union",
      ]
    }
    "owasp-sqli-comment" = {
      id              = "owasp-sqli-comment"
      action          = "block"
      match           = "(?i)(--|#|/\\*).*(sleep|benchmark)"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-sqli-comment in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-sqli-comment",
      ]
    }
    "owasp-sqli-tautology" = {
      id              = "owasp-sqli-tautology"
      action          = "block"
      match           = "(?i)('\\s*or\\s+'1'\\s*=\\s*'1)"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-sqli-tautology in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-sqli-tautology",
      ]
    }
    "owasp-sqli-stacked" = {
      id              = "owasp-sqli-stacked"
      action          = "block"
      match           = "(?i);\\s*(drop|alter|create)\\s+"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-sqli-stacked in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-sqli-stacked",
      ]
    }
    "owasp-xss-script" = {
      id              = "owasp-xss-script"
      action          = "block"
      match           = "(?i)<script[^>]*>"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-xss-script in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "high",
        "owasp-xss-script",
      ]
    }
    "owasp-xss-img-onerror" = {
      id              = "owasp-xss-img-onerror"
      action          = "block"
      match           = "(?i)<img[^>]+onerror\\s*="
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-xss-img-onerror in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "high",
        "owasp-xss-img-onerror",
      ]
    }
    "owasp-xss-svg-onload" = {
      id              = "owasp-xss-svg-onload"
      action          = "block"
      match           = "(?i)<svg[^>]+onload\\s*="
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-xss-svg-onload in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "high",
        "owasp-xss-svg-onload",
      ]
    }
    "owasp-xss-javascript-uri" = {
      id              = "owasp-xss-javascript-uri"
      action          = "block"
      match           = "(?i)javascript\\s*:"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-xss-javascript-uri in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "high",
        "owasp-xss-javascript-uri",
      ]
    }
    "owasp-xss-event-handler" = {
      id              = "owasp-xss-event-handler"
      action          = "block"
      match           = "(?i)\\bon(click|load|error|mouseover)\\s*="
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-xss-event-handler in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "high",
        "owasp-xss-event-handler",
      ]
    }
    "owasp-rce-bash" = {
      id              = "owasp-rce-bash"
      action          = "block"
      match           = "(?i)(;|\\||\\&)\\s*(bash|sh|zsh)\\b"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-rce-bash in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-rce-bash",
      ]
    }
    "owasp-rce-curl-pipe" = {
      id              = "owasp-rce-curl-pipe"
      action          = "block"
      match           = "(?i)curl\\s+[^\\n]+\\|\\s*(sh|bash)"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-rce-curl-pipe in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-rce-curl-pipe",
      ]
    }
    "owasp-rce-wget" = {
      id              = "owasp-rce-wget"
      action          = "block"
      match           = "(?i)wget\\s+(-O|-o)\\s*/tmp/"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-rce-wget in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-rce-wget",
      ]
    }
    "owasp-rce-powershell" = {
      id              = "owasp-rce-powershell"
      action          = "block"
      match           = "(?i)powershell\\s+-enc\\s+"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-rce-powershell in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-rce-powershell",
      ]
    }
    "owasp-path-traversal" = {
      id              = "owasp-path-traversal"
      action          = "block"
      match           = "(?i)(\\.\\./|\\.\\.\\\\){2,}"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-path-traversal in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "high",
        "owasp-path-traversal",
      ]
    }
    "owasp-path-etc-passwd" = {
      id              = "owasp-path-etc-passwd"
      action          = "block"
      match           = "(?i)/etc/(passwd|shadow)"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-path-etc-passwd in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "high",
        "owasp-path-etc-passwd",
      ]
    }
    "owasp-path-windows" = {
      id              = "owasp-path-windows"
      action          = "block"
      match           = "(?i)(c:\\\\windows\\\\|%systemroot%)"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-path-windows in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "high",
        "owasp-path-windows",
      ]
    }
    "owasp-lfi-php-filter" = {
      id              = "owasp-lfi-php-filter"
      action          = "block"
      match           = "(?i)php://filter"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-lfi-php-filter in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "high",
        "owasp-lfi-php-filter",
      ]
    }
    "owasp-lfi-file-wrap" = {
      id              = "owasp-lfi-file-wrap"
      action          = "block"
      match           = "(?i)file://"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-lfi-file-wrap in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "high",
        "owasp-lfi-file-wrap",
      ]
    }
    "owasp-ssrf-metadata" = {
      id              = "owasp-ssrf-metadata"
      action          = "block"
      match           = "(?i)169\\.254\\.169\\.254"
      owasp_id        = "A10:2021"
      threat_class    = "ssrf"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-ssrf-metadata in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "ssrf",
        "critical",
        "owasp-ssrf-metadata",
      ]
    }
    "owasp-ssrf-localhost" = {
      id              = "owasp-ssrf-localhost"
      action          = "block"
      match           = "(?i)(https?://)?(127\\.0\\.0\\.1|localhost)(:\\d+)?/"
      owasp_id        = "A10:2021"
      threat_class    = "ssrf"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-ssrf-localhost in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "ssrf",
        "critical",
        "owasp-ssrf-localhost",
      ]
    }
    "owasp-ssrf-link-local" = {
      id              = "owasp-ssrf-link-local"
      action          = "block"
      match           = "(?i)169\\.254\\.\\d+\\.\\d+"
      owasp_id        = "A10:2021"
      threat_class    = "ssrf"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-ssrf-link-local in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "ssrf",
        "critical",
        "owasp-ssrf-link-local",
      ]
    }
    "owasp-xxe-doctype" = {
      id              = "owasp-xxe-doctype"
      action          = "block"
      match           = "(?i)<!DOCTYPE[^>]+SYSTEM"
      owasp_id        = "A05:2021"
      threat_class    = "security-misconfig"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-xxe-doctype in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "security-misconfig",
        "high",
        "owasp-xxe-doctype",
      ]
    }
    "owasp-xxe-entity" = {
      id              = "owasp-xxe-entity"
      action          = "block"
      match           = "(?i)<!ENTITY\\s+\\w+\\s+SYSTEM"
      owasp_id        = "A05:2021"
      threat_class    = "security-misconfig"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-xxe-entity in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "security-misconfig",
        "high",
        "owasp-xxe-entity",
      ]
    }
    "owasp-deserialization-java" = {
      id              = "owasp-deserialization-java"
      action          = "block"
      match           = "rO0AB"
      owasp_id        = "A08:2021"
      threat_class    = "software-integrity"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-deserialization-java in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "software-integrity",
        "critical",
        "owasp-deserialization-java",
      ]
    }
    "owasp-deserialization-php" = {
      id              = "owasp-deserialization-php"
      action          = "block"
      match           = "(?i)O:\\d+:\\\""
      owasp_id        = "A08:2021"
      threat_class    = "software-integrity"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-deserialization-php in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "software-integrity",
        "critical",
        "owasp-deserialization-php",
      ]
    }
    "owasp-cmdi-nc" = {
      id              = "owasp-cmdi-nc"
      action          = "block"
      match           = "(?i)\\bnc\\s+-e\\b"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-cmdi-nc in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-cmdi-nc",
      ]
    }
    "owasp-cmdi-perl" = {
      id              = "owasp-cmdi-perl"
      action          = "block"
      match           = "(?i)perl\\s+-e\\s+'"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-cmdi-perl in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-cmdi-perl",
      ]
    }
    "owasp-cmdi-python-os" = {
      id              = "owasp-cmdi-python-os"
      action          = "block"
      match           = "(?i)os\\.system\\s*\\("
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-cmdi-python-os in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-cmdi-python-os",
      ]
    }
    "owasp-open-redirect" = {
      id              = "owasp-open-redirect"
      action          = "block"
      match           = "(?i)(url|redirect|next)=(https?:)?//"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-open-redirect in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "medium",
        "owasp-open-redirect",
      ]
    }
    "owasp-header-injection" = {
      id              = "owasp-header-injection"
      action          = "block"
      match           = "(?i)(%0d%0a|\\r\\n)(set-cookie|location):"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-header-injection in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "medium",
        "owasp-header-injection",
      ]
    }
    "owasp-csrf-token-missing" = {
      id              = "owasp-csrf-token-missing"
      action          = "allow"
      match           = "(?i)X-CSRF-Token:\\s*\\S+"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-csrf-token-missing in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "medium",
        "owasp-csrf-token-missing",
      ]
    }
    "owasp-bot-scanner-nikto" = {
      id              = "owasp-bot-scanner-nikto"
      action          = "block"
      match           = "(?i)\\bNikto\\b"
      owasp_id        = "A04:2021"
      threat_class    = "insecure-design"
      severity        = "low"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-bot-scanner-nikto in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "insecure-design",
        "low",
        "owasp-bot-scanner-nikto",
      ]
    }
    "owasp-bot-scanner-sqlmap" = {
      id              = "owasp-bot-scanner-sqlmap"
      action          = "block"
      match           = "(?i)\\bsqlmap\\b"
      owasp_id        = "A04:2021"
      threat_class    = "insecure-design"
      severity        = "low"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-bot-scanner-sqlmap in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "insecure-design",
        "low",
        "owasp-bot-scanner-sqlmap",
      ]
    }
    "owasp-bot-scanner-nmap" = {
      id              = "owasp-bot-scanner-nmap"
      action          = "block"
      match           = "(?i)\\bNmap Scripting Engine\\b"
      owasp_id        = "A04:2021"
      threat_class    = "insecure-design"
      severity        = "low"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-bot-scanner-nmap in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "insecure-design",
        "low",
        "owasp-bot-scanner-nmap",
      ]
    }
    "owasp-protocol-smuggle" = {
      id              = "owasp-protocol-smuggle"
      action          = "block"
      match           = "(?i)Transfer-Encoding:\\s*chunked"
      owasp_id        = "A05:2021"
      threat_class    = "security-misconfig"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-protocol-smuggle in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "security-misconfig",
        "high",
        "owasp-protocol-smuggle",
      ]
    }
    "owasp-http-request-smuggle" = {
      id              = "owasp-http-request-smuggle"
      action          = "block"
      match           = "(?i)Content-Length:\\s*\\d+.+Transfer-Encoding"
      owasp_id        = "A05:2021"
      threat_class    = "security-misconfig"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-http-request-smuggle in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "security-misconfig",
        "high",
        "owasp-http-request-smuggle",
      ]
    }
    "owasp-ldap-injection" = {
      id              = "owasp-ldap-injection"
      action          = "block"
      match           = "(?i)(\\*\\)\\(|\\)\\(uid=)"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-ldap-injection in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "high",
        "owasp-ldap-injection",
      ]
    }
    "owasp-nosql-injection" = {
      id              = "owasp-nosql-injection"
      action          = "block"
      match           = "(?i)\\$where\\s*:"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-nosql-injection in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "high",
        "owasp-nosql-injection",
      ]
    }
    "owasp-template-ssti" = {
      id              = "owasp-template-ssti"
      action          = "block"
      match           = "(?i)\\{\\{.*(__import__|config).*\\}\\}"
      owasp_id        = "A03:2021"
      threat_class    = "injection"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-template-ssti in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "injection",
        "critical",
        "owasp-template-ssti",
      ]
    }
    "owasp-log4shell" = {
      id              = "owasp-log4shell"
      action          = "block"
      match           = "(?i)\\$\\{jndi:(ldap|rmi|dns):"
      owasp_id        = "A06:2021"
      threat_class    = "vulnerable-components"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-log4shell in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "vulnerable-components",
        "critical",
        "owasp-log4shell",
      ]
    }
    "owasp-spring4shell" = {
      id              = "owasp-spring4shell"
      action          = "block"
      match           = "(?i)class\\.module\\.classLoader"
      owasp_id        = "A06:2021"
      threat_class    = "vulnerable-components"
      severity        = "critical"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-spring4shell in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "vulnerable-components",
        "critical",
        "owasp-spring4shell",
      ]
    }
    "owasp-graphql-introspection" = {
      id              = "owasp-graphql-introspection"
      action          = "block"
      match           = "(?i)__schema\\s*\\{"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-graphql-introspection in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "medium",
        "owasp-graphql-introspection",
      ]
    }
    "owasp-graphql-batch" = {
      id              = "owasp-graphql-batch"
      action          = "block"
      match           = "(?i)\\\"query\\\".*\\\"query\\\""
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-graphql-batch in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "medium",
        "owasp-graphql-batch",
      ]
    }
    "owasp-api-mass-assign" = {
      id              = "owasp-api-mass-assign"
      action          = "block"
      match           = "(?i)\\\"(is_admin|role|permissions)\\\"\\s*:"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-api-mass-assign in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "medium",
        "owasp-api-mass-assign",
      ]
    }
    "owasp-jwt-none-alg" = {
      id              = "owasp-jwt-none-alg"
      action          = "block"
      match           = "(?i)\\\"alg\\\"\\s*:\\s*\\\"none\\\""
      owasp_id        = "A02:2021"
      threat_class    = "cryptographic-failures"
      severity        = "high"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-jwt-none-alg in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "cryptographic-failures",
        "high",
        "owasp-jwt-none-alg",
      ]
    }
    "owasp-cors-wildcard" = {
      id              = "owasp-cors-wildcard"
      action          = "block"
      match           = "(?i)Access-Control-Allow-Origin:\\s*\\*"
      owasp_id        = "A05:2021"
      threat_class    = "security-misconfig"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-cors-wildcard in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "security-misconfig",
        "medium",
        "owasp-cors-wildcard",
      ]
    }
    "owasp-sensitive-backup" = {
      id              = "owasp-sensitive-backup"
      action          = "block"
      match           = "(?i)\\.(bak|old|sql|dump|git)(\\?|$)"
      owasp_id        = "A01:2021"
      threat_class    = "broken-access"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-sensitive-backup in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "broken-access",
        "medium",
        "owasp-sensitive-backup",
      ]
    }
    "owasp-phpinfo" = {
      id              = "owasp-phpinfo"
      action          = "block"
      match           = "(?i)phpinfo\\s*\\(\\s*\\)"
      owasp_id        = "A05:2021"
      threat_class    = "security-misconfig"
      severity        = "low"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-phpinfo in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "security-misconfig",
        "low",
        "owasp-phpinfo",
      ]
    }
    "owasp-debug-trace" = {
      id              = "owasp-debug-trace"
      action          = "block"
      match           = "(?i)^(TRACE|TRACK)\\s+"
      owasp_id        = "A05:2021"
      threat_class    = "security-misconfig"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-debug-trace in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "security-misconfig",
        "medium",
        "owasp-debug-trace",
      ]
    }
    "owasp-method-override" = {
      id              = "owasp-method-override"
      action          = "block"
      match           = "(?i)X-HTTP-Method-Override:\\s*(PUT|DELETE)"
      owasp_id        = "A05:2021"
      threat_class    = "security-misconfig"
      severity        = "medium"
      parity_required = true
      apply_phases    = ["request-header", "request-body", "query-string"]
      false_positive_notes = [
        "Tune owasp-method-override in detect mode before promoting to enforce on unfamiliar traffic.",
        "Keep allowlist exceptions scoped to engagement ${var.engagement} only.",
      ]
      signal_tags = [
        "security-misconfig",
        "medium",
        "owasp-method-override",
      ]
    }
  }

  api_rules = [
    for r in var.waf.rules : {
      id     = r.id
      action = r.action
      match  = r.match
    }
  ]

  rule_ids = [for r in local.api_rules : r.id]

  body = {
    id    = var.waf.id
    mode  = var.final_mode
    rules = local.api_rules
  }

  marker = sha256(jsonencode(local.body))
  payload_path = "${var.payload_dir}/${var.waf.id}.json"

  severity_counts = {
    critical = length([for id, r in local.rule_catalog : id if r.severity == "critical"])
    high     = length([for id, r in local.rule_catalog : id if r.severity == "high"])
    medium   = length([for id, r in local.rule_catalog : id if r.severity == "medium"])
    low      = length([for id, r in local.rule_catalog : id if r.severity == "low"])
  }
}
