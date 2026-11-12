"""Numbers for the video reviewer (the reviewer agent reads them with the contact sheet; they do not decide alone).

analyse({"previs": mp4, "h3": mp4, "wan": mp4}, n_used, sheet_path) ->
  window_start      first usable Wan frame (skips the darker opening frames), so the edit takes [start, start + n_used)
  dark_frames       how many opening frames are darker than 93 % of the shot's median brightness
  jump_ratio        biggest frame-to-frame change / median change inside the window (> 4 = visible jump or seam)
  speed_ratio       Wan motion / H3 motion (optical flow; 1.0 = Wan keeps H3's pace; we reject any retiming)
  cam_follow_h3/wan how well the camera path follows the previs: mean correlation of the global pan x, pan y and zoom
                    trajectories (1 = same path, 0 = unrelated, < 0 = opposite); None without previs
  cam_amp_h3/wan    size of the camera move relative to the previs (1 = as big, 0.5 = half)
Also writes the contact sheet (rows previs / H3 / Wan, 8 frames over the window) and 3 full-size Wan frames.
"""
from pathlib import Path

import cv2
import numpy as np


def frames(path, size=(180, 320)):
    cap, out = cv2.VideoCapture(str(path)), []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    cap.release()
    return out


def gray(f, size=None):
    """Grayscale analysis copy, ~57.6k px, keeping the source aspect ratio (180x320 for 9:16, 320x180 for 16:9)."""
    if size is None:
        h, w = f.shape[:2]; k = (57600 / (w * h)) ** 0.5; size = (max(8, round(w * k)), max(8, round(h * k)))
    return cv2.cvtColor(cv2.resize(f, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)


def global_path(fr):
    """Cumulative camera-like motion per frame: pan x, pan y (fraction of the frame) and log zoom."""
    tx, ty, sc = [0.0], [0.0], [0.0]
    prev = gray(fr[0])
    for f in fr[1:]:
        g = gray(f)
        p0 = cv2.goodFeaturesToTrack(prev, 300, 0.01, 6)
        dx = dy = ds = 0.0
        if p0 is not None and len(p0) >= 8:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None)
            ok = st.ravel() == 1
            if ok.sum() >= 8:
                M, _ = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
                if M is not None:
                    dx, dy = M[0, 2] / g.shape[1], M[1, 2] / g.shape[0]
                    ds = float(np.log(max(1e-3, np.hypot(M[0, 0], M[1, 0]))))
        tx.append(tx[-1] + dx); ty.append(ty[-1] + dy); sc.append(sc[-1] + ds)
        prev = g
    return np.array([tx, ty, sc])


def follow(ref, got):
    n = min(ref.shape[1], got.shape[1])
    ref, got = ref[:, :n], got[:, :n]
    cors, amps = [], []
    for a, b in zip(ref, got):
        ra, rb = np.ptp(a), np.ptp(b)
        if ra < 0.02:            # the previs barely moves on this axis: nothing to follow
            continue
        cors.append(float(np.corrcoef(a, b)[0, 1]) if rb > 1e-4 else 0.0)
        amps.append(rb / ra)
    if not cors:
        return None, None
    return round(float(np.mean(cors)), 2), round(float(np.median(amps)), 2)


def motion(fr):
    m, prev = [], gray(fr[0])
    for f in fr[1:]:
        g = gray(f)
        flow = cv2.calcOpticalFlowFarneback(prev, g, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        m.append(float(np.linalg.norm(flow, axis=2).mean())); prev = g
    return np.array(m)


def analyse(src, n_used, sheet_path: Path):
    F = {k: frames(v) for k, v in src.items() if Path(v).exists()}
    W = F["wan"]
    luma = np.array([gray(f).mean() for f in W])
    ref = np.median(luma[6:40]) if len(luma) > 40 else np.median(luma)
    dark = int(np.argmax(luma >= 0.93 * ref)) if (luma >= 0.93 * ref).any() else 0
    start = int(min(max(dark, 2), max(0, len(W) - n_used)))
    win = W[start:start + n_used]
    d = np.array([np.abs(gray(a).astype(float) - gray(b).astype(float)).mean() for a, b in zip(win, win[1:])])
    out = {"frames": len(W), "window_start": start, "dark_frames": dark,
           "jump_ratio": round(float(d.max() / max(np.median(d), 1e-3)), 1) if len(d) else None}
    if "h3" in F:
        mw, mh = motion(W[start:start + n_used]), motion(F["h3"][start:start + n_used])
        out["speed_ratio"] = round(float(mw.mean() / max(mh.mean(), 1e-3)), 2)
    if "previs" in F:
        pp = global_path(F["previs"])
        for k in ("h3", "wan"):
            if k in F:
                out[f"cam_follow_{k}"], out[f"cam_amp_{k}"] = follow(pp, global_path(F[k]))
    # contact sheet: one row per source, 8 frames spread over the edit window
    idx = np.linspace(start, start + n_used - 1, 8).astype(int)
    fh_, fw_ = W[0].shape[:2]
    # tiles keep the source aspect ratio: 135x240 for 9:16 (as before), 240x135 for 16:9
    tw, th = (135, 240) if fh_ >= fw_ else (240, 135)
    tw, th = tw, round(tw * fh_ / fw_)
    rows = [k for k in ("previs", "h3", "wan") if k in F]
    sheet = np.full((len(rows) * (th + 22), 8 * tw, 3), 17, np.uint8)
    for r, k in enumerate(rows):
        for c, i in enumerate(idx):
            i = min(i, len(F[k]) - 1)
            sheet[r * (th + 22) + 22:r * (th + 22) + 22 + th, c * tw:(c + 1) * tw] = cv2.resize(F[k][i], (tw, th), interpolation=cv2.INTER_AREA)
            cv2.putText(sheet, f"{k} {i}", (c * tw + 4, r * (th + 22) + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
    cv2.imwrite(str(sheet_path), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    for j, i in enumerate((idx[0], idx[4], idx[-1])):
        cv2.imwrite(str(sheet_path.with_name(sheet_path.stem.replace("_sheet", "") + f"_f{j}.jpg")), W[min(i, len(W) - 1)],
                    [cv2.IMWRITE_JPEG_QUALITY, 90])
    return out
