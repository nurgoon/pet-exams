# Changelog

## 2026-03-17
### Added
- Staff “Cabinet” main page with quests, rewards, and daily progress.
- Quest submissions with photo proof and manual approval flow.
- Duty schedule (cleaning) view on staff page.
- PWA assets (manifest, service worker, app icons).
- Admin quick actions for approving/rejecting submissions.
- Thumbnails for proof images in admin list.
- Push notifications backend + admin tools (VAPID).

### Changed
- Admin theme forced to light for review convenience.
- Frontend API layer expanded for quests/duties/leaderboard.
- Reward badges styling and completion button highlight.
- Leaderboard trimmed to top 5 on staff page.

### Notes
- Local env requires `backend/.env` for VAPID keys when testing push.
- Django debug set via `DJANGO_DEBUG=1` for local runs.
