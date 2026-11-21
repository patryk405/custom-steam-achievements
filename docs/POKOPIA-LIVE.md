# Pokopia: experimental live tracking without a mod

Implemented against Recompia source, with synthetic tests. **No real game was
started during development; gameplay validation is still pending.**

This prototype is for the native Linux Recompia game executable and Pokopia
2.0.1 main build `76a489f3bd3642fa5e18bd83d32c98ba`. Wine/Proton, AppImage launchers
that detach, Windows and macOS are not supported by this launch wrapper.

The CSA wrapper starts the game as its child. It opens `/proc/<child>/mem` read-only
and exposes five counters over a same-user Unix socket with permissions 0600.
The existing tracker queries it every two seconds. No mod, injection, game writes,
manual save, elevation, ptrace attach or system security setting changes are used.
Linux Yama ptrace_scope=1 permits the parent-child read; stricter host policies
can refuse it, in which case tracking reports an error rather than changing policy.

## Prepare an installation (does not launch it)

Run from the plugin source folder:

```sh
python scripts/configure-pokopia-live.py \
  --game-exe /path/to/recompia/pkp \
  --main /path/to/recompia/exefs/main \
  --game-dir /path/to/recompia \
  --steam-appid YOUR_UNSIGNED_SHORTCUT_ID
```

The main file must be the one actually loaded by this installation. The helper
validates its NSO build, decompression, SHA-256 text integrity and code signature;
it does not supply or modify game files. Compressed NSO text needs system liblz4.
It creates `$XDG_DATA_HOME/custom-achievements/launch-pokopia-live.sh`
(default `~/.local/share/custom-achievements/launch-pokopia-live.sh`). Set this as
the **Target** of the existing Steam shortcut, keeping its ID and artwork. The
helper prints the path but does not alter Steam or start the game itself.
Pass extra game arguments after `--` if necessary. Then build the plugin and
restart Steam and the tracker service. Do not point the wrapper back at Steam.

For validation without launch:

```sh
python scripts/launch-pokopia-live.py --check \
  --main /path/to/exefs/main --cwd /path/to/recompia -- /path/to/recompia/pkp
```

## What is checked before accepting progress

- Supported NSO build and mapped instruction windows match the chosen game image.
- Reads stay in mapped guest main/heap ranges; no arbitrary memory-read commands
  are exposed through the socket.
- Save state, game state and local player pointers exist; the player's vtable
  matches the referenced class, stage is valid and input is not locked.
- A complete snapshot must repeat consistently and its pointers remain unchanged.
- Two consecutive gameplay samples must have a stable identity and fresh monotonic timestamps. The save play-time counter may stay unchanged; regressions or large jumps require a new baseline. Pauses, loading,
  long sampling gaps and changed objects require a new baseline.
- Socket peer UID, protocol, build, freshness and metric bounds are validated.

The eleven existing achievements use dex/habitat/recipe counts, learned moves
and Water Gun's use count. Already-earned progress also counts when first read.
There is no new reset or invented test achievement. Source `pkp_coop_unlocks.cpp`
confirms the live move-history base/stride/learned flag; its use-counter layout
is inferred from the corresponding PokoHex serialized Skill record and remains
subject to gameplay verification. False-positive protection is conservative,
but only a real run can confirm offsets, pause behavior and the wrapper's startup.

The manifest defaults to `liveOnly: true`: no silent save fallback. The dormant
save adapter can be explicitly restored by removing `live`, or enabled as a
fallback with `liveOnly: false` and a configured save path.

## Later gameplay test

1. Start through the prepared shortcut and enter controllable gameplay.
2. Confirm the panel reports **Live tracking**, not `live-waiting` or save tracking.
3. With autosave off, build a first habitat or register a new Pokémon (use a
   not-yet-earned objective). Expect a card update and toast within a few seconds.
4. Pause/load/exit; confirm unavailable samples do not add progress.

## Source references

https://github.com/Dittobyte/Recompia/tree/4d7c1ff6f0e8cb7f23fb1f139495c55dc2130496

- `runtime/include/nxrt/memory.h`: guest addresses map directly to host addresses.
- `runtime/games/pkp/core/pkp_layout.h`: globals, clock, player, recipes, ability flags.
- `pkp_coop_discovery.cpp`: dex and habitat arrays.
- `pkp_coop_unlocks.cpp`: move history.
- `pkp_linkplay.cpp`: main build and instruction signature.
- `recomp/nxrecomp/nso.py`: NSO format reference.

GPL-3.0-or-later source references; the read-only adaptation is included in
`tracker/adapters/pokopia_live.py`. Existing PokoHex licence text is in licenses/.

## Native Windows (0.7.0 preview)

The Windows tracker does not need the Linux launch wrapper. In Setup, select
Pokopia and **Live tracking**, choose the compiled `pkp.exe` and the exact
`exefs/main` used by that installation, and save. Start Recompia normally.
Only one instance of that configured executable may run.

The reader resolves the process by full executable path, checks its owner SID
and creation time, and opens it with query/read permissions only. It uses
`VirtualQueryEx` and `ReadProcessMemory` inside the existing guest main/heap
ranges. Guarded, unmapped and unreadable pages are rejected. Every sample still
checks the NSO instruction probes and existing game-object/layout guards.
A new process resets the sampling baseline. No elevation, debug privilege,
injection, mod, game write, or save fallback is used.

The address mapping is shared with Windows in the pinned Recompia source
`runtime/include/nxrt/memory.h` (guest addresses equal host addresses).
Compressed NSO text now uses a bounded raw-LZ4 decoder bundled with the tracker;
Windows users do not need a separate liblz4 DLL.

Windows CI allocates the documented address ranges in a disposable child
process, changes synthetic dex data without writing any save, and exercises
the real Win32 reader and existing sampler. This verifies the platform code,
not actual Recompia gameplay: that final test remains pending. Builds other
than the verified 2.0.1 NSO are refused.
