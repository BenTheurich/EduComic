# Task 10 report

Implemented fail-closed PDF export shared by both teacher callers.

- `exportStoryPdf` fetches every panel with a native 10-second timeout, requires complete PNG/JPEG framing, browser decoding, and matching positive jsPDF dimensions, then passes verified `Uint8Array` data to jsPDF.
- Image embedding starts only after all panel fetches and decodes validate; any request, validation, embed, or save failure rejects the export.
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

## Review fix round 1

Replaced header-only checks with complete container framing, native browser decoding, and jsPDF's installed property parser; preserved each source image's aspect ratio when fitting it into 2-up or 4-up cells.

- RED: the prior exporter saved both a 3-byte `FF D8 FF` JPEG and a JPEG truncated after its valid dimensions; both 2-up/4-up layout assertions received square dimensions.
- GREEN: complete valid 3×2 PNG and JPEG fixtures pass through real jsPDF properties; both truncated JPEGs reject before `addImage`/`save`; 2-up and 4-up coordinates retain 3:2 dimensions and center the image.
- Final verification: focused 9/9 and full 19/19 tests, typecheck, touched-file ESLint, and the production build passed; audit remains at 0 critical production advisories.
