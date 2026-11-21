# Bloodborne / BBPort adapter

Status: implemented and fixture-tested, not yet tested with a real installation.
Target source: deadinside28/bloodborne_pc commit
`0fc2921c45f8ff3900f6bfa43a299e9a4f532af4`.

Protocol references:
- https://github.com/deadinside28/bloodborne_pc/blob/0fc2921c45f8ff3900f6bfa43a299e9a4f532af4/src/runtime_trophy.c
- https://github.com/deadinside28/bloodborne_pc/blob/0fc2921c45f8ff3900f6bfa43a299e9a4f532af4/launcher/trophy_list.py

BBPort appends a v1 JSON event to `<user>/trophies.jsonl` and flushes it at each
trophy unlock. No manual save is needed. Our tracker polls every two seconds,
validates the configured TITLE_ID, version, numeric trophy ID and timestamp,
and only imports IDs in the player's catalog. It also reads historical IDs from
`<user>/trophy/NPWR05818_00/unlocked.txt`. No other communication IDs are selected.
Incomplete last JSON lines are retried, duplicate unlocks are monotonic, and
existing Zelda progress is unaffected. Files are read-only and bounded at 8 MiB.
This is account/user-folder trophy progress, not a per-character challenge set.

## Connect an installation

The bundled catalog now contains 40 trophies (34 base game, 6 Old Hunters).
A local XML import is no longer required. Use `scripts/configure-game.py
bloodborne --path /path/to/user --title-id CUSA03173 --steam-appid YOUR_ID`,
then rebuild and restart Steam and the tracker. Use your actual title ID.
See [NEW-GAMES.md](NEW-GAMES.md) for setup and source details.

The older `configure-bbport.py` remains an optional local XML importer; it
replaces the bundled list with the supplied catalog. Existing vector icons are
used by trophy grade. IDs remain `bb_trophy_<number>`.

Notifications and host-side sound use the same delivery path as BOTW/OOT.
Previously earned trophies can unlock and notify on the first configured scan.
Custom achievements beyond BBPort's native trophy events need a separate signal
source and are not implemented here. Other forks/formats are not presumed supported.

## Validation

23 Python tests and frontend tests pass, including complete/partial journal
appends, duplicates, wrong titles/versions, invalid IDs/timestamps, historic
unlocks, XML import, duplicates/entities, host restart and preserving other games.
Real unlock delivery still requires verification with a real BBPort install.
