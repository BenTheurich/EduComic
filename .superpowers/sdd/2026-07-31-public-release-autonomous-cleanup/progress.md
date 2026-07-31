# SDD ledger - plan: docs/superpowers/plans/2026-07-31-public-release-autonomous-cleanup.md

Workspace: C:\tmp\EduComic-worktrees\public-release-cleanup
Branch: codex/public-release-cleanup
Baseline: ae15bc659421ec16adc9df4c10fddde273867af4

Preflight ruling: keep Pillow in Task 2 because Task 13 uses the existing dependency to validate and re-encode image uploads. Removing it and adding it back would contradict the deletion-first goal.

Preflight ruling: when Task 9 makes `VITE_API_URL` mandatory for production builds, update the secret-free CI workflow from Task 5 with a non-secret invalid test URL.

Baseline: frontend production build passes with a 623.86 kB main bundle and large-chunk warning.

Baseline: ESLint fails with 23 errors and 9 warnings.

Baseline: `npx tsc --noEmit` exits successfully under the current permissive root configuration; Task 4 will add an explicit application typecheck.

Baseline: backend Pytest collection fails because the repository has no configured tests directory and collects the broken live script at `src/services/test_story_idea.py`.

Task 1: partial commit c87bab5 (`.gitignore` and Phase 0 status).

Task 1: parked - required artifact removals remain tracked because the approval reviewer rejected exact deletion twice and a recoverable quarantine move once. Ruling: real spec gap, not load-bearing for Tasks 2 through 21; do not retry destructive operations without a new user-approved path.

Task 1: reviewer confirmed the partial diff is clean but spec compliance fails while the artifacts and unsafe historical advice remain.

Task 1: fix round 1/5 (3 addressed, 0 open - remove remaining binaries, stale README links, and secret-bearing ignored review package; commits ef28ff6..9240824).

Task 1: complete (commits c87bab5, ef28ff6, 9240824; review clean). Tracked candidate and staged source export pass redacted Gitleaks.

Task 2: complete (commits c87bab5..6d088c1, review clean).

Task 3: fix round 1/5 (1 addressed, 0 open - align avatar BFL key with readiness; commits 65e941e..86fd084).

Task 3: complete (commits fea50fd..86fd084, review clean).

Task 4: complete (commits b8e5e7b..9c0189d, review clean).

Task 6: fix round 1/5 (1 addressed, 0 open - remove unrelated UploadedMaterial typing; commits d624aec..a7a8352).

Task 6: complete (commits 9c0189d..a7a8352, review clean).

Task 6 browser check: headed desktop/mobile landing, direct invite, and teacher mobile navigation passed against an offline stub API; console had no application errors.

Task 6: browser fix round 2/5 (1 addressed, 0 open - responsive teacher/student layout roots; commit ef5aa81, review clean).

Tasks 7-10 headed browser checkpoint: desktop workflow, truthful status/reader guards, PDF success/failure, and mobile rerun passed against offline stubs. Two PDFs downloaded (4,379 B and 4,123 B). Minor teacher horizontal overflow is assigned to Task 18.

Task 7: fix round 1/5 (1 addressed, 0 open - propagate classroom-style lookup failures before provider/storage calls; commits c05e519..eac0bfd).

Task 7: complete (commits f02261e..eac0bfd, review clean).

Task 8: fix round 1/5 (3 addressed, 0 open - student dashboard ready-only story, teacher direct reader guard, ready-only reader navigation; commits c3b126d..4dc93dd).

Task 8: complete (commits eac0bfd..4dc93dd, review clean).

Task 9: fix round 1/5 (1 addressed, 0 open - load Vite mode env files and validate every build mode; commits 56462b2..8fb0d4f).

Task 9: complete (commits 4dc93dd..8fb0d4f, review clean).

Task 10: fix round 1/5 (2 addressed, 0 Important open - require real image decode/properties and preserve 3:2 aspect ratio; commits c6fc9e8..626ad1b).

Task 10: complete (commits 9240824..626ad1b, approved with one Minor native-decode test caveat assigned to headed browser verification).

