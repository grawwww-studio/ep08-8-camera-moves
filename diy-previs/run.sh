#!/usr/bin/env bash
# run.sh <script.py> <outdir>: headless Blender 4.5 in the same sandbox flags as run_previs.sh (CPU, no network).
# The script's own OUT is under /tmp inside the container; we copy it out through the mounted folder by overriding OUT with sed.
set -e
S=$(realpath "$1"); O=$(realpath "$2"); mkdir -p "$O"
sed 's#^OUT = .*#OUT = "/out/" + MOVE + ".mp4"#' "$S" > "$O/_run.py"
docker run --rm --network none --read-only --tmpfs /tmp:size=2g -e HOME=/tmp --user 1000:1000 --cap-drop ALL \
  --security-opt no-new-privileges --memory 4g --pids-limit 512 -v "$O":/out -w /out \
  blender-versus:4.5.14 -b --factory-startup --python-exit-code 1 --python /out/_run.py
rm -f "$O/_run.py"
