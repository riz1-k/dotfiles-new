#!/bin/bash

# @vicinae.schemaVersion 1
# @vicinae.title Rice Doctor
# @vicinae.mode fullOutput
# @vicinae.icon 🩺
# @vicinae.packageName Rice
# @vicinae.description Check that every app follows the theme

rice=$(command -v rice || echo "$HOME/.local/bin/rice")
exec "$rice" doctor
