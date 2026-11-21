CUSTOM STEAM ACHIEVEMENTS 0.6.0 — PREVIEW

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
Live Ocarina and Pokopia readers currently require Linux and a compatible
configured game runtime. Installing the plugin alone does not add a game's
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
