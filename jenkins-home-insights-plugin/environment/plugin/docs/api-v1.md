# API v1

The standalone endpoint is `GET /operational-insights/api/v1/query`; health is `GET /operational-insights/api/v1/health`. Jenkins RootAction uses the same URL namespace. Responses are UTF-8 JSON.

Query parameters:

- `view`: `records`, `queue`, `builds`, `lineage`, `plugins`, or `summary`.
- `kind`: repeatable source-family filter for record views.
- `contains`: case-insensitive canonical record search.
- `sort`: `key`, `kind`, `sequence`, or `display`.
- `direction`: `asc` or `desc`.
- `limit`: positive integer no greater than 1000.
- `cursor`: opaque cursor returned by the preceding request.
- `principal`, `system-read`, `overall-read`, and repeatable `item` model the standalone authorization context.

A successful query contains `generationId`, `view`, `items`, `total`, `nextCursor`, `facets`, and `metadata`. Empty cursors serialize as JSON null. Invalid filters or cursors are request errors. Unauthorized requests are forbidden and contain no result metadata.

CLI `query` flags have the same names and semantics as HTTP parameters. Ordering, default bounds, null handling, and errors are transport-independent.
