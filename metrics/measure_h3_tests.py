#!/usr/bin/env python3
"""EP08 8 worlds pre-approval-1 H3 tests: the numbers (video-director 2026-11-09). CPU; run under tools/cpujob with the vt.py venv.
cam_follow / cam_amp = review_metrics follow(global_path(previs), global_path(take)) on frames 0-106 (H3 used the first 107 frames of the
121-frame previs: grid 17k+5, audit D1). Dolly zoom (w7*): cumulative scale of tracked corners in a box on her (x 18-48 %, y 5-100 %)
and outside it beyond x 55 % (the valley and spires), f0 -> f106 and f0 -> f123. Orbit (w3*): the take's pan range and log zoom.
usage: measure_h3_tests.py w3t1 w7t1 w8t1   -> metrics/h3_metrics.json
Night mode (2026-11-10, production + words-only takes after approval 1): previs and takes are 124 f, N = 124.
usage: measure_h3_tests.py --night [w1p w1w ...]   (default: all 16) -> metrics/h3_metrics_night.json
  per take: follow / amp vs the previs on all 124 f, path ranges, timing of the dominant axis (frame where the previs and the take reach
  10 / 50 / 90 % of their own range; offset = take - previs, + = late); w7*: her scale from the red-jacket shoulder width (largest row
  widths of the red mask, top 40 % of it) and the background scale from tracked corners right of her mask (cumulative, f0 -> f123)."""
import json, math, sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_metrics as R

P = Path(__file__).resolve().parent.parent   # repo root; expects previs/wN/beauty_24fps.mp4 and h3/night/<take>.mp4 (see README)
N = 107


def region_scale(fr, box):
    out, prev = [0.0], R.gray(fr[0]); hh, ww = prev.shape
    mask = np.zeros_like(prev); x0, x1, y0, y1 = box
    mask[int(hh * y0):int(hh * y1), int(ww * x0):int(ww * x1)] = 255
    for f in fr[1:]:
        g = R.gray(f); ds = 0.0
        p0 = cv2.goodFeaturesToTrack(prev, 300, 0.01, 4, mask=mask)
        if p0 is not None and len(p0) >= 8:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None); ok = st.ravel() == 1
            if ok.sum() >= 8:
                Mx, _ = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
                if Mx is not None:
                    ds = float(np.log(max(1e-3, np.hypot(Mx[0, 0], Mx[1, 0]))))
        out.append(out[-1] + ds); prev = g
    return np.array(out)


def progress_times(path):
    """Frames where a cumulative path reaches 10/50/90 % of its net travel (start -> end)."""
    a = np.asarray(path, float); d = a[-1] - a[0]
    if abs(d) < 1e-6:
        return None
    q = (a - a[0]) / d
    return [int(np.argmax(q >= k)) for k in (0.1, 0.5, 0.9)]


def red_mask(f):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    m = (((hsv[..., 0] < 8) | (hsv[..., 0] > 170)) & (hsv[..., 1] > 110) & (hsv[..., 2] > 50)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return None, None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return (lab == k), st[k]


def her_and_bg(fr):
    """Her: red-jacket shoulder width (px, mean of the 5 widest rows in the top 40 % of the jacket). Background: cumulative log scale
    of corners right of her (x > jacket right + 4 % W, y < 85 % H)."""
    widths, bg, prev, prevmask = [], [0.0], None, None
    for f in fr:
        m, st = red_mask(f)
        if m is None:
            widths.append(None)
        else:
            y0, hgt = st[cv2.CC_STAT_TOP], st[cv2.CC_STAT_HEIGHT]
            rows = m[y0:y0 + max(3, int(hgt * 0.4))].sum(1)
            widths.append(float(np.mean(np.sort(rows)[-5:])))
        g = R.gray(f); hh, ww = g.shape; sx = ww / f.shape[1]
        mask = np.zeros_like(g)
        xr = int(((st[cv2.CC_STAT_LEFT] + st[cv2.CC_STAT_WIDTH]) * sx if st is not None else 0.5 * ww) + 0.04 * ww)
        mask[:int(hh * 0.85), min(ww - 8, xr):] = 255
        if prev is not None:
            ds = 0.0
            p0 = cv2.goodFeaturesToTrack(prev, 300, 0.01, 4, mask=prevmask)
            if p0 is not None and len(p0) >= 8:
                p1, stt, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None); ok = stt.ravel() == 1
                if ok.sum() >= 8:
                    Mx, _ = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
                    if Mx is not None:
                        ds = float(np.log(max(1e-3, np.hypot(Mx[0, 0], Mx[1, 0]))))
            bg.append(bg[-1] + ds)
        prev, prevmask = g, mask
    return widths, np.array(bg)


