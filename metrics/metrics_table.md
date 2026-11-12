# EP08 camera-move metrics (first takes, raw H3, 124 frames)

Source: `h3_metrics_night.json`, computed by `measure_h3_tests.py --night`, then `summarize_night.py`.

**Result: 5 of 8 moves followed the plan with the previs, 4 of 8 with words only.**
Rule (fixed before any number was computed): followed = follow score >= 0.70 and the main axis moves in the planned direction; the dolly zoom by its own written rule; tie = gap under 0.10.

## Overshoot: WHOLE CAMERA PATH · ALL AXES

`cam_amp` is the median, over the axes where the previs moves (pan x, pan y, log zoom), of take range / previs range. 1 = as big as planned; above 1 = H3 moved more than the previs. Production takes, moves 1 to 8: 1.88, 0.38, 1.32, 0.75, 1.74, 1.03, 1.5, 3.82; median 1.41.

## Per move

The follow score is the mean correlation of the take's camera path (pan x, pan y, log zoom, from optical flow) with the previs path. The per-move amplitude columns are labelled MAIN AXIS: take range / previs range on the previs's biggest axis. The last column is the WHOLE CAMERA PATH · ALL AXES value (`cam_amp`).

| # | Move | Seed | Follow (previs) | Follow (words only) | Followed with previs | Followed words only | Winner | MAIN AXIS amp, previs take | MAIN AXIS amp, words-only take | WHOLE CAMERA PATH · ALL AXES cam_amp, previs take |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | push-in | 777001 | 0.92 | 0.77 | yes | yes | previs | 1.13 | 1.22 | 1.88 |
| 2 | tilt | 777001 | 0.86 | 0.88 | yes | yes | tie | 1.45 | 1.5 | 0.38 |
| 3 | orbit | 777001 | 0.85 | 0.56 | yes | no | previs | 2.19 | 2.62 | 1.32 |
| 4 | pull-out | 777001 | 0.89 | 0.73 | yes | yes | previs | 0.75 | 0.77 | 0.75 |
| 5 | truck | 777001 | -0.28 | 0.09 | no | no | neither | 1.74 | 1.47 | 1.74 |
| 6 | pedestal | 777001 | 0.01 | -0.01 | no | no | neither | 1.29 | 0.55 | 1.03 |
| 7 | dolly-zoom | 777001 | -0.32 | -0.32 | no | no | neither | 0.37 | 0.38 | 1.5 |
| 8 | crane-up | 777001 | 0.92 | 0.91 | yes | yes | tie | 2.98 | 2.92 | 3.82 |

Note: the dolly zoom (move 7) is judged by its own rule, «helmet scale +16 % (161→187 px)», a different measure from `w7p.her_scale_f0_f123` (-45 %) in the JSON. The helmet figure is her helmet width read by eye on full frames at f0 and f123 (`_w7_rule` in the JSON, method field); `her_scale_f0_f123` is the automatic change of her red-jacket shoulder width (mask, mean of the 5 widest rows in the top 40 % of the jacket; `her_and_bg` in `measure_h3_tests.py`), so it also reacts to her turning or leaving the frame.

The pedestal retry (w6r) is reported apart in the JSON and never counted in the 5 of 8.
