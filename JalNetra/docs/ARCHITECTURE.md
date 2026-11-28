# System architecture

[Repository home](../README.md) · [Workflow](WORKFLOW.md) · [API contract](API.md) · [SQLite schema](../database/schema.sql)

## Shared deployment

The citizen pages, Community Drives and the operator workspace share the Vercel API entry point. Shared pilot requests use Supabase Auth, Postgres and private photo storage. The database checks lake membership and role before allowing operator actions. Public schedule and conditions responses expose only the fields intended for citizens. The community dashboard counts completed cleanups and verified restorations from shared records.

The Vercel rehearsal uses isolated browser sessions backed by private Blob storage. The local offline rehearsal uses in-memory SQLite. See [shared pilot setup and permissions](SUPABASE_PILOT.md).

## Local and rehearsal component diagram

```mermaid
flowchart TD
    UI["Browser: report, map and draft views"] --> API["Node.js HTTP application"]
    API --> REPORT["Report intake and analysis orchestration"]
    API --> HOTSPOT["Hotspot aggregation"]
    API --> DRAFT["Complaint draft service"]
    REPORT --> STORE[("SQLite")]
    HOTSPOT --> STORE
    DRAFT --> HOTSPOT
    DRAFT --> STORE
    REPORT --> PHOTOS[("PNG evidence in SQLite")]
    REPORT --> ADAPTER["Vision adapter"]
    ADAPTER --> LIVE["Live vision model"]
    ADAPTER --> REPLAY["Offline response fixtures"]
```

| Component | Responsibility |
|---|---|
| Browser | Render the form, bundled map, status labels, evidence panel, history, and draft editor. |
| HTTP API | Serve the frontend and API from the same origin. Validate requests, identify the active data mode, and return consistent errors. |
| Intake | Validate format, byte limit and image dimensions. Strip metadata, save only the normalized image, and fingerprint it for evidence deduplication. |
| Vision adapter | Give live and replay modes one result contract. Validate labels and cues against the allowlist and time out the live request at about 12 seconds. |
| Hotspot service | Compute eligible evidence and group status from the persisted facts. The dashboard and complaint service share the same calculation. |
| Draft service | Recheck eligibility and save the draft with evidence report IDs in one transaction. |
| Persistence | SQLite stores zones, report and analysis history, and complaint drafts. Normalized PNG bytes are stored in SQLite and served by report ID. |

## Upload and analysis sequence

```mermaid
sequenceDiagram
    actor Citizen
    participant API as HTTP API
    participant Store as SQLite
    participant Vision as Vision adapter
    Citizen->>API: Submit photo, zone and request ID
    API->>API: Validate and normalize image
    API->>Store: Save pending report and start attempt
    API->>Vision: Analyse normalized photo
    alt Valid and usable result
        Vision-->>API: Categories and visual cues
        API->>Store: Save classified or no-target outcome
    else Unclear result or model failure
        Vision-->>API: Unclear or error
        API->>Store: Save review reason
    end
    API-->>Citizen: Return saved report and result
```

**Working on retries.** Uniquely constrain request IDs per data mode. Store report data and PNG bytes in one transaction and return the existing report for a repeat submission. Use a per-report attempt record with an expiry for model calls. Claim a retry atomically for one caller. A late response from an expired attempt must never replace the outcome of a fresher attempt.

## Data relationships

```mermaid
erDiagram
    ZONE ||--o{ REPORT : receives
    REPORT ||--o{ ANALYSIS_ATTEMPT : records
    ANALYSIS_ATTEMPT ||--o{ DETECTION : returns
    ZONE ||--o{ COMPLAINT_DRAFT : groups
    COMPLAINT_DRAFT ||--|{ COMPLAINT_EVIDENCE : links
    REPORT ||--o{ COMPLAINT_EVIDENCE : supports
```

A report points to its current analysis attempt. Earlier attempts remain auditable. A draft records its selected evidence at generation time. Use that snapshot for later export even if a supporting report has aged out of the live dashboard.

## Runtime and data boundaries

| Concern | Prototype decision |
|---|---|
| Presentation | One local process on the presentation laptop. The map and fixtures ship with the build. Rehearsal uses a separate in-memory database. |
| Credentials | The vision key is supplied through an environment variable and stays on the server. |
| Model inputs | Send normalized pixels only. Keep citizen notes, readings and locations local during analysis. |
| Replay | Display the source and use demo-only data. Unknown replay images should return a clear unsupported-fixture outcome. |
| Citizen data | The prototype is a controlled demo. A pilot requires access controls, a retention policy, and verified complaint routing. |

## Suggested module order

Implement intake and storage first. Put vision adapters behind one interface so UI development can use fixtures. Next, make the map and complaint service call the same hotspot calculation. Add the demo reset after the end-to-end path works.
