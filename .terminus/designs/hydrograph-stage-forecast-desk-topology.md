# Defect topology — hydrograph-stage-forecast-desk

```text
STATUS: DESIGN_READY
CONTROL_PLANE_COMMIT: 72c0df6ee13f275bfa7d9573bb90e6d5711123d7
```

Seven root-cause clusters, 30 manifestations, ≥15 on causal edges. Inject **only** these at ENVIRONMENT_BUILD. Do not invent extras.

| Cluster | Idea | Manifestations |
| --- | --- | --- |
| RC_CIVIL_TIME | unused site TZ / DST | D01–D03 |
| RC_RATING | bounds/effective/reverse ignored | D04–D07, D29 |
| RC_QC_HOLD | holds recorded but ineffective | D11–D14 |
| RC_SERIES | uniqueness / supersede / units | D08–D10, D30 |
| RC_JOURNAL | usage touch, event_id, replay order | D18–D22, D28 |
| RC_FORECAST | horizon / as-of / held filter | D15–D17 |
| RC_PUBLISH | warehouse mix + health lies | D23–D27 |

Grace decision (locks Q3): **forecast `--as-of` skew only**; no scheduled observation slots in v1.

Machine-readable detail: `hydrograph-stage-forecast-desk.json`.

```text
DESIGN_READY -> ENVIRONMENT_BUILD
```
