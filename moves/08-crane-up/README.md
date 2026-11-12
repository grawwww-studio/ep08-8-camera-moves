# Move 8: crane-up

- `previs_params.json`: recipe for the grey plan (read by `previs-tools/pv_render.py` inside Blender 4.5). Render it to get the grey plan (124 frames, 24 fps).
- `prompt_with_previs.txt`: H3 prompt with the grey plan as `<Video 1>`. `prompt_words_only.txt`: same prompt without the video reference.
- Seed: 777001 (the same for both arms).
- Follow score, previs: 0.92; words only: 0.91. MAIN AXIS amplitude (previs take): 2.98x the plan.
