#!/usr/bin/env bash
set -euo pipefail

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
plugin_id=io.github.vitorpacheco.streamcam
plugin_dir="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/$plugin_id"

if ! command -v python3 >/dev/null; then
  echo "Missing dependency: python3." >&2
  exit 1
fi
message() { python3 "$source_dir/backend/i18n.py" "$@"; }

for command_name in omarchy omarchy-shell v4l2-ctl; do
  if ! command -v "$command_name" >/dev/null; then
    message 'Missing dependency: {name} (Python and v4l-utils are required).' "name=$command_name" >&2
    exit 1
  fi
done
if [[ -e "$plugin_dir" || -L "$plugin_dir" ]]; then
  message 'Already exists: {path}. Remove the plugin through Omarchy before reinstalling.' "path=$plugin_dir" >&2
  exit 1
fi
omarchy plugin validate "$source_dir"
omarchy-shell shell ping >/dev/null
mkdir -p -- "$plugin_dir/backend"
cp -- "$source_dir/manifest.json" "$source_dir/Widget.qml" "$source_dir/ControlRow.qml" "$source_dir/Preview.qml" \
  "$source_dir/I18n.qml" "$source_dir/translations.json" "$source_dir/README.md" "$source_dir/LICENSE" "$plugin_dir/"
cp -- "$source_dir/backend/streamcam.py" "$source_dir/backend/i18n.py" "$plugin_dir/backend/"
cp -R -- "$source_dir/docs" "$plugin_dir/docs"
omarchy-shell shell rescanPlugins
omarchy plugin enable "$plugin_id"
message 'StreamCam installed. Click the camera icon in the bar.'