Task 11: fix round 1/5 (3 addressed, 1 logging dependency open - URL bounds, multipart nonblank/max, service logging; commits da122f5..8a9b294).

Task 11: fix round 2/5 (1 addressed, 0 open - sanitize reachable panel-review output and normalize EOL; commit 59a9776).

Task 11: complete (commits 626ad1b..59a9776, review clean).

Task 12: fix round 1/5 (2 Important and 1 Minor addressed, 0 open - reject removed request extras, canonicalize GitHub BFL key, remove UI logs; commit b9642c2).

Task 12: complete (commits 59a9776..b9642c2, review clean).

Sequencing ruling: execute Tasks 16 and 16A before Tasks 13-15 so upload/provider hardening does not add code to stale routes or the unused materials feature.

Task 16: fix round 1/5 (1 addressed, 0 open - assert stale paths absent under every HTTP method; commit 6f20437).

Task 16: complete (commits b9642c2..6f20437, review clean).

Task 16A: fix round 1/5 (1 addressed - add a positive sidebar render assertion; commits 350392c..91ab256).

Task 16A: feature-removal review is clean. Its repository-wide lint gate remains open only because the remaining errors are in modules/config assigned to deletion-first Task 17; Task 16A will receive final clean review after Task 17.

Sequencing ruling: execute Task 17 before Task 13 so the already-reviewed materials deletion can satisfy its full lint gate without polishing frontend modules scheduled for deletion.

Task 16A: complete (commits 350392c..91ab256; re-review at bdf4980 clean after Task 17 closed the full lint gate).

Task 17: complete (commits 4a53b1f..bdf4980; review clean). Deleted 38 unreachable source modules and 28 unused direct dependencies; all 16 routes remain, lint/typecheck/29 tests/build pass, and the main entry fell from 623.86 kB to 403.87 kB.

Task 17 advisory: production audit reports 3 high React Router advisories with no v6 fix and 0 critical. Major-version migration is deferred to the founder checklist unless a safe in-scope fix appears.

Task 20 follow-up: remove stale `frontend/RESTRUCTURE_SUMMARY.md` references to deleted `NavLink` and classroom type files.

Task 5: complete (commit e6ab427; review clean). The sole workflow is read-only, secret-free CI and every mirrored backend/frontend gate passes locally.

Task 13 preflight ruling: delete the unauthenticated optional student-photo upload instead of adding validation/storage compensation to it. Avatar generation already works text-only; with no access model, signed bearer URLs would not make child photos meaningfully private. Remove the orphan-prone two-request upload flow, photo fields/fallbacks, and now-unused Pillow/python-multipart dependencies. Reintroduction is a founder gate after authentication, consent, retention, private object storage, authorized signed access, and abandoned-upload cleanup exist.

Task 13: complete (commit 9185bfc; review clean). Backend 32 tests and frontend 30 tests pass; the upload route/field/UI/fallbacks and direct Pillow/python-multipart dependencies are absent.

Task 14 preflight: OpenAI SDK 2.8.1 supports Pydantic structured parsing through `chat.completions.parse`. Use strict idea/script/review contracts, context-aware known-speaker validation, explicit token ceilings, no narrative avatar URLs, and no permissive padding/default normalization.

Task 15 preflight: preserve panels by generating and durably uploading the complete replacement before one atomic `replace_chapter_generation` RPC; a failure-reporting wrapper sets `failed`. Task 19 owns the security-invoker RPC and bucket migration. The founder still owns applying the migration, service-key configuration, access-model choice for generated images, and a durable worker.

Task 18A: complete (commits 6eed33f..bf4ba58; re-review clean). Frontend 37 tests, typecheck, lint, production build, and diff check pass; the duplicate responsive-sidebar control ID was removed.

Task 18B: complete. Production `frontend/src` contains zero `console.log`, `console.debug`, `console.warn`, or `console.error` calls. Student classroom, student sidebar classroom-list, and story-generator metadata failures now stay visible and provide retry actions. Focused 9 tests and full frontend 40 tests, typecheck, lint, production build, diff check, and staged Gitleaks pass.
