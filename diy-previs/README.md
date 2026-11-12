# DIY previs: a camera move in Blender from one prompt

A single Blender Python script that builds a grey floor, a capsule and a few boxes, animates one camera move for 5 seconds (24 fps, 120 frames, 1280x720) and renders it to an MP4 with the Workbench engine. No add-ons, no external files.

**The script was written by an AI assistant (Claude) from the plain prompt in [`prompt.md`](prompt.md).** Nothing was edited by hand except one fix to make it safe to paste into a running Blender (it no longer resets the whole scene file).

## Run it

**Paste it into Blender (4.5)**

1. Open the *Scripting* tab, press *New*, paste the contents of `diy_previs.py`, press *Run Script*.
2. Press Space in the timeline to watch the camera move (look through the camera with Numpad 0).
3. *Render > Render Animation* (Ctrl+F12) writes the MP4 to your temp folder.

**From a terminal**

```
blender -b -P diy_previs.py
```

It prints where the MP4 was written (`diy_previs_<move>.mp4` in your temp folder).

## Pick the move

Change one line at the top:

```python
MOVE = "push_in"   # push_in, pull_out, orbit, pedestal, tilt, truck, crane, dolly_zoom
```

Each move is a few-line function that returns the camera position, the point it looks at and the focal length. The dolly zoom moves the camera in while the lens zooms out, so the capsule keeps its size and the background bends. Add your own by writing one more function.

`sheet/contact_sheet.png` shows the first, middle and last frame of all eight moves (rendered at 480x270 for the proof).

## Licence

MIT. Do what you like with it.
