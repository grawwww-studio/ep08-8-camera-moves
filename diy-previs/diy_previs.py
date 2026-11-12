"""diy_previs.py - a basic previs in Blender: grey floor, a capsule, one camera move.

Written by an AI assistant (Claude) from the prompt in prompt.md.
Blender 4.5, no add-ons, no external files.

Run it either way:
  * In Blender: open the Scripting tab, New, paste this, press Run Script.
    Then press Space in the timeline to watch the camera move.
    (Render > Render Animation, or Ctrl+F12, writes the MP4.)
  * From a terminal: blender -b -P diy_previs.py   (renders the MP4 for you)
"""
import bpy, math, os, tempfile

# ----------------------------------------------------------------- settings
MOVE = "push_in"   # push_in, pull_out, orbit, pedestal, tilt, truck, crane, dolly_zoom
SECONDS, FPS = 5, 24
WIDTH, HEIGHT = 1280, 720
OUT = os.path.join(tempfile.gettempdir(), "diy_previs_" + MOVE + ".mp4")
RENDER = bpy.app.background   # render by itself only when run headless

# ----------------------------------------------------------------- the moves
# Each move answers: where is the camera (x, y, z), where does it look, and
# what focal length, at time u (0 = first frame, 1 = last frame)?
def lerp(a, b, u): return a + (b - a) * u
HEAD = (0, 0, 1.2)  # the point we usually look at: the capsule's chest

def push_in(u):    return (0, -lerp(6, 2, u), 1.4), HEAD, 35
def pull_out(u):   return (0, -lerp(2, 6, u), 1.4), HEAD, 35
def orbit(u):
    a = math.radians(lerp(-90, 30, u))                  # 120 degrees around the capsule
    return (5 * math.cos(a), 5 * math.sin(a), 1.6), HEAD, 35
def pedestal(u):   # camera rises straight up, still looking straight ahead
    z = lerp(0.4, 3.0, u); return (0, -5, z), (0, 0, z), 35
def tilt(u):       # camera stays put and only rotates up, feet to above the head
    return (0, -5, 1.0), (0, 0, lerp(0.1, 2.4, u)), 35
def truck(u):      # camera slides sideways, still looking straight ahead
    x = lerp(-3, 3, u); return (x, -5, 1.4), (x, 0, 1.2), 35
def crane(u):      # up and back in an arc, always looking at the capsule
    return (0, -lerp(3, 6, u), lerp(0.6, 4.5, u)), HEAD, 35
def dolly_zoom(u): # move in while zooming out: the capsule keeps its size, the world bends
    d = lerp(8, 3, u); return (0, -d, 1.2), HEAD, 18 * d / 3   # 48 mm far away, 18 mm close

# ----------------------------------------------------------------- the scene
scene = bpy.context.scene
for ob in list(bpy.data.objects):                       # empty the scene (so you can run it again and again)
    bpy.data.objects.remove(ob)

def grey(name, value):                                  # a flat grey material
    m = bpy.data.materials.new(name); m.diffuse_color = (value, value, value, 1); return m

# floor
bpy.ops.mesh.primitive_plane_add(size=60)
bpy.context.object.data.materials.append(grey("floor", 0.6))

# capsule = cylinder + two spheres (1.8 m tall, 0.6 m wide)
parts = []
bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=1.2, location=(0, 0, 0.9)); parts.append(bpy.context.object)
for z in (0.3, 1.5):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(0, 0, z)); parts.append(bpy.context.object)
bpy.ops.object.select_all(action="DESELECT")
for p in parts: p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
bpy.ops.object.shade_smooth()
bpy.context.object.name = "Capsule"
bpy.context.object.data.materials.append(grey("capsule", 0.9))

# a few boxes in the background, so you can SEE the camera move (and the dolly zoom)
for x, y, h in [(-3, 4, 2), (-1, 6, 3), (2, 5, 1.5), (4, 8, 4), (-5, 9, 2.5)]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2)); box = bpy.context.object
    box.scale = (1, 1, h); box.data.materials.append(grey("box", 0.65))

# camera + a "target" empty it always looks at
cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data); scene.collection.objects.link(cam)
target = bpy.data.objects.new("Target", None); scene.collection.objects.link(target)
look = cam.constraints.new("TRACK_TO")                  # camera's -Z looks at the target, Y is up
look.target, look.track_axis, look.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
scene.camera = cam

# ----------------------------------------------------------------- animate
move = globals()[MOVE]
scene.render.fps = FPS
scene.frame_start, scene.frame_end = 1, SECONDS * FPS   # 120 frames
for f in range(scene.frame_start, scene.frame_end + 1):
    u = (f - 1) / (scene.frame_end - 1)
    u = u * u * (3 - 2 * u)                             # ease in and out
    cam.location, target.location, cam_data.lens = move(u)
    cam.keyframe_insert("location", frame=f)
    target.keyframe_insert("location", frame=f)
    cam_data.keyframe_insert("lens", frame=f)
scene.frame_set(1)

# ----------------------------------------------------------------- render settings
scene.render.engine = "BLENDER_WORKBENCH"               # fast, flat, no ray tracing
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.view_settings.view_transform = "Standard"
scene.world = bpy.data.worlds.new("World"); scene.world.color = (0.75, 0.78, 0.82)
scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.filepath = OUT

if RENDER:
    bpy.ops.render.render(animation=True)
    print("Wrote", OUT)
else:
    print("Scene ready. Press Space in the timeline to play; Ctrl+F12 renders to", OUT)
