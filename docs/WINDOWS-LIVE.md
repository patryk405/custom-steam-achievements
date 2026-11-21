# Windows live tracking (0.7.0 preview)

Install the [Windows package](https://github.com/patryk405/custom-steam-achievements/releases/download/v0.7.0/custom-steam-achievements-windows-x64.zip), then open **Custom Steam Achievements Setup** from Start.

## Ocarina of Time / Longshot

1. Select Ocarina, keep **Live tracking** checked, and choose the actual game `bin/longshot.exe` (not the Launcher).
2. Save. Setup creates `%LOCALAPPDATA%\custom-achievements\Ocarina of Time - Achievements.lnk`.
3. For the existing Steam shortcut, set Target to `"%LOCALAPPDATA%\custom-achievements\app\csa-tracker.exe"` (expand `%LOCALAPPDATA%` to your actual folder if Steam does not expand it), and Launch Options to `--launch-longshot`. Keep the game's name so its achievement panel is recognized. Alternatively, launch through the generated shortcut.
4. Open the game's Steam library page once, then play. Walk five metres or collect one Rupee.

Supported Longshot identification: `v3.0.0 (source bd6a0cdd)`, protocol 1. The launch helper enables the local `HOS_CONTROL` named pipe for this process. The tracker sends read-only status/subscription commands; it does not enable memory commands or modify Longshot files.

## Pokémon Pokopia / Recompia

1. Select Pokopia, keep **Live tracking** checked, and choose the compiled `pkp.exe` (not `Recompia.exe`).
2. Choose the actual extracted `exefs/main` used by that installation. The supported game build is Pokopia 2.0.1, NSO ID `76a489f3bd3642fa5e18bd83d32c98ba`.
3. Save and start Recompia normally. Only one instance of the configured `pkp.exe` should run.
4. Open the game's Steam library page once. Register a first Pokémon or build a habitat. If already earned, these achievements will not notify again.

The tracker reads live memory with normal user permissions. It checks the executable, account, process lifetime, NSO code signatures and game state before accepting counters. It never writes game memory or requires a mod/save. It refuses unsupported builds.

## Check the result

The achievement details should report **Live tracking**, and progress should update within a few seconds after two stable samples. A waiting/error message means no live progress is being accepted. These live configurations do not silently fall back to save files.

Windows CI tests real named pipes and real read-only access to synthetic child-process memory. Actual gameplay, Steam notifications and sound with these two Windows games still require user testing. Existing unlocked achievements and cloud progress are preserved.
