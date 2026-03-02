# Final Build Summary

## Frontend
- Added 3D exam icons (thiings) in exam cards.
- Added onboarding and result status hero icons.
- Fixed exam cards layout:
  - stable title/description block height,
  - aligned stats row,
  - aligned primary action button plane.
- Moved `3D icons by thiings.co` attribution to centered footer.
- Added icon mapping for new subject `Инфобез`.
- Improved exam submit UX:
  - no fake `0%` when API submit fails,
  - explicit submit error message and retry path.

## Backend / API
- Stabilized startup flow in containerized deployment.
- Fixed CSRF/session-auth conflict causing `403` on `POST /api/exams/<id>/submit/` from SPA.
- Hardened runtime defaults:
  - production-safe `DEBUG` behavior,
  - strict `SECRET_KEY` guard in production mode,
  - host/origin security configuration via env.
- Improved static handling in container startup:
  - safer collectstatic behavior under missing map assets.

## Deployment
- Removed BOM-related breakages in startup scripts/configs.
- Added backend healthcheck in docker compose.
- Frontend now waits for healthy backend (`depends_on: service_healthy`).
- Reduced startup race conditions that caused intermittent `502`.
- Made `.env.docker` optional in compose to avoid hard boot failures.

## Data Seeding
- Replaced domain-specific seed content with neutral employee certification topics.
- Seeding behavior improved:
  - no auto-reseed over existing DB on each restart,
  - optional force reseed via env switch.

## Repository Hygiene
- Removed tracked Python cache artifacts (`__pycache__`, `*.pyc`) from VCS.
- Removed accidental duplicate root `exams/` package (backend source of truth is `backend/exams/`).

