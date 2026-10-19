#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Pick Theme
# @vicinae.mode silent
# @vicinae.icon 🎨
# @vicinae.packageName Rice
# @vicinae.description Open the theme carousel

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" theme picker
