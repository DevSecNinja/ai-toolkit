#!/bin/bash
# Post-create script for the devcontainer.
# Called by devcontainer.json postCreateCommand after the container is built.
# mise (and the dotfiles) are preinstalled in the dotfiles-devcontainer image,
# so we only trust the repo config, install the pinned tools and wire up hooks.

set -euo pipefail

########################################
# Git — mark the workspace as a safe directory
# Avoids "detected dubious ownership" failures when git runs in the
# bind-mounted workspace (owned by a different uid than the container user).
########################################
git config --global --add safe.directory "$(pwd)"

########################################
# Mise — install the tools pinned in .mise.toml (lefthook)
########################################
mise trust --all --yes
mise install

########################################
# Lefthook — git hooks
########################################
mise exec -- lefthook install

echo "✅ Dev container setup complete!"
