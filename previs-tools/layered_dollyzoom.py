#!/usr/bin/env python3
"""EP08 8 worlds, shot 7 fallback: a layered (2.5D) dolly zoom built from still 8711 (video-director 2026-11-09, reviewer round 2 fix 3).
CPU only, one test. Near layer = her (GrabCut from a box) + the rock wall left of a line along its edge; both stay the same size (1.00 -> 0.98,
a true dolly zoom keeps the subject plane). Far layer = a clean plate (OpenCV Telea fill of the near layer, dilated) that swells 1.00 -> 1.45
around a far point right of her head. Timing = the previs keys (hold to 0.25 s, ease to 4.6 s), 124 frames at 24 fps, 1280x720.
Outputs: h3/w7_layered_test.mp4 (silent), review/w7_layered_strip.jpg, review/w7_layered_mask.jpg (mask over the still, for checking).
Usage (under tools/cpujob, vt.py venv): layered_dollyzoom.py [--line x_top,x_bottom] [--far px,py] [--swell 1.45]"""
import subprocess, sys
from pathlib import Path
import cv2
import numpy as np

P = Path(__file__).resolve().parent.parent   # repo root; expects previs/wN/beauty_24fps.mp4 and h3/night/<take>.mp4 (see README)
W, H, N, FPS = 1280, 720, 124, 24
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
XT, XB = (float(v) for v in args.get("--line", "0.40,0.50").split(","))
FX, FY = (float(v) for v in args.get("--far", "0.70,0.30").split(","))
SWELL = float(args.get("--swell", "1.45"))


def ease(u):
    u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def scaled(img, s, cx, cy):
    M = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)


def main():
    still = cv2.resize(cv2.imread(str(P / "stills/w7.png")), (W, H), interpolation=cv2.INTER_AREA)
    # her: GrabCut seeded with a box around her (still 8711: x ~0.25-0.54 W, y 0.04-1.0 H)
    m = np.zeros((H, W), np.uint8); bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(still, m, (int(0.25 * W), int(0.04 * H), int(0.29 * W), int(0.96 * H)), bg, fg, 6, cv2.GC_INIT_WITH_RECT)
    her = np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(her)
    if n > 1:
        her = np.where(lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])), 255, 0).astype(np.uint8)
    cv2.ellipse(her, (int(0.425 * W), int(0.15 * H)), (int(0.072 * W), int(0.095 * H)), 0, 0, 360, 255, -1)   # helmet (GrabCut lost its right half)
    her = cv2.dilate(her, np.ones((5, 5), np.uint8))                                                       # hair and rope edges
    # the wall: everything left of the line along its edge
    yy, xx = np.mgrid[0:H, 0:W]
    wall = np.where(xx < (XT + (XB - XT) * yy / (H - 1)) * W, 255, 0).astype(np.uint8)
    near = cv2.max(her, wall)
    near_f = cv2.GaussianBlur(near, (5, 5), 0).astype(np.float32) / 255.0
    plate = cv2.inpaint(still, cv2.dilate(near, np.ones((25, 25), np.uint8)), 9, cv2.INPAINT_TELEA)
    dbg = still.copy(); dbg[near > 0] = (0.5 * dbg[near > 0] + 0.5 * np.array([0, 0, 255])).astype(np.uint8)
    cv2.circle(dbg, (int(FX * W), int(FY * H)), 10, (255, 255, 0), 3)
    cv2.imwrite(str(P / "review/w7_layered_mask.jpg"), np.hstack([dbg, plate]), [cv2.IMWRITE_JPEG_QUALITY, 88])
    tmp = P / "h3/_w7_layered"; tmp.mkdir(exist_ok=True)
    cxn, cyn = 0.40 * W, 1.0 * H                      # near layer scales about her feet (keeps her standing on the ledge)
    for f in range(N):
        u = ease((f / FPS - 0.25) / (4.6 - 0.25))
        far = scaled(plate, 1.0 + (SWELL - 1.0) * u, FX * W, FY * H)
        s_n = 1.0 - 0.02 * u
        nl, nm = scaled(still, s_n, cxn, cyn), scaled(near_f, s_n, cxn, cyn)[..., None]
        out = (far.astype(np.float32) * (1 - nm) + nl.astype(np.float32) * nm).clip(0, 255).astype(np.uint8)
        cv2.imwrite(str(tmp / f"{f:04d}.png"), out)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "%04d.png"), "-c:v", "libx264", "-crf", "16",
                    "-pix_fmt", "yuv420p", str(P / "h3/w7_layered_test.mp4")], check=True)
    strip = np.hstack([cv2.resize(cv2.imread(str(tmp / f"{f:04d}.png")), (480, 270)) for f in (0, 40, 80, 123)])
    cv2.imwrite(str(P / "review/w7_layered_strip.jpg"), strip, [cv2.IMWRITE_JPEG_QUALITY, 88])
    for p in tmp.glob("*.png"):
        p.unlink()
    tmp.rmdir()
    print("her mask px", int((her > 0).sum()), "near px", int((near > 0).sum()), "->", P / "h3/w7_layered_test.mp4")


if __name__ == "__main__":
    main()
