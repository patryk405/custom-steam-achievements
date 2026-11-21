# Custom Steam Achievements

Private community pack library for Custom Steam Achievements. The current release supports BOTW on Savage Wind 0.6.0-alpha.6 / BOTW 1.9.0.

## Included
- Searchable catalog, achievement details and JSON downloads.
- Authenticated JSON uploads with persistent D1 storage.
- Strict schema and known-signal validation, bounded streaming body (128 KiB), 200 achievements and 20 packs per creator.
- 38-objective starter collection derived from the existing local tracker, with original Reddit attribution and detection caveats.
- Creator template and guide.

## Limits
- Private preview; change hosting audience only deliberately before a community launch.
- No automatic plugin import yet. Pack envelopes need an importer that maps achievements and rules into the local catalog/adapter.
- Upload identity uses trusted Sites edge headers. A different hosting provider MUST implement real authentication and strip untrusted identity headers; do not expose the local preview directly to the Internet.
- Before public launch: add moderation/reporting, owner pack removal, version management and stronger abuse controls. Upload limits are early-access safeguards, not a complete moderation system.
- Rules are structure-checked, not gameplay-certified. Icon names are metadata; site previews reuse the original plugin SVG icons, with a star fallback for unknown icon names.
- GitHub Education is independent of this Sites deployment. No permanent free backend entitlement is assumed.

## Verification
Run `npx tsc --noEmit`, build, apply the local migration per README, then `python tests/api-smoke.py` against localhost:4173. The API test uses synthetic identity headers only on the local preview and stores a disposable local test pack. It never targets production.

## Game catalog and artwork
The Games selector includes BOTW, Ocarina of Time Remake, Bloodborne, Pokémon Legends: Arceus, Super Mario Odyssey and Pokémon Pokopia. Only BOTW has a tracker adapter and accepts uploads. Other game entries have empty libraries; no unsupported progress tracking is implied. Game selection uses the `game` URL query parameter and supports browser back/forward.

Cover artwork is bundled through Vite URL imports. `lib/covers/sources.json` records the original source pages and image URLs. Rights remain with the original owners. Ocarina uses ABH20’s SteamGridDB composition of original game artwork, not an official remake cover.

Cover presentation uses a consistent 2:3 crop with object-fit: cover. Flat poster art replaces physical packaging photos. The interface loads Motiva Sans through Steam’s published stylesheet; no font binaries are stored in this repository.

## Home and download
The root route is the Home page; `/library` holds the pack browser. Legacy `/?game=...` URLs redirect to the corresponding library view. The supplied logo is used in the shared header, top-right home link and favicon metadata.

`lib/downloads/custom-steam-achievements-0.1.0-source.zip` is a curated developer source archive, not an installer. It excludes personal runtime state and replaces local shortcut IDs with configurable zero placeholders. A newly generated neutral chime replaces the extracted Steam sample. The archive README explains manual setup and unverified clean-install compatibility. `release.json` records the exact byte size and SHA-256, checked against the HTTP download. The running local plugin has not been changed.

## Preview 0.2.0
Home and the source ZIP now include the 66-objective Longshot adapter and the experimental BBPort trophy importer. The Ocarina collection has a downloadable built-in JSON pack and full preview; community uploads remain BOTW-only and this restriction is explicit. Bloodborne has no fabricated trophy pack: names and IDs must come from a user's local BBPort XML. Its game page explains configuration and pending real-game testing. No game files, keys or player state are distributed.

`python scripts/package-preview.py` regenerates the sanitized 0.2.0 ZIP from the sibling plugin checkout, includes all adapter resources and the BBPort setup script, replaces local shortcut IDs with zero, and uses an original chime. It does not change the installed plugin.
