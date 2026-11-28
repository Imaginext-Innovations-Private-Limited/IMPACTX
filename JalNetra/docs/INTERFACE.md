# Interface guide

[Repository home](../README.md) · [Workflow](WORKFLOW.md) · [Build and demo](BUILD_AND_DEMO.md)

This guide describes the report and evidence screens used in the rehearsal. The [evaluator walkthrough](BUILD_AND_DEMO.md) covers the current shared pilot and Community Drives pages.

Use two primary views, **Report observation** and **Lake dashboard**. Open the evidence and draft panels from the dashboard. Give the project a lake-blue and teal palette, use warm amber for Watch and a clearly labelled priority status. Use text labels and icons so colour is optional for interpreting the map.

| Screen | What appears | Primary action |
|---|---|---|
| Report observation | Zone selector, observation time, upload button and preview. Optional readings and notes sit in a collapsed section. | Analyse photo |
| Report result | Photo, visual cue or review reason, zone, time, optional readings, source label. | View on map or retry |
| Lake dashboard | Bundled shoreline map, legend, three zone markers and a keyboard-accessible zone list. Show mode near the title. | Open a zone |
| Evidence panel | Category, status, number of unique photos in the active window, and chronological report cards. | Generate draft when eligible |
| Complaint editor | Recipient and body fields, linked report IDs, visible evidence summary, and export control. | Download draft |

## Status copy

| State | Example copy |
|---|---|
| Running | “Photo saved. Analysing visible signs…” |
| Usable, no labels | “No target signs detected in this photo.” |
| Unclear | “Needs review. Try a clearer view of the shoreline.” |
| Timed out | “Photo saved. Analysis took too long. Retry when you’re ready.” |
| Watch | “1 matching photo in the last 48 hours.” |
| Priority | “2 distinct photos show foam in North Inlet.” |
| Duplicate | “This photo already counts toward this category.” |
| Evidence expired | “The observation is in history and outside the current 48-hour window.” |

Use descriptive labels for upload and form inputs. Show actionable validation next to the field, preserve selected values during errors, and announce upload results with an accessible status region. On narrow screens, put the zone list immediately below the map and stack evidence cards vertically. Mark all replay fixtures and fictional reports clearly in the interface.
