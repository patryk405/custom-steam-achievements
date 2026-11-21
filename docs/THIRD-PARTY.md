# Adapter and catalog sources

- `tracker/adapters/arceus.py` is a Python read-only adaptation of PKHeX's
  SwishCrypto / SCBlock / SCXorShift32 format algorithms, GPL-3.0. PKHeX contributors:
  https://github.com/kwsch/PKHeX . License: `licenses/PKHeX-GPL-3.0.txt`.
  Save metrics are documented in `PKHeX.Core/Saves/Access/SaveBlockAccessor8LA.cs`.
  The modified source is included here; this file retains its GPL-3.0 terms.
- Odyssey format and field mapping reference Alex Norum's
  https://github.com/anorum/mario_odyssey_save_editor at
  `2c781f390b051c3cca4a12d0f8b4ec304862eef3`. The new reader adds bounds, cycle,
  schema and type checks and removes all writing. MIT notice in
  `licenses/odyssey-save-editor-MIT.txt`.
- Bloodborne trophy definitions/IDs: https://github.com/bloodborne-native/bloodborne-runtime
  at `d97fc678a912b2b6c23715f24ab0f197f646d55b`, `gpu/shim/trophy_catalog.json`.
  GPL-2.0 license supplied in `licenses/bloodborne-runtime-GPL-2.0.txt`.
  Definitions are kept in `resources/catalog.json`; game artwork is not copied.
- Pokopia achievement definitions: The Modtopia contributors, Community
  Achievements mod, declared MIT by its `mod.toml` and the public mod catalog:
  https://pokopia-native.vercel.app/mods/catalog.json (0.4.2, inspected 2026-11-21).
  Read protocol: Recompia `launcher/src-tauri/src/achievements.rs` at
  `4d7c1ff6f0e8cb7f23fb1f139495c55dc2130496`.
  Icons here are existing plugin vector motifs, not the separately licensed
  community images. No mod executable is redistributed or installed.

Third-party license terms apply to their respective contributions. This is not
an endorsement by the game publishers or the referenced projects.

Pokopia direct save reader: GPL-3.0 adaptation of PokoHex by berichan and
contributors, https://github.com/berichan/PokoHex at
`2de3651266877bb0d765e4b5cd273dc7e2e36f96`.
References: SaveFile.cs, SaveLayout.cs, Catalogue.cs, PlayerAbilities.cs, Skill.cs.
License: licenses/PokoHex-GPL-3.0.txt. Numeric public catalogue indices are derived
from its CatalogueInfo filters; no game text/images are included in the layout.
The earlier Modtopia attribution concerns achievement titles/descriptions only;
its mod and journal are no longer used by the tracker.
