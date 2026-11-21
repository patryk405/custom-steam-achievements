# Custom Steam Achievements

## Download

Ready-to-install [Windows x64](https://github.com/patryk405/custom-steam-achievements/releases/download/v0.6.0/custom-steam-achievements-windows-x64.zip) and [Linux x64](https://github.com/patryk405/custom-steam-achievements/releases/download/v0.6.0/custom-steam-achievements-linux-x64.zip) packages include the plugin, standalone tracker and a native game setup window. No Python or Bun installation is needed. Install [Millennium](https://steambrew.app/) first, close Steam, extract the ZIP, and run `Install.cmd` (Windows) or `bash install-linux.sh` (Linux).

See [package instructions and compatibility](packaging/README.txt). Windows is experimental; live Ocarina/Pokopia adapters currently require Linux. Open each supported game's library page once to connect notifications. Updates preserve progress. [Plugin only](https://github.com/patryk405/custom-steam-achievements/releases/download/v0.6.0/local.custom-achievements.star) requires a separately running tracker.

Builds run on Windows and Ubuntu 22.04; the executable resource/lock smoke tests must pass before release publication. This does not replace gameplay testing on each supported runtime.


[Website](https://patryk405.github.io/custom-steam-achievements/) · [Pack library](https://patryk405.github.io/custom-steam-achievements/?view=library) · [Steam account](https://patryk405.github.io/custom-steam-achievements/?view=account)

The packages above are the easiest installation path. The instructions below are for building from source. Big Picture and Decky are not included.

## Build from source
1. Install Millennium using https://steambrew.app/ and confirm it works in desktop Steam.
2. Extract this archive. Install Bun and Python 3 if needed.
3. Add your game to Steam as a non-Steam shortcut. Set its numeric shortcut ID in `resources/shortcut-ids.json`: all IDs are intentionally 0 in this source distribution. Alternatively, open the supported game’s library page once; the plugin saves its shortcut ID at runtime.
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
- Steam's private interface can change. Packages pass automated build and resource checks, but clean-machine Steam integration remains experimental.
- Optional Steam-account cloud synchronization is available in plugin settings; see docs/CLOUD-SYNC.md. It requires a reachable public deployment and one-time pairing per device. This does not create official Steam profile achievements.
- Downloadable website pack envelopes do not yet have a one-click plugin importer.

## Source checks
`bun test`, `bun run typecheck`, `lua tests/notifications.lua`, and `python -m unittest discover -s tests -v` are the project's development checks. The distribution's zero shortcut IDs must be configured before gameplay testing.

## Repository layout
- `frontend/`, `backend/`, `resources/`: Millennium plugin and built-in catalogs.
- `tracker/`, `scripts/`: account-scoped trackers and game configuration tools.
- `tests/`, `docs/`: regression checks and adapter documentation.
- `website/`: archived implementation and shared pack definitions/assets.
- `web/`: React application published on GitHub Pages.
- `supabase/`: production Steam OpenID API, cloud synchronization, packs and database schema. Runtime data and credentials are not included.
- `docs-site/`: static GitHub Pages site and sanitized source download. The library and account interface run on Pages; the Supabase API handles authentication, uploads and cloud progress.

## GitHub Pages
Run `npm ci --prefix web`, `npm run typecheck --prefix web`, and `npm run build --prefix web`. Publish `docs-site/` with the Pages workflow. Under repository Settings → Pages select **GitHub Actions**. The workflow uploads only this directory. It never publishes runtime data or backend files.

## Website development
Run `npm ci --prefix web`, then `npm run dev --prefix web`. Production authentication accepts only the configured GitHub Pages origin. Set the frontend and API URLs in `web/src/api.ts`, `supabase/functions/achievements/index.ts`, and `tracker/cloud.py` for your own deployment.

Apply `supabase/schema.sql` to a new Supabase database. Deploy the `achievements` Edge Function with platform JWT verification disabled: it verifies Steam assertions and its own hashed browser/device tokens. The service role credential is available only through Supabase runtime environment variables, never in frontend code. All tables have RLS enabled and deny direct browser access.

Browser sessions use sessionStorage and a verifier-bound one-time login exchange. Steam authenticates the user on its own site and returns to GitHub Pages. Sign out revokes the browser token; device access is managed separately in the account panel.

## Distribution
Version 0.5.0 uses the Supabase backend; older 0.4.x clients need updating to keep cloud sync working.

The source preview includes an original notification chime. Game files, keys, saves and credentials are not distributed. Third-party notices are in `docs/THIRD-PARTY.md`, `licenses/`, and `website/lib/covers/sources.json`. No blanket license is assigned to third-party game artwork.
