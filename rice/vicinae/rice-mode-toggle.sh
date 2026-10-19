#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Toggle Light/Dark Theme
# @vicinae.mode silent
# @vicinae.icon 🌗
# @vicinae.packageName Rice
# @vicinae.description Switch to the current theme's light or dark pair

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" mode toggle
