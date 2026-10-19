#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Next Theme
# @vicinae.mode silent
# @vicinae.icon 🎨
# @vicinae.packageName Rice
# @vicinae.description Switch to the next theme

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" theme next
