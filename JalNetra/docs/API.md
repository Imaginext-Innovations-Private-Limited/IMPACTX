# API and data contract

[Repository home](../README.md) · [Architecture](ARCHITECTURE.md) · [Schema](../database/schema.sql)

This is the contract for the local prototype. All routes are scoped to the active dataset. Configure the dataset mode on the server and include it in API results and the UI. Use ISO 8601 timestamps with offsets for inputs and UTC timestamps for stored and returned values.

| Method and path | Inputs | Success |
|---|---|---|
| `GET /api/status` | None | `200` with the active mode and available offline samples. |
| `GET /api/zones` | None | `200` with zone IDs, names, optional coordinates, and marker positions. |
| `POST /api/reports` | Multipart fields listed below | `201` for a newly saved report. `200` for a repeat request that returns its existing report. |
| `GET /api/reports` | Optional `zoneId` filter | `200` with recent reports and status. Use a bounded result set. |
| `GET /api/reports/:id` | Report ID | `200` with fields, model result, and photo URL. |
| `GET /api/reports/:id/photo` | Report ID | `200` with the normalized image and correct content type. |
| `POST /api/reports/:id/retry` | Report ID | `200` with the updated result or `202` with an already-running attempt. |
| `GET /api/hotspots` | None | `200` with zones and their current per-category evidence. |
| `POST /api/complaints` | JSON `zoneId`, `category` | `201` with a new draft or `200` with the saved draft for identical evidence. |
| `GET /api/complaints/:id` | Draft ID | `200` with the saved draft and evidence references. |
| `PATCH /api/complaints/:id` | JSON `recipient`, `draftText` | `200` with saved edits and unchanged evidence references. |
| `GET /api/complaints/:id/export` | Draft ID | `200` with a downloadable text draft. |
| `POST /api/demo/reset` | JSON object in rehearsal mode | `200` after resetting the in-memory rehearsal and seeding one Watch report. |

Use `400` for invalid fields, `404` for records absent from the active dataset, `409` for a draft whose evidence no longer qualifies or reuse of a request ID with different content, `413` for oversized files, and `415` for unsupported files. A vision failure after a successful save returns the saved report with `needs_review` and a reason. Use a predictable error shape such as `{"error":{"code":"INVALID_ZONE","message":"Choose a listed shoreline zone."}}`.

## Report submission fields

| Field | Rule |
|---|---|
| `photo` | Raw RGB from a JPEG or PNG decoded in the browser. The browser accepts originals up to 5 MB. |
| `photoWidth`, `photoHeight` | Integer dimensions from 1 to 1,200. The server checks three RGB bytes per pixel and encodes a metadata-free PNG. |
| `zoneId` | Existing zone ID. |
| `observedAt` | Required timestamp with an offset. Reject future times. |
| `requestId` | Stable, unique client-generated ID for the submission and its retries. |
| `note` | Optional text, up to 500 characters. |
| `ph` and `temperatureC` | Optional finite numbers. Save empty values as null and display supplied values as citizen-reported. |

## Vision adapter response

```json
{
  "imageQuality": "usable",
  "detections": [
    {
      "category": "foam",
      "cue": "White froth gathers along the shoreline."
    }
  ]
}
```

Use `usable` or `unclear` for quality. The categories are `foam`, `algae_like_growth`, and `dumping`. Require at most one entry per category with a nonempty visual cue. An empty list with usable quality produces `no_target_signs`. Store adapter provenance as `live_model`, `captured_replay`, or `simulated`. Invalid output or an unavailable adapter produces `needs_review`.

## Example hotspot payload

```json
{
  "dataMode": "demo",
  "zones": [
    {
      "zoneId": "north-inlet",
      "status": "priority_hotspot",
      "categories": [
        {
          "category": "foam",
          "status": "priority_hotspot",
          "evidenceCount": 2,
          "evidenceReportIds": ["JN-001", "JN-002"]
        }
      ]
    }
  ]
}
```

Render zone statuses as `none`, `watch`, or `priority_hotspot`. Report analysis has its own states `pending`, `classified`, `no_target_signs`, and `needs_review`. Labels such as “Duplicate evidence” and “Outside active window” are calculated when displaying a group or report.

## Persistence notes

Apply the [SQLite starter schema](../database/schema.sql) when building the backend. Enable foreign keys on every connection. Insert the generated draft and its evidence rows in one transaction. The exported text may be edited in the browser and downloaded as plain text. Date, time, location and evidence links should appear in the initial generated text.
