#!/usr/bin/env bash
set -euo pipefail
src="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
base="${XDG_DATA_HOME:-$HOME/.local/share}"
dest="$base/custom-achievements/app"
plugins="$base/millennium/plugins"
if [[ ! -d "$base/millennium" ]]; then
  echo 'Install Millennium first: https://steambrew.app/'; exit 1
fi
if systemctl --user is-active --quiet custom-achievements-tracker.service; then
  systemctl --user stop custom-achievements-tracker.service
fi
mkdir -p "$dest" "$plugins" "$base/applications" "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
cp -R "$src/tracker/." "$dest/"
cp "$src/local.custom-achievements.star" "$plugins/"
chmod +x "$dest/csa-tracker"
unit="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/custom-achievements-tracker.service"
# Quote systemd's own syntax, including percent specifiers in home paths.
escaped="${dest//\\/\\\\}"
escaped="${escaped//\"/\\\"}"
escaped="${escaped//%/%%}"
cat > "$unit" <<EOF
[Unit]
Description=Custom Steam Achievements tracker
[Service]
ExecStart="$escaped/csa-tracker"
Restart=on-failure
[Install]
WantedBy=default.target
EOF
cat > "$base/applications/custom-achievements-setup.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Custom Steam Achievements Setup
Exec="$escaped/csa-tracker" --configure
Terminal=false
Categories=Game;
EOF
systemctl --user daemon-reload
systemctl --user enable --now custom-achievements-tracker.service
echo 'Installed. Restart Steam and enable Custom Achievements in Millennium.'
echo 'Open Custom Steam Achievements Setup from your applications menu to select game saves.'
