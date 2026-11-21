CUSTOM STEAM ACHIEVEMENTS 0.7.0 — PREVIEW

1. Install Millennium from https://steambrew.app/ (desktop Steam).
2. Close Steam. Extract this entire archive.
3. Windows: double-click Install.cmd. Linux: run bash install-linux.sh.
4. Start Steam and enable Custom Achievements in Millennium.
5. Open Custom Steam Achievements Setup from Start / your applications menu.
   Choose your game's save file (or BBPort user directory). Open the game's
   Steam library page once to connect its achievement notifications.

The tracker starts automatically when you sign in. Updates preserve progress.
Connect Steam cloud in the plugin settings to sync to another device.
Requires Windows 10/11 x64 or Linux x64 with glibc 2.35+, desktop Steam and
Millennium. Flatpak/Snap Steam and Decky are not included. Linux audio needs
paplay, pw-play or aplay. Do not run the installer as root.

Windows is experimental: bundled executable is smoke-tested on Windows,
but Steam integration and game readers still need real gameplay testing.
Save readers: BOTW, Arceus, Odyssey, Pokopia. Events: supported BBPort builds.
Live Ocarina and Pokopia readers support native Windows and Linux with a
compatible configured game runtime. Windows gameplay validation is pending. Installing the plugin alone does not add a game's
control socket or live launch wrapper. See docs for version requirements.

Data: Linux ~/.local/share/custom-achievements; Windows
%LOCALAPPDATA%\custom-achievements. Custom saves are only read, never changed.
The .star alone installs the Steam UI; it needs the tracker for automation.
These are community achievements, not Steamworks profile achievements.

Uninstall Linux: systemctl --user disable --now custom-achievements-tracker
then remove the unit, app directory, Setup .desktop and .star plugin file.
Uninstall Windows: remove CustomSteamAchievements from HKCU\Software\Microsoft\
Windows\CurrentVersion\Run, stop csa-tracker.exe, and remove the app folder,
Setup shortcut and .star plugin. Keep the data folder to preserve progress.

Source, adapters and licenses:
https://github.com/patryk405/custom-steam-achievements

WINDOWS LIVE SETUP
Open Custom Steam Achievements Setup and leave Live tracking enabled.
Ocarina: select the game bin/longshot.exe (Longshot v3.0.0 source bd6a0cdd).
Save settings. Setup creates Ocarina of Time - Achievements.lnk in the data
folder. Use it to launch, or set the existing Steam shortcut Target to the
installed csa-tracker.exe and Launch Options to --launch-longshot. Keep the
shortcut's name/artwork. This enables HOS_CONTROL for that game process only.
Pokopia: select the compiled pkp.exe and its actual exefs/main (2.0.1 build
76a489f3bd3642fa5e18bd83d32c98ba). Save settings and start Recompia normally.
Only one instance of the configured game may run. No admin rights or mods.
The panel should say Live tracking. It will not silently fall back to saves.
Test Ocarina with 5 metres of walking or one Rupee; Pokopia with a first dex
entry or habitat. Existing achievements stay unlocked; no progress is reset.
