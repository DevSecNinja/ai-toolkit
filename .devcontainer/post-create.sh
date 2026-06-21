#!/bin/bash
# Post-create script for the devcontainer.
# Called by devcontainer.json postCreateCommand after the container is built.

set -euo pipefail

########################################
# Mise — tool version manager (pins lefthook in .mise.toml)
########################################
curl https://mise.run | sh
# shellcheck disable=SC2016 # Intentionally single-quoted to defer expansion to .bashrc
echo 'eval "$(~/.local/bin/mise activate bash)"' >>~/.bashrc
~/.local/bin/mise install

########################################
# Git — mark the workspace as a safe directory
# Avoids "detected dubious ownership" failures when git runs in the
# bind-mounted workspace (owned by a different uid than the container user).
########################################
git config --global --add safe.directory "$(pwd)"

########################################
# Lefthook — git hooks
########################################
~/.local/bin/mise exec -- lefthook install

echo "✅ Dev container setup complete!"
