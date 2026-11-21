# Longshot live adapter (experimental)

Supports the installed `v3.0.0 (source bd6a0cdd)` build and control protocol 1.
Source: https://git.magicbean.dev/MagicBeanDev/Longshot/src/tag/v3.0.0/docs/control.md

The game launcher exports HOS_CONTROL to
`${XDG_DATA_HOME:-$HOME/.local/share}/custom-achievements/longshot.sock`.
The bridge is same-user only. The adapter sends only `status` and read-only `subscribe` requests; it never injects
input, reads raw memory or changes game/save files. No HOS_CONTROL_MEM is needed.
The launcher backup is `~/Games/Longshot/longshot.before-achievements`.
A Longshot update can replace the launcher: reapply the environment setting and
validate the new version before updating the supported build check.

The 66-objective set is documented in [LONGSHOT-ACHIEVEMENTS.md](LONGSHOT-ACHIEVEMENTS.md). The original starter objectives are preserved:
- First Steps: walk 5 metres in one tracker/game session. Uses horizontal sampled
  positions in metres, omits teleports, loading, cutscenes, stale samples and map changes.
  A curved route between samples may undercount; walk a little farther if needed.
- Pocket Change: wallet has at least 1 Rupee. Existing wallet balances count.

The shared tracker polls every 2 seconds. The shared Steam notification path
handles the toast and audio. BOTW progress and its adapter are unchanged.
Partial walking progress is session-based; completed unlocks persist.
All 66 OOT objectives have live rules. No save-file fallback for OOT.

Validation: unit tests and a fake Unix control server exercised both unlocks,
stale/loading/version rejection, scene/teleport/restart handling and integration
with the host without writing actual player progress. Real gameplay verification
is still pending; no game was launched during implementation.

Manual test: launch the existing Ocarina shortcut in Steam, enter gameplay, walk
forward several metres, then collect a Rupee. Check two notifications and audio.
The OOT achievement dialog should show `Live tracking — no save required`.

## Millennium hot reload on this host

After `bun run build`, verify `plugin.status` and a successful `get_state` FFI response.
Starlight can report restarted while the backend dies when its MEP connection closes.
Use `node scripts/mep-reload-hold.mjs plugin.restart '{"name":"local.custom-achievements"}'`
and keep that process running until Steam exits. Do not stop it as task cleanup.
A live test on 2026-11-21 detected First Steps automatically; RPC recovery delivered
the pending notification and host audio playback succeeded.

## Windows (0.7.0 preview)

The native Windows reader connects to Longshot's existing byte-mode named pipe;
it sends the same `status` and `subscribe` requests as Linux. It checks the
server PID, creation time, current-user SID and configured executable path,
plus the existing protocol and game-version checks. Reads and writes have
bounded deadlines. No raw-memory access is enabled.

In Setup, select Ocarina, keep **Live tracking** enabled, choose the game's
`bin/longshot.exe`, and save. Launch through the generated `.lnk`, or point the
existing Steam shortcut at the installed `csa-tracker.exe` with launch options
`--launch-longshot`. This helper sets `HOS_CONTROL=csa-longshot-v3` only for its
child, preserves the game working directory and waits for the child to exit.
Launching directly without that environment setting will not expose the pipe.

Windows CI exercises real local named pipes, walking and flag responses,
timeouts and version rejection with a disposable fake game. Actual Windows
Longshot gameplay remains unverified. The supported version is still
`v3.0.0 (source bd6a0cdd)`; newer versions are rejected rather than assumed safe.

Transport source: [Longshot control bridge](https://git.magicbean.dev/MagicBeanDev/Longshot/src/branch/main/docs/dev/reference/control-bridge.md),
`host/control.c` (Windows `PIPE_TYPE_BYTE`, local current-user DACL).
