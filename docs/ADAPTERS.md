# Local automatic achievement tracking

The daemon reads game inputs and applies rules to local achievement state. It never
writes to a game save, attaches to game memory, or updates official Steam stats.

## Installed BOTW adapter

`resources/botw-adapter.json` defines the 38 automatically supported objectives shown in BOTW.
`tracker/adapters/botw.py` reads Switch 1.8/1.9 revision 0x4730, 1,027,248-byte
`game_data.sav` files. The matching caption file supplies the ending-clear flag.
Every five seconds, the daemon checks the newest slot in
`$XDG_DATA_HOME/savagewind/save/save_0` (default `~/.local/share/…`). It waits for
unchanged metadata across two checks before parsing, validates the structure,
and rechecks metadata afterwards. It ignores backups and older slots.

Unlocks become visible after the game saves, not at the exact moment of an event.
Existing save progress is recognized too. Automatic progress is cumulative and
never relocks when a save is rolled back. This version keeps one local progress
set per game; it does not isolate multiple player profiles. Alternative Savage
Wind profiles require an explicit root override; the default adapter follows
only the default save folder.

Conservative rules may trigger late: Your First Steps waits until leaving the
Plateau; home and special horse achievements wait for quest completion. “All
memories” means the completed Captured Memories quest. These choices are shown
in the details UI. Combat-method counts, no-death runs, ambiguous roleplay goals,
and other unverified signals are excluded from the BOTW catalogue.

Save names/types were checked against the user's own 1.9.0 Bootup schema.
Format references (no game assets or saves are bundled):
- https://github.com/marcrobledo/savegame-editors/tree/master/zelda-botw
- https://github.com/Revivedx/SavageWindRecomp/blob/main/tools/botw_save_convert.py

## Add another game

1. Add its catalogue and `matchNames` aliases in `resources/catalog.json` and build
   the Steam plugin. Each achievement needs a stable id, name, description,
   positive integer target, and an icon key.
2. Create a producer appropriate to that game (a game mod, event exporter, or
   read-only save parser). There is no universal way to infer arbitrary events.
3. For a producer that can write JSON, emit schema 1 with a matching `game` id
   and numeric/boolean `metrics`. Write to a temporary file then rename atomically.
4. Put an adapter manifest in `~/.local/share/custom-achievements/adapters/` and
   restart `custom-achievements-tracker.service`. The JSON-snapshot reader is
   already implemented. A manifest with an existing adapter id overrides that
   adapter, allowing e.g. a custom save root. Do not install two adapters for the
   same game unless their objectives are deliberately disjoint.
5. Other binary formats require another reader under `tracker/adapters/` plus
   registration in the adapter host. The evaluation, persistence and UI stay shared.

See `examples/oot-snapshot-adapter.json` and `examples/oot-progress.json`.
They are documentation fixtures, not a working Longshot producer; they are NOT
installed automatically and never award real achievements.

Rule operators: `any`, `all`, `count` (boolean flags), `number`, `sum` (numeric
metrics). Missing or invalid values produce no unlock. Thresholds equal to the
catalogue target show partial progress; otherwise they resolve to a boolean
objective. Rules are data, never executable code. Input files are local and are
not tamper-proof or independently verified.

## State and controls

- Service: `systemctl --user status custom-achievements-tracker`
- Automatic records: `~/.local/share/custom-achievements/state.json`
- Preferences: `~/.local/share/custom-achievements/preferences.json`
- Manual records remain in Millennium config, separately from automatic records.

“Enable automatic save tracking” pauses/resumes observation. Previously earned
automatic progress stays visible. Only original line icons are installed.

To stop the background process completely:
`systemctl --user disable --now custom-achievements-tracker.service`
Disabling only the Millennium plugin does not stop this independent service.

## Validation

`python -m unittest discover -s tests -v` covers synthetic BOTW data, missing
signals, partial writes, wrong versions, cumulative progress, restart persistence,
paused tracking, cross-game rejection and the generic JSON adapter. Synthetic
fixtures stay in temporary directories and are never mixed into live state.

At installation the actual BOTW save folder did not yet exist. The running
service reports “Waiting for the first save or autosave”. An actual in-game
unlock has not yet been observed; schema validation and synthetic integration
checks must not be described as a verified gameplay unlock.


## Live BOTW adapter

`tracker/adapters/botw_live.py` reads the current-read flag buffer from Savage Wind
0.6.0-alpha.6 / BOTW 1.9.0 via the read-only subset of the local control protocol.
It validates code signatures and every flag hash before evaluating values.
`botw-adapter.json` enables it with `live: savagewind-1.9.0`. A refused connection,
loading world or unsupported layout falls back to save tracking. Other games
must supply their own live adapter; the rule engine and notification delivery
remain shared. Existing snapshot adapters can export metrics without saving the
game, but require a game-specific producer.

To revert to save-only tracking remove `live` from the BOTW manifest and
`export SAVAGEWIND_CONTROL=27777` from `~/.local/bin/savagewind`, then restart the
tracker and game. No game executable was patched.

Live integration: all 180 configured signals read successfully from the running
game. Synthetic tests exercise changes without saves and reject changed flag
identities/getter signatures. A newly-earned real achievement remains unverified.
