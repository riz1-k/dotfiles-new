#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Next Background
# @vicinae.mode silent
# @vicinae.icon 🖼️
# @vicinae.packageName Rice
# @vicinae.description Cycle the current theme's backgrounds

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" bg next
