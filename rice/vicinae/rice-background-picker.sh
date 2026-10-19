#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Pick Background
# @vicinae.mode silent
# @vicinae.icon 🖼️
# @vicinae.packageName Rice
# @vicinae.description Open the background carousel for the current theme

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" bg picker
