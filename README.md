# 8 camera moves, 8 worlds: does a grey Blender plan make an AI video model move the camera the way you ask?

Material for the EP08 cold open of the Grawwww Studio channel.

- Video: https://youtu.be/psEtMEct_SA

## What the video tested

Eight classic camera moves (push-in, tilt, orbit, pull-out, truck, pedestal, dolly zoom, crane up), each in its own world. For every move we made the same shot twice with MiniMax H3, same still, same seed:

1. **With previs**: a grey Blender plan of the move is given to the model as the camera reference.
2. **Words only**: the same prompt, no video reference.

Then we measured, with optical flow, how closely the camera path of each take follows the planned path.

## Result

- **5 of 8** moves followed the plan with the previs (push-in, tilt, orbit, pull-out, crane up).
- **4 of 8** followed it with words only (push-in, tilt, pull-out, crane up).
- Truck and pedestal: neither take followed. Dolly zoom: neither passed its own rule.
- H3 usually moves more than planned: median WHOLE CAMERA PATH amplitude 1.41x the plan.

The criteria were written before any number was computed (see `_criteria` in `metrics/h3_metrics_night.json`). Full table: [`metrics/metrics_table.md`](metrics/metrics_table.md) and `.csv`.

## Layout

| Folder | What |
|---|---|
| `moves/NN-<move>/` | per move: previs recipe (`previs_params.json`), H3 prompt with previs, words-only prompt, seed, short README |
| `previs-tools/` | `pv_render.py` (Blender script that builds the grey plan from a params file), `run_previs.sh` (renders it), `layered_dollyzoom.py` (the dolly-zoom layered fallback) |
| `metrics/` | the measurement scripts and the results |
| `SHOTLIST.md` | the eight shots: move, world and what happens. |
| `diy-previs/` | a one-file Blender script that makes any of the 8 moves from a plain prompt, for you to try |

## Reproduce

1. **Grey plan.** Install Blender 4.5. Put one `previs_params.json` as `params.json` in a folder and run `blender -b --factory-startup --python previs-tools/pv_render.py` from that folder. It writes numbered PNG frames into `out/`; `previs-tools/run_previs.sh` shows how we ran it (in a container) and encoded the MP4 with ffmpeg. The moves are camera keyframes in the params (distance, angle, height, lens, target).
2. **Depth (Wan stage only, not part of the measurement).** Depth Anything V2 and Wan 2.2 Fun were used for the final edit; their workflows are not in this repo.
3. **H3.** Give MiniMax H3 your first frame as `<Picture 1>` and the grey plan as `<Video 1>`, paste `prompt_with_previs.txt`; for the control paste `prompt_words_only.txt` with no video. Seed in `seed.txt`, 1152x648, 124 frames, 24 fps. The H3 workflow graph is not included; any H3 runner that takes a first frame, a reference video and a seed will do.
4. **Measure.** Lay the files out as `previs/wN/beauty_24fps.mp4` (the grey plans) and `h3/night/wNp.mp4` / `wNw.mp4` (previs and words-only takes), then `python3 metrics/measure_h3_tests.py --night` (needs OpenCV and NumPy) and `python3 metrics/summarize_night.py`. Raw H3 takes are not in this repo.

## Tools

Blender 4.5, MiniMax H3, Depth Anything V2, Wan 2.2 Fun, one RTX 4090.

## Not here

The grey-plan videos (render them from `previs_params.json`), the H3 workflow graph, model weights, the raw H3 and Wan videos, stills, logos and any third-party reference footage.

## Licence

MIT for our code, prompts and numbers (see `LICENSE`; `NOTICE.md` says what that covers and what is not here). Not affiliated with MiniMax, Blender or the Wan team. No model weights are included.
