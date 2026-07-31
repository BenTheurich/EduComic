# Task 10 report

Implemented fail-closed PDF export shared by both teacher callers.

- `exportStoryPdf` fetches every panel with a native 10-second timeout, accepts only signature-matching PNG/JPEG responses, and passes verified `Uint8Array` data to jsPDF.
- PDF construction starts only after all panel fetches validate; any request, validation, embed, or save failure rejects the export.
- `ClassroomDetail` and `StoryViewer` now call the shared exporter and show success only after it saves; rejected exports reach their existing error toast.
- Updated jsPDF from 3.0.4 to 4.2.1. The prior critical advisory affected `<=4.2.0`; `npm audit --omit=dev` now reports 0 critical production vulnerabilities (remaining repository advisories: 12 moderate, 11 high).

Verification:

- RED: focused test failed with `Not implemented` after defining successful-byte and failed/invalid-panel behavior.
- GREEN: `npm.cmd test -- --run exportStoryPdf` passes 4 tests.
- `npm.cmd test -- --run`: 7 files, 14 tests passed.
- `npm.cmd run typecheck`: passed.
- Touched-file ESLint: passed.
- `VITE_API_URL=https://api.example.invalid npm.cmd run build`: passed (existing stale Browserslist data and large-chunk warnings remain).
- `npm.cmd audit --omit=dev`: 0 critical; exits nonzero for the pre-existing high/moderate advisories outside Task 10.
