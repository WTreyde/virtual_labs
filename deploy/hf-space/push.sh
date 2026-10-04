#!/usr/bin/env bash
# Push the current main to a Hugging Face Docker Space (replay-only; no secrets are sent).
# Usage: deploy/hf-space/push.sh <hf-username>/<space-name>
# Auth: run `huggingface-cli login` (or `hf auth login`) first, or export HF_TOKEN with write access.
set -euo pipefail
space="${1:?usage: deploy/hf-space/push.sh <hf-username>/<space-name>}"
root="$(git rev-parse --show-toplevel)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
git -C "$root" archive HEAD | tar -x -C "$tmp"
cp "$root/deploy/hf-space/README.md" "$tmp/README.md"   # Space settings live in README front-matter
rm -f "$tmp/.env"
# The Hub rejects plain binary files; the Space needs none of these (README screenshots, Finder metadata).
rm -rf "$tmp/docs/img"
find "$tmp" -name .DS_Store -delete
cd "$tmp"
git init -q -b main
git lfs install --local >/dev/null 2>&1 || true
git lfs track "*.png" "*.jpg" >/dev/null 2>&1 || true   # the Hub rejects plain binaries
git add -A
git -c user.name="LabForge" -c user.email="labforge@users.noreply.huggingface.co" commit -qm "Deploy $(git -C "$root" rev-parse --short HEAD)"
url="https://huggingface.co/spaces/$space"
if [ -n "${HF_TOKEN:-}" ]; then url="https://user:${HF_TOKEN}@huggingface.co/spaces/$space"; fi
git push --force "$url" main
echo "Pushed. Build log and app: https://huggingface.co/spaces/$space"
