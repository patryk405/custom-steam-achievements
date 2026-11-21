# Custom Steam Achievements

[Website](https://patryk405.github.io/custom-steam-achievements/) · [Pack library](https://achievement-hub-patryk405.green-ray-4163.chatgpt.site/library) · [Steam account](https://achievement-hub-patryk405.green-ray-4163.chatgpt.site/account)

This is a developer preview, not a one-click installer. Linux desktop Steam and Millennium are required. Big Picture, Decky, and Windows are not supported by this preview.

## Setup
1. Install Millennium using https://steambrew.app/ and confirm it works in desktop Steam.
2. Extract this archive. Install Bun and Python 3 if needed.
3. Add your game to Steam as a non-Steam shortcut. Set its numeric shortcut ID in `resources/shortcut-ids.json`: all IDs are intentionally 0 in this source distribution. They must match your own installation for notifications.
4. Check `resources/botw-adapter.json` and `docs/ADAPTERS.md` for the supported save locations and adapter setup. Live tracking is version-pinned to Savage Wind 0.6.0-alpha.6 / BOTW 1.9.0; start your game launcher with SAVAGEWIND_CONTROL=27777 in its environment.
5. From the extracted directory, run `bun install`, then `bun run build`. The Millennium Starlight build uses the local Millennium plugin output location (`output_path = "auto"`). Fully exit and reopen Steam and enable Custom Achievements in Millennium.
6. Start the separate tracker in a terminal with `python tracker/daemon.py`. Keep it running while playing. Stop it with Ctrl+C. This archive does not install a background service.
7. Open the achievements panel and use Test notification. Live tracking should report its status while the supported game is running. Check your shortcut ID mapping if a notification is missing.

## Contents and limits
- Native-style local achievement panels, BOTW rules and a Python tracker.
- Ocarina: 66 objectives for Longshot v3.0.0 (source bd6a0cdd). Set HOS_CONTROL to ${XDG_DATA_HOME:-$HOME/.local/share}/custom-achievements/longshot.sock in the game launcher environment. See docs/LONGSHOT.md and docs/LONGSHOT-ACHIEVEMENTS.md. Only starter goals have been verified in real gameplay; the expanded set needs playthrough testing.
- Bloodborne: full 40-trophy BBPort event pack. Arceus: 38 save-based objectives. Odyssey: 35 save-based objectives. Pokopia: 11 objectives with experimental Recompia 2.0.1 live memory tracking, no mod required. See docs/POKOPIA-LIVE.md. First Friend and First Habitat were verified in gameplay. Configure with scripts/configure-game.py; see docs/NEW-GAMES.md. These four adapters have fixture tests but await real-game verification. Third-party source/license notices are included under docs/THIRD-PARTY.md and licenses/.
- This distribution replaces machine-specific shortcut IDs with 0 and uses an original neutral chime instead of the local Steam audio sample.
- Game files, ROMs, keys, save data, user progress, screenshots, credentials and node_modules are not included.
- Steam's private interface can change. This sanitized source archive has not been validated end-to-end on a clean machine. It is intended for developers and manual setup.
- Optional Steam-account cloud synchronization is available in plugin settings; see docs/CLOUD-SYNC.md. It requires a reachable public deployment and one-time pairing per device. This does not create official Steam profile achievements.
- Downloadable website pack envelopes do not yet have a one-click plugin importer.

## Source checks
`bun test`, `bun run typecheck`, `lua tests/notifications.lua`, and `python -m unittest discover -s tests -v` are the project's development checks. The distribution's zero shortcut IDs must be configured before gameplay testing.

## Repository layout
- `frontend/`, `backend/`, `resources/`: Millennium plugin and built-in catalogs.
- `tracker/`, `scripts/`: account-scoped trackers and game configuration tools.
- `tests/`, `docs/`: regression checks and adapter documentation.
- `website/`: full hosted application, Steam OpenID, cloud API, database schema and migrations. Runtime databases and credentials are not included.
- `docs-site/`: static GitHub Pages site and sanitized source download. GitHub Pages cannot run the authentication, uploads or cloud API; links open the hosted application.

## GitHub Pages
Publish `docs-site/` with the Pages workflow. Under repository Settings → Pages select **GitHub Actions**. The workflow uploads only this directory. It never publishes runtime data or backend files.

## Website development
From `website/`, install dependencies with `npm ci`, then use `npm run dev`. Production uses Cloudflare Workers and a D1 binding named `DB`; apply the migrations under `website/drizzle/`. Existing hosting metadata refers to the current deployment. Forks must provision their own backend and configure the endpoint in `tracker/cloud.py`.

## Distribution
The source preview includes an original notification chime. Game files, keys, saves and credentials are not distributed. Third-party notices are in `docs/THIRD-PARTY.md`, `licenses/`, and `website/lib/covers/sources.json`. No blanket license is assigned to third-party game artwork.
