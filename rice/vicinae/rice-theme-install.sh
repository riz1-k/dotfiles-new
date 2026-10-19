#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Install Theme
# @vicinae.mode compact
# @vicinae.icon 📦
# @vicinae.packageName Rice
# @vicinae.description Install a theme from a git repository (Omarchy format)
# @vicinae.argument1 { "type": "text", "placeholder": "git URL" }

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" theme install "$1"
