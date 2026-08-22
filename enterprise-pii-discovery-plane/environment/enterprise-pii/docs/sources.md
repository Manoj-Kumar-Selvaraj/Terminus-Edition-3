# Source and Parsing Contract

Canonical source identity is relative to an approved real root and includes archive member identity. Walking never follows a path or symlink outside that root. Files are opened read-only and never renamed, touched, quarantined, or rewritten.

Supported inputs are UTF-8 text, CSV, JSON, NDJSON, XML, Java properties, RFC-style email, and ZIP containers of supported bounded entries. BOMs are recognized. Invalid UTF-8 is isolated and reported without shifting adjacent valid offsets. CSV quoting, nested JSON paths, XML text nodes, properties keys, email headers and body parts retain field-level provenance.

Readers enforce bytes, records, nesting, archive entries, expanded bytes, matches, errors, memory, and elapsed time at deterministic boundaries. A malformed record does not abort adjacent records. Every skipped, malformed, and truncated unit contributes bounded structured state.