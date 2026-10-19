#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Update Themes
# @vicinae.mode compact
# @vicinae.icon 📦
# @vicinae.packageName Rice
# @vicinae.description Pull every theme installed from git

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" theme update
