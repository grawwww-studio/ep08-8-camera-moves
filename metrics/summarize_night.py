#!/usr/bin/env python3
"""EP08 8 worlds: apply the pre-registered night criteria (review/h3_metrics_night.json "_criteria", written 01:53:27Z before any number)
to the measured takes. Adds per take "followed", per move "_summary" {winner, gap, line} and "_counts" {n_previs, n_words, amp median}.
w7: "followed" comes from "_w7_rule" {pass: bool, ...} (helmet width and shared-feature swell measured on full frames), never from the path.
Retries (w*r) are summarised apart and never enter n_previs. CPU, tiny. usage: summarize_night.py"""
import json, statistics
from pathlib import Path

P = Path(__file__).resolve().parent.parent   # repo root; expects previs/wN/beauty_24fps.mp4 and h3/night/<take>.mp4 (see README)
F = P / "metrics/h3_metrics_night.json"
TIE, FOLLOW = 0.10, 0.70
NAMES = {1: "push-in", 2: "tilt", 3: "orbit", 4: "pull-out", 5: "truck", 6: "pedestal", 7: "dolly zoom", 8: "crane-up"}


def followed(t, m, M):
    if t.startswith("w7"):
        r = M.get("_w7_rule", {}).get(t)
        return bool(r and r.get("pass"))
    return bool(m.get("cam_follow") is not None and m["cam_follow"] >= FOLLOW and m.get("dominant_same_direction"))


def main():
    M = json.loads(F.read_text())
    for t, m in M.items():
        if not t.startswith("_"):
            m["followed"] = followed(t, m, M)
            ax = m["dominant_axis"]   # secondary measure, added 02:10Z after the first look (cam_amp is a median over axes and hides a tilt's size)
            m["dominant_axis_amp"] = round(m["take_range"][ax] / m["previs_range"][ax], 2) if m["previs_range"][ax] else None
    summ, npv, nw, amps = {}, 0, 0, []
    for n in range(1, 9):
        s = f"w{n}"; p, w = M.get(f"{s}p"), M.get(f"{s}w")
        if not (p and w):
            continue
        npv += p["followed"]; nw += w["followed"]
        if p.get("cam_amp") is not None:
            amps.append(p["cam_amp"])
        if n == 7:
            win = "previs" if p["followed"] and not w["followed"] else "words" if w["followed"] and not p["followed"] else ("tie" if p["followed"] else "neither")
            gap = None
        elif not p["followed"] and not w["followed"]:
            win, gap = "neither", round((p["cam_follow"] or 0) - (w["cam_follow"] or 0), 2)
        else:
            gap = round((p["cam_follow"] or 0) - (w["cam_follow"] or 0), 2)
            win = "tie" if abs(gap) < TIE else ("previs" if gap > 0 else "words")
        line = {"previs": "The previs take follows the planned path more closely.", "words": "Words alone followed the path more closely than the previs.",
                "tie": "Words and previs follow the path about equally (gap under 0.10).", "neither": "Neither take follows the planned path."}[win]
        summ[s] = dict(move=NAMES[n], winner=win, gap=gap, previs_followed=p["followed"], words_followed=w["followed"], line=line)
    M["_summary"] = summ
    M["_counts"] = dict(n_previs=npv, n_words=nw, of=len(summ), amp_production=amps, amp_median=(round(statistics.median(amps), 2) if amps else None),
                        dominant_axis_amp_production=[M[f"w{n}p"]["dominant_axis_amp"] for n in range(1, 9) if f"w{n}p" in M],
                        dominant_axis_amp_median_followed=round(statistics.median([M[f"w{n}p"]["dominant_axis_amp"] for n in range(1, 9) if M.get(f"w{n}p", {}).get("followed")]), 2),
                        note_secondary="dominant_axis_amp (take range / previs range on the previs's biggest axis) was added at 02:10Z after the first look; cam_amp stays the pre-registered measure",
                        rule=f"followed = cam_follow >= {FOLLOW} and the dominant axis in the previs direction; w7 by its written rule; tie = gap < {TIE}")
    F.write_text(json.dumps(M, indent=1))
    print(json.dumps(M["_counts"]), "\n" + "\n".join(f"{k}: {v}" for k, v in summ.items()))


if __name__ == "__main__":
    main()
