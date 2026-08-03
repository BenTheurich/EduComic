# Avatar Portrait Thumbnails

## Goal

Keep each generated full-body avatar as the canonical character reference while giving compact profile UI a consistently framed face-and-shoulders portrait. The portrait must be derived locally, require no additional provider call, and preserve the identity and styling of the canonical avatar.

The student-profile chooser should also use EduComic's cool paper background instead of the current page-wide yellow glow.

## Scope

- Add one nullable stored thumbnail reference to each student.
- Derive a 256 by 256 portrait from every newly generated full-body avatar.
- Use the portrait in compact circular avatar treatments:
  - student profile chooser;
  - student dashboard header;
  - classroom class-picture banner;
  - teacher classroom roster cards and list rows.
- Keep the full-body avatar in the main student profile and as the reference sent into comic generation.
- Backfill the current local Ben Theurich and James Smith profiles from their existing full-body avatars without contacting Black Forest Labs.
- Remove the global yellow radial wash and let the existing `background` design token provide the application canvas.

No new provider request, face-recognition dependency, authentication behavior, or public-demo behavior is included.

## Data Contract

Add `avatar_thumbnail_object_path` as a nullable column on `students` through the next Alembic migration. API student payloads expose it as `avatar_thumbnail_url` alongside the existing `avatar_url`.

- `avatar_url` remains the canonical full-body image.
- `avatar_thumbnail_url` is presentation media for compact profile contexts.
- Compact UI falls back to `avatar_url`, then initials, when a thumbnail is unavailable.

The existing `superseded_avatar_paths` manifest retains both superseded full-body and thumbnail paths until their files have been removed successfully. Student erasure and full local reset include both current paths.

## Portrait Derivation

Use Pillow, which is already installed by the backend, after the provider image has been downloaded and decoded.

1. Convert the avatar to RGB and build a foreground mask where any channel is below 245. This locates the illustrated character against the prompt's plain white background.
2. If a foreground bounding box exists, create a square crop centered on that box horizontally, beginning at its top edge, with a side length equal to 55 percent of the foreground height and clamped to the source dimensions.
3. If no useful foreground box exists, use a top-centered square crop based on the shortest source dimension.
4. Resize to 256 by 256 with Lanczos resampling and encode a metadata-free PNG.

This is intentionally deterministic rather than face detection. The existing generation prompt guarantees a single, centered, front-facing full-body child on a plain background, making a top-centered crop the smallest reliable solution.

## Publish And Cleanup Flow

Avatar generation downloads the provider result once, stages the canonical image and derived portrait, and finalizes both into the student's `avatars` directory. The database replacement publishes both paths in one transaction.

- If download or decoding fails, neither new file is published.
- If portrait derivation fails unexpectedly, the valid full-body avatar may still be published with a null thumbnail; compact UI uses its fallback.
- If the database update fails, any newly finalized files are deleted as compensation.
- After a successful replacement, the old full-body image and old thumbnail are deleted independently. Any failed cleanup remains in `superseded_avatar_paths` for the existing durable cleanup path.

## Frontend Treatment

Student payload types gain `avatar_thumbnail_url`. Compact avatar components select:

```text
avatar_thumbnail_url -> avatar_url -> initials
```

The main profile page intentionally continues to show `avatar_url` so the student can review the complete character used in comics.

`BackgroundComponent` becomes a single `bg-background` canvas. The yellow `story-spark` token remains available for small narrative highlights but is no longer used as a page-wide gradient, matching the existing One Spark Rule in `DESIGN.md`.

## Verification

Backend checks cover:

- portrait output is a valid 256 by 256 PNG;
- portrait framing uses the upper foreground rather than the center of a full-body image;
- student serialization returns both URLs;
- replacement and erasure include both current and superseded files;
- thumbnail failure does not destroy a successfully downloaded canonical avatar.

Frontend checks cover:

- compact components prefer `avatar_thumbnail_url` and preserve fallback behavior;
- the profile page still uses the full-body avatar;
- the global background no longer renders the yellow radial overlay.

Finish with a desktop and mobile browser pass of the student chooser, student dashboard, classroom roster, class-picture banner, and student profile. Confirm existing Ben and James portraits are correctly framed and no provider credits were used.
