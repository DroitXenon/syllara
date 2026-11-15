#!/bin/zsh
# Install (or reinstall) the daily `syllara check` launchd job for the current user.
set -euo pipefail

repo="${0:A:h:h}"
bin="$repo/.venv/bin/syllara"
label="com.syllara.check"
dest="$HOME/Library/LaunchAgents/$label.plist"

[[ -x "$bin" ]] || { echo "Missing $bin — create the venv first (see README)." >&2; exit 1; }
mkdir -p "$HOME/.syllara/logs" "$HOME/Library/LaunchAgents"

sed -e "s|__SYLLARA_BIN__|$bin|" -e "s|__HOME__|$HOME|g" "$repo/launchd/$label.plist" > "$dest"

launchctl bootout "gui/$UID/$label" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$dest"
echo "Installed $dest (runs daily at 08:00)."
echo "Run now:   launchctl kickstart gui/$UID/$label"
echo "Uninstall: launchctl bootout gui/$UID/$label && rm $dest"
