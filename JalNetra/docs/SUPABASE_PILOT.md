# Shared reporting

Open **Citizen lake map and reporting**, **Report to lake operator**, or **Operator sign in** on the homepage. Citizens sign in, join a mapped lake, choose a shoreline sector, and submit a photo or concern. A citizen can read their own submissions on another device after signing in. Operators see submissions for their assigned lakes and can open private photos, request live analysis, or record a review decision. An administrator can promote an enrolled citizen to operator or return that account to citizen in their assigned lake.

Supabase stores the shared records and applies role and lake restrictions. The public rehearsal remains isolated. The starter administrator must be assigned by a trusted Supabase administrator after their account is verified. Set the production Auth Site URL to the JalNetra deployment, allow the /pilot.html redirect URL, and configure custom SMTP before inviting the general public. Hosted Supabase default mail only reaches authorized team addresses. Keep email confirmation enabled. The **Forgot password?** button uses the same mail configuration and verified /pilot.html redirect.

## Vision and review

Vercel uses AI Gateway through its deployment identity, or the configured server-side OPENAI_API_KEY or AI_GATEWAY_API_KEY. JALNETRA_VISION_MODEL can override the default. Model results show visible signs and are saved separately from review decisions. Failed requests leave the report available for retry and manual review. A citizen upload automatically requests a preliminary assessment. The result is saved on the photo report for both the citizen and the operator. Operators can still request analysis for reports without a saved result. Model output can contribute to triage after a human confirms or corrects it.

A 64-bit difference hash flags visually similar recent photos for comparison. It can miss crops or match scenes with similar structure. A reviewer can mark a report as a duplicate and choose the original. The shared API groups recent confirmed or corrected evidence by sector and category, counting each reporting citizen once. One reporting citizen starts Watch. Two distinct reporting citizens start Priority. The operator review queue lists 25 reports per page and has a **Needs review** filter.

To evaluate classification on real imagery, prepare a permission-cleared, independently labeled PNG dataset with visible positives, ordinary negatives, and unclear images. Each manifest row provides file (relative to the manifest), quality (usable or unclear), and labels (an array of foam, algae_like_growth, and dumping). Run:

    node scripts/evaluate-vision.mjs path/to/manifest.json

The script sends those images to the configured provider and prints category precision and recall, review rate, and errors. Use only photographs authorized for processing by that provider.

## Citizen lake conditions

The signed-in citizen map displays the highest recent signal for each lake and shows individual sectors, categories and times when selected. It summarizes observations from the past seven days. The map uses verified concern, awaiting review, no visible issue in a reviewed photo and no recent information. No photos, notes or account identifiers appear in the map summary. A reviewed photo does not measure water quality.

A citizen can raise a concern from a photo assessment. The concern remains linked to that photo for operator review. The runtime uses a server-only `PILOT_ANALYSIS_WRITE_TOKEN` whose SHA-256 digest is stored in the private database configuration.

## Civic complaint draft

The public rehearsal exposes a complaint draft from a Priority hotspot. The shared operator workspace includes a **Demo concern** card when opened from the homepage's demo concern link. The confirmation and export in that card demonstrate the complaint workflow with illustrative evidence. The shared complaint API requires an assigned operator and recalculates eligibility before generating a draft.

For Devanahalli Lake, the draft suggests the [Devanahalli Town Municipal Council](https://bangalorerural.nic.in/en/public-utility/devanahalli-tmc/) as a local contact. Confirm responsibility for the specific site and issue before filing. [Karnataka Janaspandana](https://ipgrs.karnataka.gov.in/) is available as a public grievance route. The operator files the draft separately.

## Community action

Open `/community.html` to find cleanups and register as a volunteer. Community groups and organizations can create a confirmed email account and propose a drive with a lake, start time, meeting point and safety instructions. An assigned lake operator approves the proposal on the same page. The citizen homepage shows scheduled drives for the current Bengaluru date.

Before releasing the separate page, apply the community drive page migration. Organizer registration uses the existing `/pilot.html` email confirmation callback, which links back to community sign in. Run `supabase/tests/community_drive_page.sql` to check publishing permissions and Bengaluru date boundaries.

- **Cleanups.** Assigned operators publish authorised events with meeting and safety instructions. Citizens register before the event and show their check-in code from Community Drives. Operators match the code on the roster, record attendance after the start time, and then complete the event. Organizers see completed and cancelled drives in their submission history.
- **Lake adoption.** Citizens submit a group and stewardship plan. Assigned operators approve, decline or end an adoption. Approved plans appear on the lake's community board.
- **Restoration.** An operator starts with a human-verified pollution photo, assigns a responsible team and records work completed. A citizen chooses **Upload a follow-up photo** in the tracker and uploads a new photo from the same sector. The operator opens the private evidence and accepts or rejects it. Follow-up photos stay out of the public concern feed. Once restoration is verified, the original report no longer contributes to the active advisory.
- **Impact.** The board counts completed cleanups, unique volunteers with recorded attendance at completed cleanups, active adoptions and restorations with accepted evidence.
- **Lake alerts.** Citizens subscribe through Community action. New standalone concerns and operator confirmations or corrections generate alerts automatically. The in-app inbox refreshes every 30 seconds while the citizen page is open and keeps unread alerts for the next visit in the same session. Lake subscriptions and read state are stored with the account.

Apply the community restoration migration to the target Supabase database before releasing the community board. Run `supabase/tests/community_restoration.sql` with a database administrator connection to verify the workflow and access rules. The test rolls back its fixtures.

## Deployment checks

The pilot migrations include the 21 mapped lakes and four reporting sectors per lake. The pilot readiness route reports the database schema version and whether vision credentials are available. Run npm test and supabase/tests/pilot_access.sql to check API handling and live database role policies. The SQL test rolls back its fixtures.
