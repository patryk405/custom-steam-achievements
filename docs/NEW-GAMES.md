# Additional game adapters

Implemented and tested with synthetic fixtures, **not yet validated in real gameplay**.
Existing BOTW/OOT progress is preserved. These packs are local achievements, not Steamworks trophies.

| Game | Pack | Source of progress |
| --- | ---: | --- |
| Bloodborne / BBPort | 40 (34 base + 6 Old Hunters) | BBPort native trophy journal; no manual save |
| Pokémon Legends: Arceus | 38 | Actual `main` save, including autosaves |
| Super Mario Odyssey | 35 | Actual selected `File1.bin` / other slot save, including autosaves |
| Pokémon Pokopia / Recompia | 11 | Experimental live memory reader; no mod or save |

## Selected recompilers

Research on 2026-11-21 used GitHub stars as a rough popularity proxy among found
projects, not measured player counts. Repositories can be renamed; revisions pin
what was inspected.

- [PokeL-ARecomp](https://github.com/fabioschmidt01/PokeL-ARecomp), 118 stars,
  revision `91e62268889f95c6266dcdba1f7fbb8f7132cf2a`.
- [super-odyssey-pc-recomp](https://github.com/Simon3Sarkis/super-odyssey-pc-recomp),
  about 500 stars, revision `99f1f9deddb64af9db5a0f53de81428369745504`.
- [Recompia](https://github.com/Dittobyte/Recompia), about 950 stars,
  revision `4d7c1ff6f0e8cb7f23fb1f139495c55dc2130496`.

The first two integrations consume the games' native save formats rather than a
recompiler-specific memory address. They may also work with other hosts that
write identical saves, but that compatibility is not verified. No live memory
tracking is claimed for these games. Autosave must be enabled for unattended
updates; otherwise progress updates on manual saves.

## Configuration

Run from the plugin source folder. Supply the **actual unsigned app ID of your
non-Steam shortcut**, not a store app ID. An unconfigured adapter does not scan
for saves or unlock achievements. The script backs up changed settings.

```sh
python scripts/configure-game.py arceus --path '/path/to/save/main' --steam-appid YOUR_ID
python scripts/configure-game.py odyssey --path '/path/to/save/File1.bin' --steam-appid YOUR_ID
python scripts/configure-game.py pokopia --path '/path/to/save/account/PROFILE/G00/CMNDAT.BIN' --steam-appid YOUR_ID
python scripts/configure-game.py bloodborne --path '/path/to/bbport/user' --title-id CUSA03173 --steam-appid YOUR_ID
bun run build
systemctl --user restart custom-achievements-tracker.service
```

Then fully restart Steam. CUSA03173 is an example; use your game's actual title
ID. Only the selected save slot is read, not backup folders. Existing saved
progress can unlock achievements on the first scan. Our reader never writes to
game files. Progress is monotonic and not automatically cleared on a new save.

For the optional Pokopia save adapter, select the active profile's `G00/CMNDAT.BIN` file. Only game
version 2.0.1 (save revision 0x0200017D) is supported. The tracker independently
decompresses and reads the file. Community Achievements is not used or required.
It waits while Recompia's sibling `.commit` marker indicates an unfinished save.

## What the packs cover

Arceus: ranks 1–10, five ride Pokémon, five noble battles and Arceus, Pokédex
milestones, Lost and Found, mass release, distortions, Unown, wisps, satchel
upgrades and recovered satchels. Rules use typed, named save blocks documented
by PKHeX. No inferred starter selection or unverified memory offsets are used.

Odyssey: 15 kingdom unlocks, 13 kingdom moon milestones, seven total moon
milestones. Counts use `WorldInfo.PayShineNum` and `UnlockedWorldId`, as in the
referenced save editor. These are recorded moon totals, not a claim of every
unique moon or every possible in-game accomplishment.

Pokopia: 11 objectives: registered Pokédex entries (1/25/100/150), built
habitats (1/5/15), learned recipes (100/250), ten learned moves and fifty Water Gun
uses. Unknown/catalogue padding entries are excluded. Seen Pokémon and discovered
but unbuilt habitats do not count. Other former mod objectives were removed because
we do not have verified equivalent save fields. Existing matching IDs/unlocks are
preserved; the previous 51-entry catalog is backed up locally.

Bloodborne: the complete native trophy set with IDs 0–39. The mapping comes from
bloodborne-native/bloodborne-runtime's published trophy catalog, but this reader
uses **BBPort's JSONL protocol**, not that other runtime's `trophies-v1.log` format.

## Verification still needed

After configuring a real install, earn one objective, wait for its event or
save/autosave, and check the Steam card, toast and sound. Restart the tracker to
check persistence. Expanded sets need playthrough coverage. Parser tests cover
checksum failure, wrong save type, missing signals, partial journals, future
and unknown entries, malformed BYML, out-of-range values, restart persistence
and preserving existing games. No real game files are included in fixtures.

Pokopia now defaults to live-only tracking. See [POKOPIA-LIVE.md](POKOPIA-LIVE.md)
for the native Linux launch wrapper. The save reader is retained for explicit
fallback use, not silently used when the live reader is unavailable.
