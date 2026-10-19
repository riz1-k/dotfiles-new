#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Set Theme
# @vicinae.mode compact
# @vicinae.icon 🎨
# @vicinae.packageName Rice
# @vicinae.description Switch to a theme by name
# @vicinae.argument1 { "type": "text", "placeholder": "theme name" }

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" theme set "$1"
