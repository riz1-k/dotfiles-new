#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Import Omarchy Themes
# @vicinae.mode compact
# @vicinae.icon 📦
# @vicinae.packageName Rice
# @vicinae.description Copy Omarchy's stock themes into rice

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" theme import-omarchy --all