def main_night(takes):
    out = P / "metrics/h3_metrics_night.json"
    res = json.loads(out.read_text()) if out.exists() else {}
    takes = takes or [f"w{i}{a}" for a in "pw" for i in range(1, 9)]
    for t in takes:
        s = t[:2]
        fp, ft = R.frames(P / "previs" / s / "beauty_24fps.mp4"), R.frames(P / "h3" / "night" / f"{t}.mp4")
        n = min(len(fp), len(ft))
        gp, gt = R.global_path(fp[:n]), R.global_path(ft[:n])
        fol, amp = R.follow(gp, gt)
        ax = int(np.argmax([np.ptp(a) for a in gp]))
        tp, tt = progress_times(gp[ax]), progress_times(gt[ax])
        same_dir = bool(np.sign(gp[ax][-1] - gp[ax][0]) == np.sign(gt[ax][-1] - gt[ax][0]))
        per_axis = {k: (round(float(np.corrcoef(gp[i], gt[i])[0, 1]), 2) if np.ptp(gp[i]) >= 0.02 and np.ptp(gt[i]) > 1e-4 else None)
                    for i, k in enumerate(("pan_x", "pan_y", "log_zoom"))}
        r = dict(cam_follow=fol, cam_amp=amp, frames=len(ft), previs_frames=len(fp), n=n, words_only=t.endswith("w"),
                 follow_per_axis=per_axis, dominant_axis=("pan_x", "pan_y", "log_zoom")[ax], dominant_same_direction=same_dir,
                 previs_net=[round(float(a[-1] - a[0]), 3) for a in gp], take_net=[round(float(a[-1] - a[0]), 3) for a in gt],
                 previs_range=dict(pan_x=round(float(np.ptp(gp[0])), 3), pan_y=round(float(np.ptp(gp[1])), 3), log_zoom=round(float(np.ptp(gp[2])), 3)),
                 take_range=dict(pan_x=round(float(np.ptp(gt[0])), 3), pan_y=round(float(np.ptp(gt[1])), 3), log_zoom=round(float(np.ptp(gt[2])), 3)),
                 previs_t10_50_90=tp, take_t10_50_90=tt,
                 timing_offset_f=(None if (tp is None or tt is None or not same_dir) else [b - a for a, b in zip(tp, tt)]))
        if s == "w7":
            w, bg = her_and_bg(ft)
            w0 = next((x for x in w if x), None)
            valid = [x for x in w if x]
            r["her_shoulder_px_f0_f60_f123"] = [None if w[i] is None else round(w[i], 1) for i in (0, 60, len(w) - 1)]
            if w0 and w[-1]:
                r["her_scale_f0_f123"] = round(w[-1] / w0 - 1, 3)
                r["her_scale_minmax"] = [round(min(valid) / w0 - 1, 3), round(max(valid) / w0 - 1, 3)]
            r["bg_scale_f0_f60"] = round(math.exp(bg[60] - bg[0]) - 1, 3)
            r["bg_scale_f0_f123"] = round(math.exp(bg[-1] - bg[0]) - 1, 3)
            r["her_frames_missing"] = sum(1 for x in w if not x)
        res[t] = r
        print(t, json.dumps(r), flush=True)
        del fp, ft
        out.write_text(json.dumps(res, indent=1))


def main(takes):
    res = json.loads((P / "metrics/h3_metrics.json").read_text()) if (P / "metrics/h3_metrics.json").exists() else {}
    for t in takes:
        s = t[:2]
        fp, ft = R.frames(P / "previs" / s / "beauty_24fps.mp4"), R.frames(P / "h3" / f"{t}.mp4")
        gp, gt = R.global_path(fp[:N]), R.global_path(ft[:N])
        fol, amp = R.follow(gp, gt)
        r = dict(cam_follow=fol, cam_amp=amp, frames=len(ft), previs_frames=len(fp),
                 previs_range=dict(pan_x=round(float(np.ptp(gp[0])), 3), pan_y=round(float(np.ptp(gp[1])), 3), log_zoom=round(float(np.ptp(gp[2])), 3)),
                 take_range=dict(pan_x=round(float(np.ptp(gt[0])), 3), pan_y=round(float(np.ptp(gt[1])), 3), log_zoom=round(float(np.ptp(gt[2])), 3)))
        if s == "w7":
            for lab, fr in (("take", ft), ("previs", fp[:N])):
                hs, bs = region_scale(fr, (0.18, 0.48, 0.05, 1.0)), region_scale(fr, (0.55, 1.0, 0.0, 0.85))
                r[f"{lab}_her_scale_f0_f106"] = round(math.exp(hs[106] - hs[0]) - 1, 3)
                r[f"{lab}_bg_scale_f0_f106"] = round(math.exp(bs[106] - bs[0]) - 1, 3)
                if lab == "take":
                    r["take_her_scale_f0_f123"] = round(math.exp(hs[-1] - hs[0]) - 1, 3)
                    r["take_bg_scale_f0_f123"] = round(math.exp(bs[-1] - bs[0]) - 1, 3)
        res[t] = r
        print(t, json.dumps(r), flush=True)
    (P / "metrics/h3_metrics.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--night"]:
        main_night(sys.argv[2:])
    else:
        main(sys.argv[1:])
