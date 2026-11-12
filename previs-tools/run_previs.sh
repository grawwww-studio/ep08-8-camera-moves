#!/usr/bin/env bash
# Render a previs shot dir (must contain params.json) in the sandboxed Blender container, then encode
# beauty_24fps.mp4 + depth_24fps.mp4 + check0.png. CPU by default ;
# --gpu renders with OptiX.
# Usage: run_previs.sh <shot_dir> [--one] [--gpu] [--lookdev] [--still] [--mask]
#   --one      frame 1 only, no encode (v8 behaviour)
#   --gpu      OptiX on the 4090
#   --lookdev  force look lookdev (real materials) whatever subject_params.look says
#   --frame N  render only frame N (1-based) for a check of a later beat; implies --one
#   --mask     also write the exact product mask (object-index pass of the can330 objects) as out/mask_NNNN.png, copied to <shot_dir>/mask0.png
#   --data     scene data only (camera, products, props per frame: screen-space numbers), no render: out/data.json -> <shot_dir>/data.json (CPU, seconds)
#   --with-data  render as usual and also write data.json (vt.py animatic builds)
#   --draft    animatic drafts (pv_sequence --draft): no depth pass, no mp4 encodes (beauty frames only)
#   --still    lookdev still: frame 1 at params.lookdev_still {w, h, samples}; also copied to <shot_dir>/still_lookdev.png
set -eo pipefail
D=$(realpath "$1"); LIB=$(dirname "$(realpath "$0")"); EXTRA=(); ONE=0; STILL=0; FRAME=1; SKIP=0; DATA=0; DRAFT=0
for a in "${@:2}"; do if [ "$SKIP" = 1 ]; then FRAME=$a; SKIP=0; EXTRA+=(-e PREVIS_FRAME=$a); continue; fi; case "$a" in
  --frame) ONE=1; SKIP=1;;
  --one) ONE=1; EXTRA+=(-e PREVIS_ONE=1);;
  --gpu) EXTRA+=(--gpus all -e NVIDIA_DRIVER_CAPABILITIES=all -e PREVIS_DEVICE=GPU);;   # 
  --mask) EXTRA+=(-e PREVIS_MASK=1);;
  --draft) DRAFT=1; EXTRA+=(-e PREVIS_NODEPTH=1);;
  --data) DATA=1; EXTRA+=(-e PREVIS_DATA=only);;
  --with-data) EXTRA+=(-e PREVIS_DATA=1);;
  --lookdev) EXTRA+=(-e PREVIS_LOOK=lookdev);;
  --still) ONE=1; STILL=1; EXTRA+=(-e PREVIS_ONE=1 -e PREVIS_STILL=1 -e PREVIS_LOOK=lookdev);;
  *) echo "unknown option $a" >&2; exit 2;;
esac; done
mkdir -p "$D/out"
docker run --rm --network none --read-only --tmpfs /tmp:size=2g -e HOME=/tmp "${EXTRA[@]}" --user 1000:1000 --cap-drop ALL \
  --security-opt no-new-privileges --memory 16g --pids-limit 512 -v "$D":/work -v "$LIB":/pvlib:ro -w /work \
  blender-versus:4.5.14 -b --factory-startup --python-exit-code 1 --python /pvlib/pv_render.py > "$D/blender.log" 2>&1 \
  || { tail -20 "$D/blender.log"; exit 1; }
grep -q PREVIS_DONE "$D/blender.log"
[ -f "$D/out/data.json" ] && cp "$D/out/data.json" "$D/data.json"
if [ "$DATA" = 1 ]; then echo "PREVIS_OK $D"; exit 0; fi
F=$(printf "%04d" $FRAME)
cp "$D/out/beauty_$F.png" "$D/check0.png"
[ -f "$D/out/mask_$F.png" ] && cp "$D/out/mask_$F.png" "$D/mask0.png"
[ "$STILL" = 1 ] && cp "$D/out/beauty_0001.png" "$D/still_lookdev.png"
if [ "$ONE" != 1 ] && [ "$DRAFT" != 1 ]; then
  FPS=$("${VT_PY:-python3}" -c "import json;print(json.load(open('$D/params.json')).get('fps',24))")
  ffmpeg -v error -y -framerate $FPS -i "$D/out/beauty_%04d.png" -c:v libx264 -crf 18 -pix_fmt yuv420p "$D/beauty_24fps.mp4"
  ffmpeg -v error -y -framerate $FPS -i "$D/out/depth_%04d.png" -c:v libx264 -crf 12 -pix_fmt yuv420p "$D/depth_24fps.mp4"
fi
echo "PREVIS_OK $D"
