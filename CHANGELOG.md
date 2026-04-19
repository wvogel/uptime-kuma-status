# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-19

### Added
- Incident end time (`resolved_at`) with automatic deactivation and 30-minute "Resolved" grace period on the public page
- Incident updates timeline with timestamp, bilingual text and optional severity change per update
- Redundant outage filter: duplicate and prefixed monitor names (e.g. `VPN Köln` when `Köln` is down) are collapsed into one entry with a `+` indicator; hidden monitors are listed in an instant CSS tooltip
- Monitor search box in the admin for instant client-side filtering
- Unsaved-settings warning — pulsing save button and "Unsaved changes" hint when a setting was changed but not yet saved
- Optional SSO user display on the public status page: when reached through an oauth2-proxy, the logged-in user and a logout button appear in the header
- Fullscreen mode scaling — real F11 / Fullscreen API triggers a scaled layout with 3 tiers (1080p / 2K / 4K) for wall displays and distance readability
- Live OS theme change detection — both pages update instantly when the system switches between light and dark mode
- `TZ=Europe/Berlin` in container definitions for correct local time handling
- Full open-source project meta: `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, GitHub issue/PR templates, Dependabot config, Docker build GitHub Actions workflow, README badges

### Changed
- Groups in the outage list are now hidden; only the individual affected monitors are shown with the group path available on hover
- Groups whose children are partially down are now reported as `degraded` (yellow) instead of `down` (red); red is reserved for fully-failed groups
- Public status page favicon redesigned using the original Uptime Kuma blob shape with status dots overlay
- Admin favicon gets an additional gear overlay
- Favicons adapt to dark mode (dots and gear flip to dark background colour)
- Issue-list dots are now inline SVGs for pixel-perfect alignment across all sizes
- SQLite access hardened with WAL mode and a 10s busy timeout for safer concurrent reads
- Bumped to FastAPI 0.136, SQLAlchemy 2.0.49, aiofiles 25.1.0, redis 7.4.0, Python 3.14-slim base image

### Fixed
- `resolved_at` comparison uses local time in both the SQL query and the Python layer so incidents resolve at the moment the admin entered
- `_read_sqlite()` now returns the `incident_updates` map (previously crashed in the public worker)
- `TemplateResponse` updated to the new Starlette signature `(request, name, context)` to stay compatible with FastAPI 0.136+

## [0.1.0] - 2026-04-06

Initial release.

- Multi-instance Uptime Kuma aggregation via [uptime-kuma-api](https://github.com/wvogel/uptime-kuma-api) sidecar
- Compact status page with masonry grid and monitor hierarchy
- Admin GUI behind oauth2-proxy for instances, monitors, incidents, footer, settings
- German / English bilingual support
- Light / dark / auto theme
- Real-time updates via WebSocket with HTTP polling fallback
- SQLite for configuration, Valkey for live monitor cache
