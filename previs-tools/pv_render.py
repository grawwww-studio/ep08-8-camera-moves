"""Parametric previs for the video team (Blender 4.5, headless, sandboxed container). One script for every shot: a set,
a subject and a camera move, all read from /work/params.json (written by tools/video/vt.py from the shot list).
Generalises hanger5 / calle5 / rooftop5 (v8 ad); with their parameters it reproduces them (presets in templates.json).

params.json
  frames, fps, w, h, samples
  set:      studio_dark | street | rooftop | boxes | stage  (+ seed; `stage` = ground, blocks and building rows from set_params, see set_stage)
  subject:  hanger_hoodie | proxy | walker | sitter | rig | none   (+ subject_params; for people use proxy, see BOOK.md; `rig` = a generic object from animatic.yaml, see subject_rig)
  camera:   cylindrical coordinates around the subject's anchor: d (m), a_deg (+ = towards the subject's left /
            screen right), z (m), lens (mm, vertical 36 mm sensor), tx, tz (look-at offset from the anchor, m).
            Either keys=[{t, d, a_deg, z, lens, tx, tz}, ...] (eased between keys; omitted fields carry over) or the
            start -> end form {d: [a, b], ...} eased over ease=[t0, t1]. Optional handheld (sway amplitude, m).
  depth:    near, far (m) for the normalised Z pass (near = white)
Outputs in $PREVIS_OUT (default /work/out/): beauty_####.png, depth_####.png. Env PREVIS_ONE=1 renders frame 1 only;
PREVIS_START=n resumes.
"""
import json, math, os, random
import bpy
from mathutils import Vector, Euler, Quaternion

P = json.load(open(os.environ.get("PREVIS_PARAMS", "/work/params.json")))
FPS, N, W, H = P.get("fps", 24), P.get("frames", 121), P.get("w", 720), P.get("h", 1280)
SAMPLES = P.get("samples", 8)
T0 = P.get("time_offset", 0.0)   # spot clock: every channel evaluates at t = T0 + (frame - 1) / fps
# look: clay (flat grey, the default and the only look of the v8 sets) | lookdev (real materials); env wins over params
LOOK = os.environ.get("PREVIS_LOOK") or (P.get("subject_params") or {}).get("look") or P.get("look") or "clay"
if os.environ.get("PREVIS_STILL"):   # lookdev still: size and samples from params.lookdev_still
    _ls = P.get("lookdev_still", {}); W, H, SAMPLES = _ls.get("w", W), _ls.get("h", H), _ls.get("samples", 512)
OUT = os.environ.get("PREVIS_OUT", "/work/out/")
random.seed(P.get("seed", 7))
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
sc = bpy.context.scene
sc.render.fps, sc.frame_start, sc.frame_end = FPS, 1, N
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100


def mat(name, rgb, rough=0.8):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    return m


CLAY, BODY, DARK = mat("clay", (0.55, 0.55, 0.55)), mat("body", (0.85, 0.72, 0.62), 0.6), mat("dark", (0.25, 0.25, 0.27))
WHITE, METAL = mat("white", (0.9, 0.9, 0.9)), mat("metal", (0.2, 0.2, 0.2), 0.4)


def box(loc, size, m=CLAY, name="box"):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object; o.name = name; o.scale = (size[0] / 2, size[1] / 2, size[2] / 2); o.data.materials.append(m)
    return o


def smooth(a, b, t):
    x = min(1, max(0, (t - a) / (b - a)))
    return x * x * (3 - 2 * x)


def world(rgb, strength):
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*rgb, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = strength
    return w


def sun(rot_deg, energy=3.0):
    bpy.ops.object.light_add(type="SUN", rotation=tuple(math.radians(r) for r in rot_deg))
    bpy.context.object.data.energy = energy


# ---------------------------------------------------------------- sets
def set_street():
    box((0, 30, -0.05), (60, 140, 0.1), name="ground")
    box((0, 30, 0.02), (6, 140, 0.04), DARK, "road")
    for k in range(-2, 9):
        box((0, k * 0.9, 0.045), (6, 0.5, 0.01), WHITE, "zebra")
    for side in (-1, 1):
        y = -15
        while y < 90:
            d, h = random.uniform(6, 14), random.uniform(7, 18)
            box((side * random.uniform(8.5, 9.5), y + d / 2, h / 2), (5, d - 0.3, h), CLAY, "building")
            y += d
        for y in range(-10, 90, 12):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=4, location=(side * 6.2, y, 2))
            bpy.context.object.data.materials.append(DARK)
        for y in range(-6, 90, 17):
            box((side * 5.0, y + random.uniform(-2, 2), 0.7), (1.8, 4.2, 1.4), DARK, "car")
    sun((50, 0, 35)); world((0.75, 0.82, 0.95), 0.8)


def set_rooftop():
    box((0, -3, -0.05), (14, 10, 0.1), name="terrace floor")
    box((0, 0.25, 0.27), (9, 0.5, 0.55), name="wall")
    for _ in range(220):
        x, y, h = random.uniform(-90, 90), random.uniform(15, 260), random.uniform(4, 22)
        box((x, y, -18 + h / 2), (random.uniform(6, 16), random.uniform(6, 16), h), CLAY, "city")
    sun((80, 0, 200)); world((0.95, 0.75, 0.55), 0.9)


def set_studio_dark():
    world((0.02, 0.02, 0.02), 1.0)
    for loc, e in (((2, -3, 3), 500), ((-3, -1, 2), 250), ((0, 3, 3), 400)):
        bpy.ops.object.light_add(type="AREA", location=loc); L = bpy.context.object; L.data.energy, L.data.size = e, 3
        L.rotation_euler = (Vector((0, 0, 0.2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 1.6, 0.5), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(mat("back", (0.02, 0.02, 0.02)))


def set_boxes():
    box((0, 0, -0.05), (30, 30, 0.1), name="floor")
    box((0, 6, 3), (30, 0.2, 6), name="backdrop")
    sun((55, 0, 30)); world((0.6, 0.6, 0.6), 0.8)


# ---------------------------------------------------------------- subjects (each returns anchor(t) -> Vector)
J = {}


def joint(name, parent, loc):
    e = bpy.data.objects.new(name, None); sc.collection.objects.link(e)
    if parent:
        e.parent = J[parent]
    e.location = loc; e.rotation_mode = "XYZ"; J[name] = e
    return e


def limb(j, length, r, up=False):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, location=(0, 0, 0))
    o = bpy.context.object; o.data.materials.append(BODY)
    o.parent = J[j]; o.location = (0, 0, length / 2 if up else -length / 2)
    return o


def mannequin():
    joint("root", None, (0, 0, 0))
    joint("pelvis", "root", (0, 0, 0.95)); limb("pelvis", 0.18, 0.13, up=True)
    joint("chest", "pelvis", (0, 0, 0.2)); limb("chest", 0.3, 0.14, up=True)
    joint("neck", "chest", (0, 0, 0.32)); limb("neck", 0.1, 0.045, up=True)
    joint("head", "neck", (0, 0, 0.1))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.11, location=(0, 0, 0.11)); h = bpy.context.object
    h.scale = (0.9, 1.0, 1.15); h.data.materials.append(BODY); h.parent = J["head"]; h.location = (0, 0, 0.11)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(0, 0, 0)); n = bpy.context.object  # nose marks the face
    n.data.materials.append(DARK); n.parent = J["head"]; n.location = (0, 0.1, 0.1)
    for s, side in ((1, "R"), (-1, "L")):  # facing +Y, her right is +X
        joint(f"shoulder{side}", "chest", (s * 0.19, 0, 0.27)); limb(f"shoulder{side}", 0.28, 0.045)
        joint(f"elbow{side}", f"shoulder{side}", (0, 0, -0.28)); limb(f"elbow{side}", 0.25, 0.038)
        joint(f"wrist{side}", f"elbow{side}", (0, 0, -0.25))
        joint(f"hip{side}", "pelvis", (s * 0.09, 0, 0)); limb(f"hip{side}", 0.44, 0.07)
        joint(f"knee{side}", f"hip{side}", (0, 0, -0.44)); limb(f"knee{side}", 0.43, 0.055)
        joint(f"ankle{side}", f"knee{side}", (0, 0, -0.43))
        box((0, 0.06, -0.03), (0.09, 0.22, 0.06), BODY, f"foot{side}").parent = J[f"ankle{side}"]
        bpy.data.objects[f"foot{side}"].location = (0, 0.06, -0.03)


def key_pose(rots, f):
    for k, v in rots.items():
        J[k].rotation_euler = v; J[k].keyframe_insert("rotation_euler", frame=f)


def subject_walker(sp):
    """Walks towards the camera (-Y) at speed m/s; hands in the hoodie pocket (or swinging); optional glance
    [t_in0, t_in1, t_out0, t_out1] with head yaw glance_deg (+ = her left)."""
    mannequin()
    v, stride = sp.get("speed", 1.1), sp.get("stride", 1.35)
    g = sp.get("glance", [1.2, 1.8, 2.4, 3.1]); gdeg = sp.get("glance_deg", 30)
    pocket = sp.get("hands", "pocket") == "pocket"
    for f in range(1, N + 1):
        t = (f - 1) / FPS + T0
        phi = 2 * math.pi * (v * t / stride); A = math.radians(22)
        r = {"root": (0, 0, math.radians(180))}
        r["hipL"] = (A * math.sin(phi), 0, 0); r["hipR"] = (-A * math.sin(phi), 0, 0)
        r["kneeL"] = (-math.radians(5) - math.radians(35) * max(0, math.sin(phi - 1.3)), 0, 0)
        r["kneeR"] = (-math.radians(5) - math.radians(35) * max(0, math.sin(phi + math.pi - 1.3)), 0, 0)
        if pocket:
            r["shoulderL"] = (math.radians(-12), 0, math.radians(-6)); r["shoulderR"] = (math.radians(-12), 0, math.radians(6))
            r["elbowL"] = (math.radians(75), 0, math.radians(-30)); r["elbowR"] = (math.radians(75), 0, math.radians(30))
        else:
            r["shoulderL"] = (-A * 0.8 * math.sin(phi), 0, math.radians(-4)); r["shoulderR"] = (A * 0.8 * math.sin(phi), 0, math.radians(4))
            r["elbowL"] = (math.radians(15), 0, 0); r["elbowR"] = (math.radians(15), 0, 0)
        glance = (smooth(g[0], g[1], t) - smooth(g[2], g[3], t)) if g else 0
        r["pelvis"] = (0, math.radians(2) * math.sin(phi), 0)
        r["chest"] = (0, 0, math.radians(gdeg * 8 / 30) * glance)
        r["neck"] = (0, 0, math.radians(gdeg * 18 / 30) * glance)
        r["head"] = (math.radians(-4), 0, math.radians(gdeg) * glance)
        bob = 0.02 * (math.cos(2 * phi) - 1)
        J["root"].location = (0, -v * t, bob); J["root"].keyframe_insert("location", frame=f)
        key_pose(r, f)
    return lambda t: Vector((0, -v * t, 0))


def subject_sitter(sp):
    """Seated on a 0.55 m wall facing the camera, right knee up. Optional hood pull [t0, t1, t2, t3] and a head turn
    look=[t0, t1] by look_deg (- = her right). knee_out_deg (default 6): sideways swing of the raised right knee
    (frame left); negative = knee further out to frame left (hoodie15-team s3 uses -25); knee_flex_deg (default 125) = thigh lift, higher
    = knee closer to the chest (s3 uses 140)."""
    mannequin()
    hp = sp.get("hood", [0.6, 1.6, 2.2, 2.9]); lk = sp.get("look", [2.4, 4.0]); ldeg = sp.get("look_deg", -40)
    y0 = sp.get("y", 0.1); kout = sp.get("knee_out_deg", 6); kflex = sp.get("knee_flex_deg", 125)
    J["root"].location = (0, y0, 0.55 - 0.95)
    for f in range(1, N + 1):
        t = (f - 1) / FPS + T0
        r = {"root": (0, 0, math.radians(180))}
        r["hipL"] = (math.radians(85), 0, math.radians(-8)); r["kneeL"] = (math.radians(-80), 0, 0)
        r["hipR"] = (math.radians(kflex), 0, math.radians(kout)); r["kneeR"] = (math.radians(-140), 0, 0)
        up = smooth(hp[0], hp[1], t) * (1 - smooth(hp[2], hp[3], t)) if hp else 0
        rest_l, rest_r = (math.radians(35), 0, math.radians(-12)), (math.radians(55), 0, math.radians(14))
        r["shoulderL"] = tuple(a + (b - a) * up for a, b in zip(rest_l, (math.radians(155), 0, math.radians(-25))))
        r["shoulderR"] = tuple(a + (b - a) * up for a, b in zip(rest_r, (math.radians(155), 0, math.radians(25))))
        r["elbowL"] = (math.radians(20 + 90 * up), 0, 0); r["elbowR"] = (math.radians(20 + 90 * up), 0, 0)
        look = smooth(lk[0], lk[1], t) if lk else 0
        r["pelvis"] = (math.radians(-6), 0, 0)
        r["chest"] = (math.radians(-4), 0, math.radians(ldeg * 12 / 40) * look)
        r["neck"] = (0, 0, math.radians(ldeg * 25 / 40) * look)
        r["head"] = (math.radians(-3), 0, math.radians(ldeg) * look)
        key_pose(r, f)
    return lambda t: Vector((0, y0, 0))


def subject_hanger_hoodie(sp):
    """Clay hoodie with thickness on a hanger. Turns to turn_deg by t1, then back by back_deg by t2."""
    bpy.ops.object.empty_add(location=(0, 0, 0.98)); piv = bpy.context.object

    def part(op, name, m=CLAY, bevel=0.0, **kw):
        op(**kw); o = bpy.context.object; o.name = name; o.data.materials.append(m)
        if bevel:
            b = o.modifiers.new("bev", "BEVEL"); b.width, b.segments = bevel, 4
        o.modifiers.new("sub", "SUBSURF").levels = 2
        bpy.ops.object.shade_smooth(); o.parent = piv; o.matrix_parent_inverse = piv.matrix_world.inverted(); return o

    part(bpy.ops.mesh.primitive_cube_add, "body", bevel=0.08, size=1, location=(0, 0, 0.40)).scale = (0.60, 0.17, 0.80)
    part(bpy.ops.mesh.primitive_uv_sphere_add, "hood", radius=0.17, location=(0, 0.06, 0.82)).scale = (1.0, 0.7, 0.55)
    part(bpy.ops.mesh.primitive_cube_add, "pocket", bevel=0.03, size=1, location=(0, -0.09, 0.16)).scale = (0.36, 0.03, 0.17)
    for s in (1, -1):
        sl = part(bpy.ops.mesh.primitive_cylinder_add, f"sleeve{s}", radius=0.08, depth=0.76, location=(s * 0.355, 0.0, 0.40))
        sl.rotation_euler = Euler((0, math.radians(-s * 4), 0)); sl.scale = (1.0, 0.85, 1.0)
        part(bpy.ops.mesh.primitive_cylinder_add, f"cuff{s}", radius=0.066, depth=0.07, location=(s * 0.38, 0.0, 0.03))
        part(bpy.ops.mesh.primitive_cylinder_add, f"draw{s}", radius=0.007, depth=0.22, location=(s * 0.05, -0.105, 0.62))
    part(bpy.ops.mesh.primitive_torus_add, "hook", m=METAL, major_radius=0.05, minor_radius=0.008,
         location=(0, 0, 0.93)).rotation_euler = Euler((math.radians(90), 0, 0))
    part(bpy.ops.mesh.primitive_cylinder_add, "bar", m=METAL, radius=0.012, depth=0.5,
         location=(0, 0, 0.79)).rotation_euler = Euler((0, math.radians(90), 0))
    if sp.get("rail", True):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=1.6, location=(-0.62, 0, 1.06)); rail = bpy.context.object
        rail.rotation_euler = Euler((0, math.radians(90), 0)); rail.data.materials.append(METAL)
    tt = sp.get("times", [0.2, 2.5, 4.8]); turn, back = sp.get("turn_deg", 70), sp.get("back_deg", 60)
    for f in range(1, N + 1):
        t = (f - 1) / FPS + T0
        ang = math.radians(turn) * smooth(tt[0], tt[1], t) - math.radians(back) * smooth(tt[1], tt[2], t)
        piv.rotation_euler = Euler((math.radians(2.0) * math.sin(t * 2.4), 0, ang)); piv.keyframe_insert("rotation_euler", frame=f)
    return lambda t: Vector((0, 0, 0))


# ====================================================================== can22-slime additions (2026-10-18)
# set slime_pool, subject can3 (3-part castellated can), subject slime_drip, metaball slime (puddle-coloured and
# slime-coloured families), per-part slime coat, puddle ripples, look clay|lookdev. Nothing above this block depends on it:
# the v8 sets and subjects do not touch any of these names.
import numpy as np

SLIME_SOURCES = []       # f(t) -> (puddle_family_items, slime_family_items); item = (x, y, z, visible_radius[, (sx, sy, sz)])
FRAME_HOOKS = []         # f(t): per-frame updaters (puddle mesh, coat shells)
G_ACC = 9.81


def hexlin(h):
    h = h.lstrip("#"); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def sm01(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


class Curve:
    """Monotone cubic (Fritsch-Carlson) through keys {t, <ch>, hold?, ease?}: continuous velocity, `hold: true` = zero
    velocity at that key; `ease: gravity` on a key makes the segment arriving at it an ease-in (v = v0 + dv * u^2)."""

    def __init__(self, keys, ch, default=0.0):
        ks = sorted(keys, key=lambda k: k["t"]); self.t, self.v, self.g = [], [], []
        last = default; hold = []
        for k in ks:
            last = k.get(ch, last); self.t.append(float(k["t"])); self.v.append(float(last))
            hold.append(bool(k.get("hold"))); self.g.append(k.get("ease") == "gravity")
        n = len(ks); t, v = self.t, self.v
        d = [(v[i + 1] - v[i]) / max(t[i + 1] - t[i], 1e-9) for i in range(n - 1)]
        m = [0.0] * n
        for i in range(n):
            if hold[i] or n == 1:
                m[i] = 0.0
            elif i == 0:
                m[i] = d[0]
            elif i == n - 1:
                m[i] = d[-1]
            elif d[i - 1] * d[i] <= 0:
                m[i] = 0.0
            else:
                h0, h1 = t[i] - t[i - 1], t[i + 1] - t[i]; w1, w2 = 2 * h1 + h0, h1 + 2 * h0
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        self.m = m

    def __call__(self, x):
        t, v, m = self.t, self.v, self.m
        if x <= t[0]:
            return v[0]
        if x >= t[-1]:
            return v[-1]
        for i in range(len(t) - 1):
            if x <= t[i + 1]:
                h = t[i + 1] - t[i]; u = (x - t[i]) / h
                if self.g[i + 1]:
                    return v[i] + (v[i + 1] - v[i]) * u * u
                h00, h10, h01, h11 = 2 * u**3 - 3 * u**2 + 1, u**3 - 2 * u**2 + u, -2 * u**3 + 3 * u**2, u**3 - u**2
                return h00 * v[i] + h10 * h * m[i] + h01 * v[i + 1] + h11 * h * m[i + 1]
        return v[-1]


# ---------------------------------------------------------------- materials
SP = P.get("set_params", {}) if P.get("set") == "slime_pool" else {}
COL = {"puddle": "#12A9E6", "marble": "#FFD400", "slime": "#FF2D92", "ground": "#0E0E0E", **SP.get("colours", {})}
LOOKDEV = LOOK == "lookdev"
CLAYKEY = LOOK == "clay_key"   # animatic look: clay world, labelled cans, flat-tinted fruit, pale blue-grey water


def _principled(m):
    return m.node_tree.nodes["Principled BSDF"]


def _wet_shader(m, col, glow, marble=None, gain=1.0):
    """Glossy, translucent, glowing slime on a Principled BSDF; optional world-space marbling (cyan with yellow veins)."""
    m.use_nodes = True; nt = m.node_tree; b = _principled(m); N = nt.nodes
    b.inputs["Roughness"].default_value = 0.16
    b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Coat Roughness"].default_value = 0.10
    b.inputs["Subsurface Weight"].default_value = 0.55; b.inputs["Subsurface Scale"].default_value = 0.006
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.45)
    b.inputs["Specular IOR Level"].default_value = 0.6
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    ramp = N.new("ShaderNodeMath"); ramp.operation = "MULTIPLY_ADD"
    ramp.inputs[1].default_value = glow * 1.6; ramp.inputs[2].default_value = glow * 0.55
    nt.links.new(lw.outputs["Fresnel"], ramp.inputs[0]); nt.links.new(ramp.outputs[0], b.inputs["Emission Strength"])
    if marble is None:
        b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Emission Color"].default_value = (*col, 1)
    else:
        pos = N.new("ShaderNodeNewGeometry"); n1 = N.new("ShaderNodeTexNoise")
        n1.inputs["Scale"].default_value = 11; n1.inputs["Detail"].default_value = 5; n1.inputs["Distortion"].default_value = 1.1
        nt.links.new(pos.outputs["Position"], n1.inputs["Vector"])
        sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 0.5
        ab = N.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
        mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 0.05
        mr.inputs["To Min"].default_value = 1.0; mr.inputs["To Max"].default_value = 0.0; mr.clamp = True
        n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 3.2; n2.inputs["Detail"].default_value = 3
        nt.links.new(pos.outputs["Position"], n2.inputs["Vector"])
        mr2 = N.new("ShaderNodeMapRange"); mr2.inputs["From Min"].default_value = 0.64; mr2.inputs["From Max"].default_value = 0.72
        mx = N.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; mx.use_clamp = True
        nt.links.new(n1.outputs["Fac"], sub.inputs[0]); nt.links.new(sub.outputs[0], ab.inputs[0])
        nt.links.new(ab.outputs[0], mr.inputs["Value"]); nt.links.new(n2.outputs["Fac"], mr2.inputs["Value"])
        nt.links.new(mr.outputs[0], mx.inputs[0]); nt.links.new(mr2.outputs[0], mx.inputs[1])
        mixc = N.new("ShaderNodeMix"); mixc.data_type = "RGBA"
        mixc.inputs["A"].default_value = (*[c_ * gain for c_ in col], 1); mixc.inputs["B"].default_value = (*[c_ * gain for c_ in marble], 1)
        nt.links.new(mx.outputs[0], mixc.inputs["Factor"])
        at_ = N.new("ShaderNodeAttribute"); at_.attribute_name = "stain"; at_.attribute_type = "GEOMETRY"
        sc_ = N.new("ShaderNodeMath"); sc_.operation = "MULTIPLY"; sc_.inputs[1].default_value = 0.92
        nt.links.new(at_.outputs["Fac"], sc_.inputs[0])
        mst = N.new("ShaderNodeMix"); mst.data_type = "RGBA"
        nt.links.new(mixc.outputs["Result"], mst.inputs["A"]); mst.inputs["B"].default_value = (*[c_ * gain for c_ in hexlin(COL["slime"])], 1)
        nt.links.new(sc_.outputs[0], mst.inputs["Factor"])
        nt.links.new(mst.outputs["Result"], b.inputs["Base Color"]); nt.links.new(mst.outputs["Result"], b.inputs["Emission Color"])
    return m


def make_materials():
    M = {}
    if not LOOKDEV:
        c = mat("pv_clay", (0.55, 0.55, 0.55), 0.8)
        for k in ("print", "label", "alu", "ring_c", "ring_m", "inside", "tab", "slime", "puddle", "ground"):
            M[k] = c
        M["ground"] = mat("pv_ground", (0.12, 0.12, 0.12), 0.9); M["puddle"] = mat("pv_puddle", (0.58, 0.68, 0.76) if CLAYKEY else (0.4, 0.4, 0.4), 0.5)
        return M
    cyan, mag, yel = hexlin("#12A9E6"), hexlin("#FF2D92"), hexlin(COL["marble"])
    M["slime"] = _wet_shader(bpy.data.materials.new("pv_slime"), hexlin(COL["slime"]), 1.0)
    M["slime"].use_nodes = True
    M["puddle"] = _wet_shader(bpy.data.materials.new("pv_puddle"), hexlin(COL["puddle"]), 0.10, marble=yel, gain=0.5)
    M["puddle"].use_nodes = True
    g = mat("pv_ground", hexlin(COL["ground"]), 0.55); M["ground"] = g
    # printed satin black aluminium
    p = mat("pv_print", hexlin("#111111"), 0.36); b = _principled(p); b.inputs["Metallic"].default_value = 0.55
    M["print"] = p
    # label: texture over satin metal
    lab = mat("pv_label", (0.02, 0.02, 0.02), 0.36); nt = lab.node_tree; b = _principled(lab)
    b.inputs["Metallic"].default_value = 0.4
    path = os.path.join(os.environ.get("PREVIS_ASSETS", "/pvlib/assets"), (P.get("subject_params") or {}).get("label", "grawwww_can500_label.png"))
    if os.path.exists(path):
        im = bpy.data.images.load(path); im.colorspace_settings.name = "sRGB"
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = im; tx.interpolation = "Cubic"; tx.extension = "EXTEND"
        nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
        print("PREVIS_LABEL", path, im.size[:], flush=True)
    else:
        print("PREVIS_LABEL_MISSING", path, flush=True); b.inputs["Base Color"].default_value = (*hexlin("#111111"), 1)
    M["label"] = lab
    # brushed bare aluminium (lid, neck, base dome): anisotropic, circular tangent about Z
    al = mat("pv_alu", (0.86, 0.87, 0.9), 0.24); nt = al.node_tree; b = _principled(al)
    b.inputs["Metallic"].default_value = 1.0; b.inputs["Anisotropic"].default_value = 0.6
    tg = nt.nodes.new("ShaderNodeTangent"); tg.direction_type = "RADIAL"; tg.axis = "Z"
    nt.links.new(tg.outputs["Tangent"], b.inputs["Tangent"])
    M["alu"] = al
    ins = mat("pv_inside", (0.55, 0.56, 0.6), 0.45); _principled(ins).inputs["Metallic"].default_value = 1.0; M["inside"] = ins
    for key, hx, em in (("ring_c", "#00A0DC", 0.35), ("ring_m", "#E5007D", 0.35), ("tab", "#FFD400", 0.0)):
        r = mat("pv_" + key, hexlin(hx), 0.28); b = _principled(r); b.inputs["Metallic"].default_value = 0.35
        b.inputs["Emission Color"].default_value = (*hexlin(hx), 1); b.inputs["Emission Strength"].default_value = em
        M[key] = r
    return M


MATS = make_materials()


# ---------------------------------------------------------------- lights, floor, world, puddle
def lights_slime(pack=False):
    if LOOKDEV:
        world((0.002, 0.0016, 0.004), 1.0)
    else:
        world((0.05, 0.05, 0.05), 1.0)
    cl = {"cyan": hexlin("#12A9E6"), "mag": hexlin("#FF2D92"), "top": (1.0, 0.97, 0.94), "uv": (0.42, 0.2, 1.0)}
    if not LOOKDEV:
        cl = {k: (1, 1, 1) for k in cl}
    spec = [("cyan", (-1.25, 0.5, 0.20), (0.0, 0.0, 0.11), 100, (0.22, 0.9)),
            ("mag", (1.25, 0.5, 0.20), (0.0, 0.0, 0.11), 100, (0.22, 0.9)),
            ("top", (0.0, -0.25, 0.9), (0.0, 0.0, 0.1), 45, (0.7, 0.7)),
            ("uv", (0.0, -0.7, 0.18), (0.0, 0.0, 0.1), 8, (0.5, 0.5))]
    if SP.get("pack"):   # packshot extras: a big soft white front fill (true wordmark colours) and a separate floor light
        cl["front"] = cl["floor"] = (1.0, 0.98, 0.96) if LOOKDEV else (1, 1, 1)
        spec += [("front", (0.0, -1.1, 0.42), (0.0, 0.0, 0.09), SP.get("front", 30), (0.9, 0.7)),
                 ("floor", (0.0, -0.25, 0.9), (0.0, 0.0, 0.1), SP.get("floor_top", 30.0), (0.7, 0.7))]
    for name, loc, tgt, e, (sx, sy) in spec:
        if name in SP.get("mute", []):
            continue
        bpy.ops.object.light_add(type="AREA", location=loc); L = bpy.context.object; L.name = "L_" + name
        L.data.shape = "RECTANGLE"; L.data.size, L.data.size_y = sx, sy; L.data.energy = e if LOOKDEV else e * 0.09; L.data.color = cl[name]
        L.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        L.data.use_shadow = True
        LIGHTS[name] = L
    if LOOKDEV and SP.get("glint"):   # optional: puddle and floor get their own small rim glints (off by default) (the strips would mirror as blown-out white blocks)
        for name in ("cyan", "mag"):
            if name in SP.get("mute", []):
                continue
            src = LIGHTS[name]
            bpy.ops.object.light_add(type="AREA", location=src.location); G = bpy.context.object; G.name = "G_" + name
            G.data.shape = "RECTANGLE"; G.data.size, G.data.size_y = 0.05, 0.25; G.data.energy = SP["glint"]
            G.data.color = src.data.color; G.rotation_euler = src.rotation_euler; LIGHTS["G_" + name] = G


LIGHTS = {}


def link_lights():
    """light linking (Blender 4): the strip lights light only the can and the slime on it, the glints light puddle and floor."""
    if not LOOKDEV or ("G_cyan" not in LIGHTS and "G_mag" not in LIGHTS and not SP.get("pack")):
        return
    can = bpy.data.collections.new("rcv_can"); pool = bpy.data.collections.new("rcv_pool")
    sc.collection.children.link(can); sc.collection.children.link(pool)
    for ob in list(bpy.data.objects):
        if ob.type == "LIGHT":
            continue
        grp = can if (ob.name.startswith(("can_", "coat_", "tab_")) or ob.name == "mbS" or ob.parent is not None) else pool
        for c_ in list(ob.users_collection):
            c_.objects.unlink(ob)
        sc.collection.objects.link(ob); grp.objects.link(ob)
    for name, L in LIGHTS.items():
        if name in ("cyan", "mag"):
            L.light_linking.receiver_collection = can
        elif name.startswith("G_"):
            L.light_linking.receiver_collection = pool
        elif name == "uv" and SP.get("pack"):
            L.light_linking.receiver_collection = can
        elif name in ("top", "front") and SP.get("pack"):
            L.light_linking.receiver_collection = can
            if name == "top":
                L.data.energy = SP.get("top", 80)
        elif name == "floor":
            L.light_linking.receiver_collection = pool      # packshot: a separate light paints the soft pool on the floor
    for c_ in (can, pool):
        c_.hide_render = False


def set_slime_pool():
    R, depth = SP.get("puddle_r", 0.30), SP.get("puddle_depth", 0.012)
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, -depth if SP.get("pool", True) else 0.0)); fl = bpy.context.object; fl.name = "floor"
    fl.data.materials.append(MATS["ground"])
    if SP.get("pack") and LOOKDEV:   # seamless near-black: matte, no mirror of the strips
        _principled(MATS["ground"]).inputs["Roughness"].default_value = 0.9
        _principled(MATS["ground"]).inputs["Specular IOR Level"].default_value = 0.15
    lights_slime(SP.get("pack", False))
    if SP.get("pool", True):
        build_puddle(R, depth)


PUDDLE = {}


def build_puddle(R, depth, edge=None):
    nr, na = 150, 256
    th = np.linspace(0, 2 * np.pi, na, endpoint=False)
    Rth = R * (1 + 0.05 * np.sin(3 * th + 1) + 0.03 * np.sin(5 * th + 2) + 0.02 * np.sin(8 * th)) if edge is None else edge(th)
    s = np.linspace(0, 1, nr) ** 0.85
    S, T = np.meshgrid(s, th, indexing="ij")
    rr = S * Rth[None, :]
    X, Y = rr * np.cos(T), rr * np.sin(T)
    zb = -(depth + 0.0006) * np.clip((S - 0.9) / 0.1, 0, 1) ** 1.6
    verts = np.stack([X, Y, zb], -1).reshape(-1, 3)
    idx = np.arange(nr * na).reshape(nr, na)
    faces = []
    for i in range(nr - 1):
        a, b = idx[i], idx[i + 1]
        faces += np.stack([a, np.roll(a, -1), np.roll(b, -1), b], -1).tolist()
    me = bpy.data.meshes.new("puddle"); me.from_pydata(verts.tolist(), [], faces); me.update()
    ob = bpy.data.objects.new("puddle", me); sc.collection.objects.link(ob); me.materials.append(MATS["puddle"])
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    PUDDLE.update(me=me, X=X, Y=Y, rr=rr, ang=T, zb=zb, taper=1 - np.clip((S - 0.62) / 0.3, 0, 1), events=[])
    FRAME_HOOKS.append(puddle_update)


def add_ripples(spec):
    if not spec:
        return
    for ev in (spec if isinstance(spec, list) else [spec]):
        PUDDLE["events"].append({"t0": ev.get("t0", 0.0), "amp": ev.get("amp", 0.003), "rings": ev.get("rings", 3),
                                 "c": ev.get("speed", 0.34), "lam": ev.get("lambda", 0.034)})


def puddle_update(t):
    if not PUDDLE:
        return
    z = PUDDLE["zb"].copy(); rr = PUDDLE["rr"]
    for ev in PUDDLE["events"]:
        for i in range(ev["rings"]):
            ti = t - ev["t0"] - i * 0.11
            if ti < 0:
                continue
            Rr = ev["c"] * ti; x = rr - Rr; lam = ev["lam"]
            z += ev["amp"] * math.exp(-ti / 0.9) * np.cos(2 * np.pi * x / lam) * np.exp(-(x / (1.5 * lam)) ** 2) \
                / math.sqrt(1 + Rr / 0.04) * PUDDLE["taper"]
    me = PUDDLE["me"]; co = np.stack([PUDDLE["X"], PUDDLE["Y"], z], -1).reshape(-1, 3).astype(np.float32)
    me.vertices.foreach_set("co", co.ravel()); me.update()
    st = PUDDLE.get("stain")
    if st:
        tau = t - st["t"]; val = np.zeros(rr.shape, dtype=np.float32)
        if 0 <= tau < st["fall_by"] - st["t"]:
            Rs = st["r0"] + (st["r_end"] - st["r0"]) * math.sqrt(sm01(tau / 1.1))
            Rs = Rs * (1 + 0.18 * np.sin(5 * PUDDLE["ang"] + 1.3) * np.sin(3 * PUDDLE["ang"] + 0.4))
            fade = 1 - sm01((tau - 0.35) / (st["fall_by"] - st["t"] - 0.35))
            val = ((1 - np.clip((rr - 0.55 * Rs) / (0.45 * Rs + 1e-6), 0, 1)) * fade).astype(np.float32)
        me.attributes["stain"].data.foreach_set("value", val.reshape(-1))


# ---------------------------------------------------------------- metaball families
class MB:
    def __init__(self, name, mat_, res, cap=700):
        # Blender floors metaball render_resolution at 5 mm: scale the object down by k and the elements up by 1/k
        self.k = min(1.0, res / 0.005)
        self.d = bpy.data.metaballs.new(name); self.d.resolution = 0.02; self.d.render_resolution = res / self.k
        self.d.threshold = 0.6; self.d.update_method = "UPDATE_ALWAYS"; self.d.materials.append(mat_)
        self.o = bpy.data.objects.new(name, self.d); sc.collection.objects.link(self.o); self.o.scale = (self.k,) * 3
        self.els = []
        for _ in range(cap):
            e = self.d.elements.new(type="BALL"); e.hide = True; e.radius = 0.001; self.els.append(e)

    def set(self, items):
        items = items[:len(self.els)]
        for i, e in enumerate(self.els):
            if i < len(items):
                it = items[i]; rv = max(it[3], 1e-4); k = self.k
                e.hide = False; e.co = (it[0] / k, it[1] / k, it[2] / k); e.radius = rv / 0.575 / k; e.stiffness = 2.0
                if len(it) > 4 and it[4] is not None:
                    e.type = "ELLIPSOID"; e.size_x, e.size_y, e.size_z = it[4]
                else:
                    e.type = "BALL"
            else:
                e.hide = True


MB_P = MB_S = MB_D = None


def slime_init(res_s, res_p, res_d=0.004, cap_p=700):
    """three families: mbP puddle-coloured detail (crown, droplets, meniscus), mbS slime-coloured detail (drips, strands,
    squeeze rings, glob), mbD the big puddle-coloured dome (coarse)."""
    global MB_P, MB_S, MB_D
    if MB_P is not None:   # several subjects share one set of metaball families
        return
    MB_P = MB("mbP", MATS["puddle"], res_p, cap=cap_p); MB_S = MB("mbS", MATS["slime"], res_s); MB_D = MB("mbD", MATS["puddle"], res_d, cap=4)

    def hook(t):
        a, b, d = [], [], []
        for f in SLIME_SOURCES:
            pa, pb = f(t); a += pa; b += pb
        for it in list(a):
            if len(it) > 4 and it[3] > 0.03:      # big ellipsoids (the bulge) go to the coarse family
                a.remove(it); d.append(it)
        MB_P.set(a); MB_S.set(b); MB_D.set(d)
    FRAME_HOOKS.append(hook)


# ---------------------------------------------------------------- the can
CAN_DEF = {"h": 0.168, "r": 0.033, "lid_r": 0.0265, "split": [0.036, 0.124], "teeth": 3, "tooth_h": 0.006, "wall": 0.001}
RAMP = [(0, 1.0), (1.5, 1.0), (3.5, 0.75), (6, 0.38), (9, 0.1), (12, 0.0)]    # mm from the seam -> edge weight


def castle(th, ph, n, ew=0.03):
    per = 2 * np.pi / n
    x = np.mod(th - ph + per / 2, per) / per
    return np.clip((x - 0.25) / ew, 0, 1) * np.clip((0.75 - x) / ew, 0, 1)


def can_rows(kind, c):
    """rows of one part, mm: (r, z, w, seam, material of the quad above); materials 0 print, 1 label, 2 alu, 3 ring_c, 4 ring_m."""
    rb, rn = c["r"] * 1000, c["lid_r"] * 1000; s0, s1 = c["split"][0] * 1000, c["split"][1] * 1000; H = c["h"] * 1000
    R = []
    if kind == "bot":
        for r, z, m in ((0.3, 9.5, 2), (6, 9.1, 2), (12, 7.9, 2), (18, 5.8, 2), (22.5, 3.6, 2), (25.3, 1.4, 2), (26.8, 0.15, 2),
                        (28.6, 0.5, 0), (30.8, 1.6, 0), (32.4, 3.5, 0)):
            R.append((r, z, 0, None, m))
        for z in (7, 12, 20, s0 - 14):
            R.append((rb, z, 0, None, 0))
        for off, w in reversed(RAMP[1:]):
            R.append((rb, s0 - off, w, 0, 0))
        R.append((rb, s0, 1.0, 0, 0))
    elif kind == "mid":
        for i, (off, w) in enumerate(RAMP):
            R.append((rb, s0 + off, w, 0, 4 if i == 0 else 1))
        R.append((rb, s0 + 30, 0, None, 1)); R.append((rb, (s0 + s1) / 2, 0, None, 1)); R.append((rb, s1 - 30, 0, None, 1))
        for i, (off, w) in enumerate(reversed(RAMP)):
            R.append((rb, s1 - RAMP[len(RAMP) - 1 - i][0], w, 1, 3 if i == len(RAMP) - 2 else 1))
    else:
        for i, (off, w) in enumerate(RAMP[:-1]):
            R.append((rb, s1 + off, w, 1, 0))
        z0, z1, n = s1 + 14, 157.0, 9
        for k in range(n):
            u = k / (n - 1); r = rn + (rb - rn) * (0.5 + 0.5 * math.cos(math.pi * u))
            R.append((r, z0 + u * (z1 - z0), 0, None, 0 if k < 6 else 2))
        for r, z in ((rn, 160), (rn, 163.5), (rn + 0.8, 165.5), (rn + 1.2, 167.0), (rn + 0.8, H - 0.0), (rn - 0.3, H), (rn - 1.4, H - 0.9),
                     (rn - 2.4, 165.4), (rn - 3.2, 164.0), (rn - 4.5, 163.7), (rn - 10, 163.6), (rn - 17, 163.6), (0.3, 163.6)):
            R.append((r, z, 0, None, 2))
    return R


def outer_r_func(kind, c):
    rows = can_rows(kind, c); z0 = {"bot": 0.0, "mid": c["split"][0], "top": c["split"][1]}[kind] * 1000
    zs = np.array([r[1] for r in rows]); rs = np.array([r[0] for r in rows])
    sel = {"top": slice(0, 16), "bot": slice(10, None), "mid": slice(None)}[kind]   # monotonic stretches of z
    zz, rr_ = zs[sel], rs[sel]; o = np.argsort(zz)
    return lambda zl: float(np.interp(zl * 1000 + z0, zz[o], rr_[o])) / 1000.0


def build_part(kind, c, N=720):
    rows = can_rows(kind, c); s0, s1 = c["split"][0] * 1000, c["split"][1] * 1000
    z_nom0 = {"bot": 0.0, "mid": s0, "top": s1}[kind]
    th = np.linspace(-np.pi, np.pi, N + 1)
    ph = [0.0, np.pi / 3]
    tc = [c["tooth_h"] * 1000 * castle(th, ph[i], c["teeth"]) for i in (0, 1)]
    V, UV, mats = [], [], []
    for (r, z, w, seam, m) in rows:
        zr = np.broadcast_to(z + (w * tc[seam] if seam is not None else 0.0) - z_nom0, th.shape)
        V.append(np.stack([r * np.sin(th), -r * np.cos(th), zr], -1) / 1000.0)
    V = np.array(V)[:, :N]                           # rows x N x 3 (the seam column is shared: wrap-around quads)
    nR = len(rows)
    faces = []; idx = np.arange(nR * N).reshape(nR, N)
    for i in range(nR - 1):
        a, b = idx[i], idx[i + 1]
        faces.append(np.stack([a, np.roll(a, -1), np.roll(b, -1), b], -1))
        mats += [rows[i][4]] * N
    faces = np.concatenate(faces)
    # uv: u around (0.5 = front), v over the 88 mm band for the label rows (z nominal), else arbitrary
    u = 0.5 + th / (2 * np.pi)
    vv = np.array([(min(max((rw[1] - s0) / (s1 - s0), 0), 1)) for rw in rows])
    uvs = []
    for i in range(nR - 1):
        for j in range(N):
            uvs += [(u[j], vv[i]), (u[j + 1], vv[i]), (u[j + 1], vv[i + 1]), (u[j], vv[i + 1])]
    me = bpy.data.meshes.new("can_" + kind); me.from_pydata(V.reshape(-1, 3).tolist(), [], faces.tolist()); me.update()
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(uvs, dtype=np.float32).ravel())
    me.polygons.foreach_set("material_index", np.array(mats, dtype=np.int32))
    for k in ("print", "label", "alu", "ring_c", "ring_m"):
        me.materials.append(MATS[k])
    for _ in range(5):
        me.materials.append(MATS["inside"])
    ob = bpy.data.objects.new("can_" + kind, me); sc.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(45)); ob.select_set(False)
    so = ob.modifiers.new("shell", "SOLIDIFY"); so.thickness = c["wall"]; so.offset = -1.0; so.use_even_offset = True
    so.use_rim = True; so.material_offset = 5; so.material_offset_rim = 5
    return ob


def build_tab(top, c):
    zl = 163.6 / 1000 - c["split"][1]
    def add(op, name, mat_, **kw):
        op(**kw); o = bpy.context.object; o.name = name; o.data.materials.append(mat_); o.parent = top
        return o
    pl = add(bpy.ops.mesh.primitive_cube_add, "tab_plate", MATS["tab"], location=(0.004, 0, zl + 0.0006), size=1)
    pl.scale = (0.009, 0.0042, 0.0006); b = pl.modifiers.new("b", "BEVEL"); b.width = 0.0004; b.segments = 3
    rg = add(bpy.ops.mesh.primitive_torus_add, "tab_ring", MATS["tab"], location=(-0.0055, 0, zl + 0.0006), major_radius=0.0042,
             minor_radius=0.0011, major_segments=40, minor_segments=10)
    rg.scale = (1.35, 1.0, 0.6)
    rv = add(bpy.ops.mesh.primitive_cylinder_add, "tab_rivet", MATS["alu"], location=(0.0085, 0, zl + 0.0008), radius=0.0016, depth=0.0008)
    for o in (pl, rg, rv):
        bpy.context.view_layer.objects.active = o; o.select_set(True); bpy.ops.object.shade_smooth(); o.select_set(False)


def subject_can3(sp):
    c = {**CAN_DEF, **sp.get("can", {})}; s0, s1 = c["split"]
    nom = {"bot": 0.0, "mid": s0, "top": s1}; hp = {"bot": s0, "mid": s1 - s0, "top": c["h"] - s1}
    parts = {k: build_part(k, c) for k in ("bot", "mid", "top")}
    build_tab(parts["top"], c)
    asm = bool(sp.get("assembled"))
    if asm:
        body_z, body_a = Curve(sp.get("body", [{"t": 0, "z": 0.0, "a": 0}]), "z"), Curve(sp.get("body", [{"t": 0, "z": 0.0, "a": 0}]), "a")
        zf = {k: (lambda t, k=k: body_z(t) + nom[k]) for k in parts}; af = {k: body_a for k in parts}
    else:
        pk = sp.get("parts", {})
        zf, af = {}, {}
        for k in parts:
            keys = pk.get(k, [{"t": 0, "z": nom[k], "a": 0}])
            zf[k], af[k] = Curve(keys, "z"), Curve(keys, "a")
    state = lambda k, t: (zf[k](t), af[k](t))
    for f in range(1, N + 1):
        t = (f - 1) / FPS + T0
        for k, ob in parts.items():
            z, a = state(k, t)
            ob.location = (0, 0, z); ob.rotation_euler = (0, 0, math.radians(a))
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
    S = sp.get("slime", {})
    res = S.get("res", 0.001)
    slime_init(res, S.get("res_puddle", 0.0015))
    rfun = {k: outer_r_func(k, c) for k in parts}
    CTX = dict(c=c, nom=nom, hp=hp, parts=parts, state=state, asm=asm, rfun=rfun)
    slime_can(S, CTX)
    add_ripples(S.get("ripples"))
    return lambda t: Vector((0, 0, 0))


def pw(part, ctx, t, x, y, zl):
    """part-local point (x, y, zl above the part's nominal bottom) -> world."""
    z, a = ctx["state"](part, t); ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    return (x * ca - y * sa, x * sa + y * ca, z + zl)


def az_dir(az_deg):
    return math.sin(math.radians(az_deg)), -math.cos(math.radians(az_deg))


def tooth(ctx, seam, az_deg):
    c = ctx["c"]; th = math.radians(az_deg)
    ph = (0.0, math.pi / 3)[seam]
    return float(c["tooth_h"] * castle(np.array([th]), ph, c["teeth"])[0])


# ---------------------------------------------------------------- slime on the can
def slime_can(S, ctx):
    c, nom, hp, state, asm = ctx["c"], ctx["nom"], ctx["hp"], ctx["state"], ctx["asm"]
    rb = c["r"]
    rnd = random.Random(P.get("seed", 7) + 3)
    # --- bulge: puddle-coloured dome at the centre
    if S.get("bulge"):
        bh, br = Curve(S["bulge"], "h"), Curve(S["bulge"], "r")

        def src_bulge(t):
            h, r = bh(t), br(t)
            return ([(0, 0, 0, r, (1.0, 1.0, h / r))] if h > 0.0008 else []), []
        SLIME_SOURCES.append(src_bulge)
        dome = lambda t: bh(t)
    else:
        dome = lambda t: 0.0
    # --- meniscus where a part crosses the surface (puddle-coloured ring clinging to it)

    def src_meniscus(t):
        out = []
        for k in ("bot", "mid", "top"):
            z, a = state(k, t)
            if z < -0.0005 and z + hp[k] > 0.004:
                R0 = ctx["rfun"][k](min(max(-z, 0.002), hp[k] - 0.001))
                for i in range(40):
                    ang = 2 * math.pi * i / 40
                    out.append(((R0 + 0.0022) * math.cos(ang), (R0 + 0.0022) * math.sin(ang), 0.0012, 0.0033))
        return out, []
    SLIME_SOURCES.append(src_meniscus)
    # --- coat shells
    if S.get("coat"):
        cs = S["coat"]; slide = cs.get("slide_until", 2.5)
        tt = [(f - 1) / FPS for f in range(1, N + 1)]
        for k in cs.get("parts", []):
            build_coat(k, ctx, slide, dome, tt, rnd)
    # --- drips
    for d in S.get("drips", []):
        add_drip(d, ctx, rnd)
    # --- strands and squeeze rings
    if S.get("strands"):
        add_strands(S["strands"], ctx, rnd)
    if S.get("squeeze"):
        add_squeeze(S["squeeze"], ctx)
    if S.get("crown"):
        add_crown(S["crown"], ctx, rnd)
    if S.get("droplets"):
        add_droplets(S["droplets"], ctx, rnd)


def build_coat(k, ctx, slide, dome, tt, rnd):
    c, hp, state = ctx["c"], ctx["hp"], ctx["state"]; rf = ctx["rfun"][k]
    nc = 240; thc = np.linspace(-np.pi, np.pi, nc, endpoint=False)
    zc_top = hp[k] if k != "top" else 0.036 + 0.0         # the top part is coated up to the neck
    nrw = int(zc_top / 0.0015) + 1; zl = np.linspace(0, zc_top, nrw)
    lower_seam = {"bot": None, "mid": 0, "top": 1}[k]
    ph = (0.0, np.pi / 3)
    shift = np.zeros((nrw, nc))
    if lower_seam is not None:
        tc = c["tooth_h"] * castle(thc, ph[lower_seam], c["teeth"])
        wz = np.interp(zl * 1000, [r[0] for r in RAMP], [r[1] for r in RAMP], right=0.0)
        shift = wz[:, None] * tc[None, :]
    rr_ = np.array([rf(z) for z in zl])
    # wet height history (running max of dome top minus part bottom), full if the part starts out of the slime
    z0b = state(k, 0.0)[0]
    wet = []; cur = hp[k] if z0b > dome(0.0) + 0.002 else 0.0
    for t in tt:
        zb_, _ = state(k, t)
        cur = max(cur, min(hp[k], dome(t) - zb_ + 0.003, hp[k]))
        wet.append(cur)
    ph1, ph2 = rnd.uniform(0, 6.28), rnd.uniform(0, 6.28)
    me = bpy.data.meshes.new("coat_" + k)
    idx = np.arange(nrw * nc).reshape(nrw, nc)
    faces = []
    for i in range(nrw - 1):
        a, b = idx[i], idx[i + 1]; faces.append(np.stack([a, np.roll(a, -1), np.roll(b, -1), b], -1))
    faces = np.concatenate(faces)
    base = np.stack([np.broadcast_to(np.sin(thc), (nrw, nc)), -np.broadcast_to(np.cos(thc), (nrw, nc))], -1)
    me.from_pydata(np.zeros((nrw * nc, 3)).tolist(), [], faces.tolist())
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons)); me.update()
    me.attributes.new("cov", "FLOAT", "POINT")
    cm = coat_material()
    me.materials.append(cm)
    ob = bpy.data.objects.new("coat_" + k, me); sc.collection.objects.link(ob); ob.parent = ctx["parts"][k]
    Z = zl[:, None] + shift

    def upd(t):
        fi = min(max(int(round((t - T0) * FPS)), 0), len(wet) - 1); w = wet[fi]
        s = sm01((t) / slide)
        noise = 0.8 + 0.4 * (0.5 + 0.5 * np.sin(thc * 5 + ph1) * np.cos(thc * 3 + ph2))
        zc = min(w, zc_top - 0.002) * (1 - 0.75 * s * noise)               # (nc+1,)
        h = zl[:, None]
        edge = np.clip((zc[None, :] - h) / 0.012, 0, 1); edge = edge * edge * (3 - 2 * edge)
        T = 0.0014 * (1 - 0.45 * s)
        riv = 0.75 + 0.25 * np.sin(thc[None, :] * 7 + ph1 + h * 35)
        body = T * riv * (0.55 + 0.45 * (1 - np.minimum(h / np.maximum(zc[None, :], 1e-3), 1)))
        bead = (0.0010 + 0.0016 * s) * np.exp(-(h / 0.007) ** 2) * (0.7 + 0.3 * np.sin(thc[None, :] * 9 + ph2))
        thick = (body + bead) * edge
        r = rr_[:, None] + 0.00012 + thick
        co = np.stack([r * base[..., 0], r * base[..., 1], Z], -1).reshape(-1, 3).astype(np.float32)
        me.vertices.foreach_set("co", co.ravel())
        cov = np.clip((thick - 0.00015) / 0.0004, 0, 1).reshape(-1).astype(np.float32)
        me.attributes["cov"].data.foreach_set("value", cov); me.update()
    FRAME_HOOKS.append(upd)


def coat_material():
    if not LOOKDEV:
        return MATS["slime"]
    m = bpy.data.materials.new("pv_coat"); m.use_nodes = True; nt = m.node_tree; N = nt.nodes
    for n in list(N):
        N.remove(n)
    out = N.new("ShaderNodeOutputMaterial"); mx = N.new("ShaderNodeMixShader"); tr = N.new("ShaderNodeBsdfTransparent")
    at = N.new("ShaderNodeAttribute"); at.attribute_name = "cov"; at.attribute_type = "GEOMETRY"
    sl = N.new("ShaderNodeGroup") if False else None
    # slime shader copy (a Principled with the wet settings)
    b = N.new("ShaderNodeBsdfPrincipled"); col = hexlin(COL["slime"])
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = 0.16
    b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Coat Roughness"].default_value = 0.10
    b.inputs["Subsurface Weight"].default_value = 0.55; b.inputs["Subsurface Scale"].default_value = 0.006
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.45, 0.45); b.inputs["Emission Color"].default_value = (*col, 1)
    lw = N.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.35
    ma = N.new("ShaderNodeMath"); ma.operation = "MULTIPLY_ADD"; ma.inputs[1].default_value = 1.6; ma.inputs[2].default_value = 0.55
    nt.links.new(lw.outputs["Fresnel"], ma.inputs[0]); nt.links.new(ma.outputs[0], b.inputs["Emission Strength"])
    nt.links.new(at.outputs["Fac"], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(b.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m


def add_drip(d, ctx, rnd):
    c, hp, nom, asm = ctx["c"], ctx["hp"], ctx["nom"], ctx["asm"]; k = d["part"]; az = d["az"]; t0 = d.get("t0", 0.0)
    rf = ctx["rfun"][k]; rate = d.get("rate", 0.03)
    runner = ("z0" in d) or asm
    z0 = d.get("z0", nom[k] + hp[k] * (0.55 if k != "top" else 0.4)) - nom[k]    # part-local start height of a runner
    low = hp[k]

    def src(t):
        tau = t - t0
        if tau < 0:
            return [], []
        out = []; dx, dy = az_dir(az)
        if runner:
            zs = max(z0 - rate * tau - 0.5 * 0.012 * tau * tau, 0.0)
            zbot_world_floor = None
            head_r = 0.0033 * sm01(tau / 0.35) + 0.0006
            n = min(60, max(2, int((z0 - zs) / 0.0012) + 1))
            for i in range(n):
                u = i / (n - 1); zl = z0 + (zs - z0) * u
                rad = 0.0011 + (head_r - 0.0011) * (u ** 3) if i else 0.0013
                rr = rf(min(max(zl, 0.0), hp[k])) + 0.0004 * rad / 0.001
                out.append(pw(k, ctx, t, rr * dx, rr * dy, zl) + (rad,))
            return [], out
        # hanger: bead on the part's lower edge stretches, then detaches and falls
        edge_h = tooth(ctx, {"bot": 0, "mid": 0, "top": 1}[k], az) if k != "bot" else 0.0
        T1 = 0.9
        rr = rf(0.0) + 0.0006
        P0 = pw(k, ctx, t, rr * dx, rr * dy, edge_h)
        if tau < T1:
            u = tau / T1; ln = 0.003 + 0.034 * u ** 1.4; head = 0.0022 + 0.0022 * u
            n = min(60, max(2, int(ln / 0.0012) + 1))
            for i in range(n):
                v = i / (n - 1); rad = head + (0.0013 - head) * math.sin(math.pi * v * 0.5) ** 1.0 if i < n - 1 else head
                rad = 0.0016 + (head - 0.0016) * v ** 3
                out.append((P0[0], P0[1], P0[2] - ln * v, rad))
            return [], out
        # falling drop: starts where the head was at T1 (relative to the part at detach time)
        Pd = pw(k, ctx, t0 + T1, rr * dx, rr * dy, edge_h)
        ln = 0.037; z_head = Pd[2] - ln; tf = tau - T1
        zf = z_head - 0.5 * G_ACC * tf * tf
        if zf < -0.004:
            return [], []
        out.append((Pd[0], Pd[1], zf, 0.0044)); out.append((Pd[0], Pd[1], zf + 0.007, 0.0028))
        if tf < 0.25:   # stub springs back to the part
            P1 = pw(k, ctx, t, rr * dx, rr * dy, edge_h)
            out.append((P1[0], P1[1], P1[2] - 0.004 * (1 - tf / 0.25), 0.0016 * (1 - tf / 0.25) + 0.0003))
        return [], out
    SLIME_SOURCES.append(src)


def add_strands(sd, ctx, rnd):
    c, hp, state = ctx["c"], ctx["hp"], ctx["state"]; nom = ctx["nom"]
    azs = [30 + 120 * i for i in range(3)]
    for A, B in sd["between"]:
        def src(t, A=A, B=B):
            zA, _ = state(A, t); zB, _ = state(B, t)
            gap = zB - (zA + hp[A])
            if gap < 0.0055:
                return [], []
            fade = sm01((gap - 0.0055) / 0.02)
            out = []
            for az in azs:
                dx, dy = az_dir(az); rA = ctx["rfun"][A](hp[A] - 0.001); rB = ctx["rfun"][B](0.001)
                sA = {"bot": 0, "mid": 1, "top": None}[A]; sB = {"mid": 0, "top": 1, "bot": None}[B]
                tA = tooth(ctx, 0 if A in ("bot", "mid") and B == "mid" else 1, az) if True else 0
                PA = pw(A, ctx, t, rA * dx, rA * dy, hp[A] + (tooth(ctx, 0, az) if A == "bot" else tooth(ctx, 1, az)))
                PB = pw(B, ctx, t, rB * dx, rB * dy, tooth(ctx, 0, az) if B == "mid" else tooth(ctx, 1, az))
                L = max(abs(PB[2] - PA[2]), 0.004)
                n = min(60, max(6, int(L / 0.0011) + 1))
                for i in range(n):
                    u = i / (n - 1); rad = (0.0022 - 0.0013 * math.sin(math.pi * u) * min(1.0, 0.04 / L + 0.25)) * (0.5 + 0.5 * fade)
                    sag = 0.0 if i in (0, n - 1) else -0.012 * math.sin(math.pi * u) * min(1.0, L / 0.03)
                    out.append((PA[0] + (PB[0] - PA[0]) * u, PA[1] + (PB[1] - PA[1]) * u, PA[2] + (PB[2] - PA[2]) * u + sag, max(rad, 0.0009)))
            return [], out
        SLIME_SOURCES.append(src)


def add_squeeze(keys, ctx):
    c = ctx["c"]
    for kz in keys:
        def src(t, kz=kz):
            tau = t - kz["t"]
            if tau < 0 or tau > 0.9:
                return [], []
            rr = c["r"] + 0.0016 + 0.006 * sm01(tau / 0.18) + 0.002 * sm01(tau / 0.9)
            z = kz["z"] - 0.03 * (tau / 0.9) ** 2 + 0.0
            rad = (0.0034 * sm01(tau / 0.04) * (1 - sm01((tau - 0.3) / 0.6))) + 0.0002
            return [], [(rr * math.cos(2 * math.pi * i / 72), rr * math.sin(2 * math.pi * i / 72), z, rad) for i in range(72)]
        SLIME_SOURCES.append(src)


def add_crown(cr, ctx, rnd):
    t0, h, r, fall = cr["t"], cr["h"], cr["r"], cr["fall_by"]; rb = cr.get("r0", ctx["c"]["r"]); NA = cr.get("n", 56); frs = (0.0, 0.33, 0.66, 1.0) if "m" not in cr else tuple(np.linspace(0, 1, cr["m"])); lean = cr.get("lean", 0.010)
    rs = 1.0 if "wall_r" in cr else (min(1.0, r / 0.045) ** 0.5 if "r0" in cr else 1.0)   # a crown from a small drop gets thinner walls
    fk = [0.5 + 0.5 * (1 if k % 2 == 0 else 0.45) * rnd.uniform(0.8, 1.0) for k in range(NA)]

    def src(t):
        tau = t - t0
        if tau < 0 or t > fall:
            return [], []
        up = sm01(tau / 0.13) ** 0.7; down = 1 - sm01((tau - 0.22) / (fall - t0 - 0.22))
        Hc = h * up * down
        if Hc < 0.002:
            return [], []
        Rc = rb + 0.0045 + (r - rb - 0.0045) * sm01(tau / 0.5) + 0.02 * sm01((tau - 0.3) / 0.8)
        out = []
        for k in range(NA):
            ang = 2 * math.pi * k / NA; Hk = Hc * fk[k]
            for j, fr in enumerate(frs):
                R = Rc + lean * fr * (1 - 0.5 * down) ; rad = (0.0044 + (0.0014 if j == 3 else 0.0) - 0.0006 * fr * (1 - up)) * rs if "wall_r" not in cr else cr["wall_r"] * (1 + (0.32 if j == len(frs) - 1 else 0.0) - 0.14 * fr * (1 - up))
                out.append((R * math.cos(ang), R * math.sin(ang), 0.0015 + Hk * fr, rad))
        return out, []
    SLIME_SOURCES.append(src)


def add_droplets(dr, ctx, rnd):
    t0, n, reach = dr["t"], dr["n"], dr["reach"]
    drops = []
    for k in range(n):
        T = rnd.uniform(*dr.get("T", (0.25, 0.42))); u = rnd.uniform(0.35, 1.0); ang = rnd.uniform(0, 2 * math.pi)
        drops.append(dict(T=T, vh=reach * u / T, vz=G_ACC * T / 2, ang=ang, rad=rnd.uniform(*dr.get("rad", (0.0022, 0.0046))), mag=(k % 2 == 1 and not dr.get("clear"))))

    def src(t):
        a, b = [], []
        tau = t - t0
        if tau < 0:
            return a, b
        for d in drops:
            if tau > d["T"]:
                continue
            Rd = dr.get("r0", 0.04) + d["vh"] * tau; z = 0.004 + d["vz"] * tau - 0.5 * G_ACC * tau * tau
            if z < 0.0015:
                continue
            it = (Rd * math.cos(d["ang"]), Rd * math.sin(d["ang"]), z, d["rad"])
            (b if d["mag"] else a).append(it)
        return a, b
    SLIME_SOURCES.append(src)


# ---------------------------------------------------------------- subject: hanging glob (s1, still-only)
def subject_slime_drip(sp):
    """Hanging glob. Static (the s1 still) unless `keys [{t, bulb_z, neck_r}]` (eased, like can3 parts) and/or
    `snap {t, v0, recoil_z, wobble{period, cycles}}`: at snap.t the neck pinches off, the drop falls ballistically (initial
    speed v0, gravity), the upper strand recoils to recoil_z and wobbles (damped). At t = 0 the result is the old static glob."""
    res = sp.get("res", 0.0004)
    slime_init(res, 0.003)
    top, bz, br = sp.get("top_z", 0.335), sp.get("bulb_z", 0.272), sp.get("bulb_r", 0.0105)
    neck = sp.get("neck_r", 0.0042)
    rnd = random.Random(5)
    bubbles = []
    for _ in range(16):
        a_, f_ = math.radians(rnd.uniform(-70, 70)), math.radians(rnd.uniform(-60, 60))
        bubbles.append((br * 0.95 * math.sin(a_) * math.cos(f_), -br * 0.95 * math.cos(a_) * math.cos(f_), bz + br * 1.3 * 0.95 * math.sin(f_),
                        rnd.uniform(0.00022, 0.0004)))
    keys, snap = sp.get("keys"), sp.get("snap")
    bz_c = Curve(keys, "bulb_z", bz) if keys else (lambda t: bz)
    nk_c = Curve(keys, "neck_r", neck) if keys else (lambda t: neck)
    ts = snap["t"] if snap else None
    wob = (snap or {}).get("wobble", {"period": 0.24, "cycles": 3})

    def state(t):
        """-> (bulb z, neck radius, drop z or None, strand tip z or None, tau since snap)"""
        if ts is None or t < ts:
            return bz_c(t), nk_c(t), None, None, 0.0
        tau = t - ts; zb, nr = bz_c(ts), nk_c(ts)
        zd = zb - snap.get("v0", 0.15) * tau - 0.5 * G_ACC * tau * tau
        z0 = zb + 0.01
        per = wob["period"]; dec = wob["cycles"] * per / 3.0
        ztip = snap["recoil_z"] + (z0 - snap["recoil_z"]) * math.exp(-tau / dec) * math.cos(2 * math.pi * tau / per)
        return zb, nr, zd, ztip, tau

    def src(t):
        zb, nr, zd, ztip, tau = state(t)
        out = [(0, 0, top, 0.022, (1.2, 1.2, 0.8))]
        if zd is None:
            bzt, L = zb, zb - top + 0.008 + 0.002
        else:
            bzt = ztip; L = ztip - top + 0.008
        n = max(14, min(60, int(abs(L) / (1.2 * nr)) + 1)) if zd is None else 40
        wx = 0.0
        for i in range(n + 1):
            u = i / n; z = top - 0.008 + L * u
            rad = nr + (0.0125 - nr) * (1 - u) ** 2.2
            if zd is not None:      # broken strand: wobbles sideways, ends in a small bead
                wx = 0.0022 * math.exp(-tau / 0.35) * math.sin(2 * math.pi * tau / (wob["period"] * 1.15)) * u ** 1.5
            out.append((0.0006 * math.sin(u * 3) + wx, 0, z, max(rad, nr)))
        if zd is None:
            out.append((0, 0, zb - 0.001, br, (1.0, 1.0, 1.3)))
        else:
            out.append((wx, 0, ztip - 0.001, 0.0034))
            if zd > 0.17:
                out.append((0, 0, zd - 0.001, br * 0.97, (1.0, 1.0, 1.3 + 0.5 * min(1.0, tau / 0.05))))
                if tau < 0.05:      # the thread between the tip and the falling drop thins out
                    k = min(50, max(2, int((ztip - zd) / 0.0007)))
                    for i in range(1, k):
                        out.append((0, 0, zd + (ztip - zd) * i / k, 0.0009 * (1 - tau / 0.05) + 0.0004))
        return [], out
    SLIME_SOURCES.append(src)
    # bokeh puddle far behind (only seen out of focus in the lower third)
    bp = sp.get("bokeh", {"y": 1.12, "r": 0.34})
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=bp["r"], fill_type="NGON", location=(0, bp["y"], 0.0006))
    bo = bpy.context.object; bo.scale = (1.5, 0.8, 1)
    bm = bpy.data.materials.new("bokeh"); bm.use_nodes = True; bb = _principled(bm)
    bb.inputs["Base Color"].default_value = (0, 0, 0, 1); bb.inputs["Emission Color"].default_value = (*hexlin(COL["puddle"]), 1)
    bb.inputs["Emission Strength"].default_value = 1.6 if LOOKDEV else 0.0; bo.data.materials.append(bm)
    # tiny bubbles in the glob
    mbub = bpy.data.materials.new("bubble"); mbub.use_nodes = True; b = _principled(mbub)
    b.inputs["Base Color"].default_value = (1, 0.8, 0.92, 1); b.inputs["Roughness"].default_value = 0.03
    b.inputs["Emission Color"].default_value = (1, 0.45, 0.8, 1); b.inputs["Emission Strength"].default_value = 1.2
    bub_objs = []
    for (x, y, z, r) in bubbles:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, z), segments=24, ring_count=12)
        o = bpy.context.object; o.data.materials.append(mbub); bpy.ops.object.shade_smooth(); bub_objs.append((o, (x, y, z)))
    if keys or snap:   # the bubbles ride with the bulb, then with the falling drop
        for f in range(1, N + 1):
            t = (f - 1) / FPS + T0; zb, nr, zd, ztip, tau = state(t)
            dz = (zb if zd is None else zd) - bz
            for o, (x, y, z) in bub_objs:
                o.location = (x, y, z + dz); o.keyframe_insert("location", frame=f)
    return lambda t: Vector((0, 0, 0))


def subject_slime_impact(sp):
    """A drop falls onto the puddle centre and splashes (no can). subject_params: drop {r, t_hit, v_hit}; slime {crown (+ r0 =
    base radius), droplets (+ r0), ripples, stain {t, r_end, fall_by}}. The scene is empty until the drop enters the frame."""
    S = sp.get("slime", {}); d = sp.get("drop", {"r": 0.009, "t_hit": 0.75, "v_hit": 2.2})
    slime_init(sp.get("res", 0.001), S.get("res_puddle", 0.0015))
    rnd = random.Random(P.get("seed", 7) + 5)
    ctx = {"c": {"r": 0.009}}
    if S.get("crown"):
        add_crown(S["crown"], ctx, rnd)
    if S.get("droplets"):
        add_droplets(S["droplets"], ctx, rnd)
    add_ripples(S.get("ripples"))
    if S.get("stain") and PUDDLE:
        st = S["stain"]; PUDDLE["me"].attributes.new("stain", "FLOAT", "POINT")
        PUDDLE["stain"] = {"t": st.get("t", d["t_hit"]), "r_end": st.get("r_end", 0.07), "fall_by": st.get("fall_by", 1.6), "r0": d["r"]}
    r, th, v = d["r"], d["t_hit"], d["v_hit"]

    def src(t):
        tp = th - t                                   # time before the hit
        if tp > 0:
            h = v * tp - 0.5 * G_ACC * tp * tp        # height of the bottom of the drop above the surface
            if tp > 0.2 or h > 0.30:
                return [], []
            st_ = 1.0 + 0.35 * min(1.0, v / 2.0)      # slightly teardrop-shaped in flight
            return [], [(0, 0, h + r * st_, r, (1.0, 1.0, st_))]
        tau = -tp
        if tau < 0.05:                                # the drop sinks into the surface and is gone
            k = 1 - tau / 0.05
            return [], [(0, 0, r * k * 0.8, r * (0.4 + 0.6 * k), (1.2, 1.2, 0.7))]
        return [], []
    SLIME_SOURCES.append(src)
    return lambda t: Vector((0, 0, 0))


def slime_frame_update(scene, *a):
    t = (scene.frame_current - 1) / FPS + T0
    for h in FRAME_HOOKS:
        h(t)


# ====================================================================== lime10-bench additions (2026-10-18)
# subject can330 (standard 330 ml can, 3 sections with straight cuts), set studio_pack (packshots), condensation material.
# can3 and everything above are untouched.
CAN330 = {"h": 0.1152, "r": 0.0331, "lid_r": 0.027, "split": [0.038, 0.074], "wall": 0.0005}
LIME_FIELD = "#6AA71C"


def add_condensation(nt, bsdf, amount=1.0, scale=1.0):
    """Droplets on a Principled BSDF: fine droplets (Voronoi), a few big beads, a couple of vertical runs; bump + low roughness."""
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    cl = N.new("ShaderNodeTexNoise"); cl.inputs["Scale"].default_value = 20 * scale; cl.inputs["Detail"].default_value = 3
    nt.links.new(tc.outputs["Object"], cl.inputs["Vector"])      # low-frequency noise: drops come in clusters and clear patches
    clr = N.new("ShaderNodeMapRange"); clr.inputs["From Min"].default_value = 0.35; clr.inputs["From Max"].default_value = 0.65
    clr.inputs["To Min"].default_value = 0.15; clr.inputs["To Max"].default_value = 2.2; clr.clamp = True
    nt.links.new(cl.outputs["Fac"], clr.inputs["Value"])
    def vor(scale_, thr_lo, thr_hi, gate):
        v = N.new("ShaderNodeTexVoronoi"); v.feature = "F1"; v.inputs["Scale"].default_value = scale_ * scale
        v.inputs["Randomness"].default_value = 1.0; nt.links.new(tc.outputs["Object"], v.inputs["Vector"])
        sp = N.new("ShaderNodeSeparateColor"); nt.links.new(v.outputs["Color"], sp.inputs["Color"])
        rs = N.new("ShaderNodeMath"); rs.operation = "MULTIPLY_ADD"; rs.inputs[1].default_value = 1.25; rs.inputs[2].default_value = 0.35
        nt.links.new(sp.outputs["Green"], rs.inputs[0])            # per-drop size 0.35x .. 1.6x
        dn = N.new("ShaderNodeMath"); dn.operation = "DIVIDE"; nt.links.new(v.outputs["Distance"], dn.inputs[0]); nt.links.new(rs.outputs[0], dn.inputs[1])
        mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = thr_hi; mr.inputs["From Max"].default_value = thr_lo
        mr.inputs["To Min"].default_value = 0.0; mr.inputs["To Max"].default_value = 1.0; mr.clamp = True
        nt.links.new(dn.outputs[0], mr.inputs["Value"])
        gt = N.new("ShaderNodeMath"); gt.operation = "MULTIPLY"; gt.inputs[1].default_value = gate; nt.links.new(clr.outputs[0], gt.inputs[0])
        g = N.new("ShaderNodeMath"); g.operation = "LESS_THAN"
        nt.links.new(sp.outputs["Red"], g.inputs[0]); nt.links.new(gt.outputs[0], g.inputs[1])
        m = N.new("ShaderNodeMath"); m.operation = "MULTIPLY"
        nt.links.new(mr.outputs[0], m.inputs[0]); nt.links.new(g.outputs[0], m.inputs[1])
        return m
    fine = vor(900, 0.16, 0.30, 0.55 * amount)
    beads = vor(110, 0.20, 0.30, 0.10 * amount)
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.0, 1.0, 0.05)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 260 * scale; nz.inputs["Detail"].default_value = 2
    nt.links.new(mp.outputs[0], nz.inputs["Vector"])
    rr = N.new("ShaderNodeMapRange"); rr.inputs["From Min"].default_value = 0.66 - 0.05 * amount; rr.inputs["From Max"].default_value = 0.70
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    mx1 = N.new("ShaderNodeMath"); mx1.operation = "MAXIMUM"; nt.links.new(fine.outputs[0], mx1.inputs[0]); nt.links.new(beads.outputs[0], mx1.inputs[1])
    mx2 = N.new("ShaderNodeMath"); mx2.operation = "MAXIMUM"; mx2.use_clamp = True
    nt.links.new(mx1.outputs[0], mx2.inputs[0]); nt.links.new(rr.outputs[0], mx2.inputs[1])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.8; bp.inputs["Distance"].default_value = 0.0004
    nt.links.new(mx2.outputs[0], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    rg = N.new("ShaderNodeMapRange"); rg.inputs["To Min"].default_value = bsdf.inputs["Roughness"].default_value; rg.inputs["To Max"].default_value = 0.04
    nt.links.new(mx2.outputs[0], rg.inputs["Value"]); nt.links.new(rg.outputs[0], bsdf.inputs["Roughness"])
    return mx2


def make_materials330(cond=1.0, sp=None):
    M = {}
    sp = sp or (P.get("subject_params") or {})
    if CLAYKEY:   # flat field colour + the real label texture, neutral and matte
        fc = hexlin(sp.get("field", LIME_FIELD)); p = mat("pv_print330k", fc, 0.6); M["print"] = p
        lab = mat("pv_label330k", fc, 0.6); nt = lab.node_tree; b = _principled(lab)
        path = os.path.join(os.environ.get("PREVIS_ASSETS", "/pvlib/assets"), sp.get("label", "grawwww_lime330_label.png"))
        if os.path.exists(path):
            im = bpy.data.images.load(path); im.colorspace_settings.name = "sRGB"
            tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = im; tx.interpolation = "Cubic"; tx.extension = "EXTEND"
            nt.links.new(tx.outputs["Color"], b.inputs["Base Color"])
        M["label"] = lab; M["alu"] = mat("pv_alu330k", (0.72, 0.72, 0.74), 0.5); M["inside"] = mat("pv_inside330k", (0.6, 0.6, 0.62), 0.6)
        M["soda"] = mat("pv_soda330k", (0.86, 0.94, 0.63), 0.5)
        return M
    if not LOOKDEV:
        c = mat("pv_clay", (0.55, 0.55, 0.55), 0.8)
        for k in ("print", "label", "alu", "soda", "inside"):
            M[k] = c
        return M
    lime = hexlin(sp.get("field", LIME_FIELD))
    p = mat("pv_print330", lime, 0.34); b = _principled(p); b.inputs["Metallic"].default_value = 0.4
    b.inputs["Specular IOR Level"].default_value = 0.6
    if cond:
        add_condensation(p.node_tree, b, cond)
    M["print"] = p
    lab = mat("pv_label330", lime, 0.34); nt = lab.node_tree; b = _principled(lab); b.inputs["Metallic"].default_value = 0.4
    path = os.path.join(os.environ.get("PREVIS_ASSETS", "/pvlib/assets"), sp.get("label", "grawwww_lime330_label.png"))
    if os.path.exists(path):
        im = bpy.data.images.load(path); im.colorspace_settings.name = "sRGB"
        tx = nt.nodes.new("ShaderNodeTexImage"); tx.image = im; tx.interpolation = "Cubic"; tx.extension = "EXTEND"
        nt.links.new(tx.outputs["Color"], b.inputs["Base Color"]); print("PREVIS_LABEL", path, im.size[:], flush=True)
    else:
        print("PREVIS_LABEL_MISSING", path, flush=True)
    if cond:
        add_condensation(nt, b, cond)
    M["label"] = lab
    al = mat("pv_alu330", (0.50, 0.51, 0.54), 0.44); nt = al.node_tree; b = _principled(al)
    b.inputs["Metallic"].default_value = 1.0; b.inputs["Anisotropic"].default_value = 0.8
    tg = nt.nodes.new("ShaderNodeTangent"); tg.direction_type = "RADIAL"; tg.axis = "Z"; nt.links.new(tg.outputs["Tangent"], b.inputs["Tangent"])
    M["alu"] = al
    ins = mat("pv_inside330", (0.6, 0.62, 0.66), 0.4); _principled(ins).inputs["Metallic"].default_value = 1.0; M["inside"] = ins
    sd = mat("pv_soda", hexlin("#DCEFA0"), 0.12); b = _principled(sd)
    b.inputs["Roughness"].default_value = 0.35; b.inputs["Coat Weight"].default_value = 0.4; b.inputs["Coat Roughness"].default_value = 0.1
    b.inputs["Emission Color"].default_value = (*hexlin("#DCEFA0"), 1); b.inputs["Emission Strength"].default_value = 0.45
    M["soda"] = sd
    return M


def can330_rows(c):
    """(r, z, matabove) in mm, bottom centre outward and up. mat: 0 lime print, 1 label, 2 alu."""
    rb, rn, H = c["r"] * 1000, c["lid_r"] * 1000, c["h"] * 1000
    R = [(0.3, 7.2, 2), (7, 6.8, 2), (13, 5.4, 2), (18, 3.4, 2), (22.5, 1.6, 2), (25.5, 0.3, 2), (26.8, 0.0, 2),
         (28.4, 0.4, 2), (30.6, 1.5, 2), (32.2, 3.3, 0), (rb - 0.1, 5.8, 0), (rb, 8.0, 1)]
    for z in range(14, 98, 6):
        R.append((rb, float(z), 1))
    R.append((rb, 98.0, 0))
    n = 8
    for k in range(1, n + 1):
        u = k / n; R.append((rn + (rb - rn) * (0.5 + 0.5 * math.cos(math.pi * u)), 98.0 + u * 10.8, 0))
    R += [(rn, 111.0, 2)] if False else []
    R.append((rn, 111.4, 2))
    for r, z in ((rn + 0.5, 113.0), (rn + 0.9, 114.4), (rn + 0.4, H), (rn - 0.5, H), (rn - 1.6, H - 1.2), (rn - 2.6, H - 2.9),
                 (rn - 3.4, H - 3.9), (rn - 5, 111.2), (rn - 12, 111.1), (rn - 20, 111.1), (0.3, 111.1)):
        R.append((r, z, 2))
    return R


def clip_rows(R, zlo, zhi):
    out = []
    for i, (r, z, m) in enumerate(R):
        if zlo - 1e-9 <= z <= zhi + 1e-9:
            out.append((r, z, m))
        if i + 1 < len(R):
            r2, z2, _ = R[i + 1]
            if z < zlo < z2:
                u = (zlo - z) / (z2 - z); out.append((r + (r2 - r) * u, zlo, m))
            if z < zhi < z2:
                u = (zhi - z) / (z2 - z); out.append((r + (r2 - r) * u, zhi, m)); break
    return out


CAN_FLESH = "#D6E58C"   # pale lime flesh of the cut faces (between the lime halves' #C5E07A and the reference's pale yellow-green)


def flesh_mat330(MM):
    """`can.cut_face: flesh` (2026-10-19, founder: the can is sliced like the fruit): the cut face is solid pale lime flesh, flush with the
    print, no metal. Clay: the clay grey; clay_key: flat flesh colour; lookdev: juicy flesh with faint radial segments, a thin paler pith
    ring at the edge, pulp noise, subsurface and a wet coat. Created lazily, so `soda` scenes keep exactly their old datablocks."""
    if "flesh" in MM:
        return MM["flesh"]
    fc = hexlin(CAN_FLESH)
    if not (LOOKDEV or CLAYKEY):   # clay: the clay grey with a faint self-light, so a face turned away from the key reads as a solid face, never a hole
        m = mat("pv_flesh330c", (0.55, 0.55, 0.55), 0.8); b = _principled(m)
        b.inputs["Emission Color"].default_value = (0.55, 0.55, 0.55, 1); b.inputs["Emission Strength"].default_value = 0.35
        MM["flesh"] = m; return m
    if CLAYKEY:
        m = mat("pv_flesh330k", fc, 0.5); b = _principled(m)
        b.inputs["Emission Color"].default_value = (*fc, 1); b.inputs["Emission Strength"].default_value = 0.25
        MM["flesh"] = m; return m
    m = mat("pv_flesh330", fc, 0.3); nt = m.node_tree; N_ = nt.nodes; L_ = nt.links; b = _principled(m)
    b.inputs["Subsurface Weight"].default_value = 0.35; b.inputs["Subsurface Radius"].default_value = (0.9, 1.0, 0.45)
    b.inputs["Subsurface Scale"].default_value = 0.004
    b.inputs["Coat Weight"].default_value = 0.6; b.inputs["Coat Roughness"].default_value = 0.08
    def math_(op, a=None, b_=None, v1=None):
        n = N_.new("ShaderNodeMath"); n.operation = op
        if v1 is not None:
            n.inputs[1].default_value = v1
        if a is not None:
            L_.new(a, n.inputs[0])
        if b_ is not None:
            L_.new(b_, n.inputs[1])
        return n.outputs[0]
    tc = N_.new("ShaderNodeTexCoord"); sep = N_.new("ShaderNodeSeparateXYZ"); L_.new(tc.outputs["Object"], sep.inputs[0])
    ang = math_("ARCTAN2", sep.outputs["Y"], sep.outputs["X"])                       # polar angle in the disc plane
    mem = math_("POWER", math_("ABSOLUTE", math_("COSINE", math_("MULTIPLY", ang, v1=5.0))), v1=40.0)   # 10 thin membranes
    rad = math_("DIVIDE", math_("SQRT", math_("ADD", math_("MULTIPLY", sep.outputs["X"], sep.outputs["X"]),
                                              math_("MULTIPLY", sep.outputs["Y"], sep.outputs["Y"]))), v1=CAN330["r"])
    pale = math_("MAXIMUM", math_("MAXIMUM", math_("GREATER_THAN", rad, v1=0.94), math_("LESS_THAN", rad, v1=0.10)),
                 math_("MULTIPLY", mem, v1=0.5))                                       # pith ring, core, membranes
    nz = N_.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 900.0; nz.inputs["Detail"].default_value = 4.0
    L_.new(tc.outputs["Object"], nz.inputs["Vector"])
    c0 = N_.new("ShaderNodeMix"); c0.data_type = "RGBA"; c0.inputs["A"].default_value = (*[v * 0.82 for v in fc], 1); c0.inputs["B"].default_value = (*fc, 1)
    L_.new(nz.outputs["Fac"], c0.inputs["Factor"])
    c1 = N_.new("ShaderNodeMix"); c1.data_type = "RGBA"; c1.inputs["B"].default_value = (*[min(1.0, v * 1.22 + 0.04) for v in fc], 1)
    L_.new(c0.outputs["Result"], c1.inputs["A"]); L_.new(pale, c1.inputs["Factor"]); L_.new(c1.outputs["Result"], b.inputs["Base Color"])
    bp = N_.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.25; bp.inputs["Distance"].default_value = 0.0003
    L_.new(nz.outputs["Fac"], bp.inputs["Height"]); L_.new(bp.outputs["Normal"], b.inputs["Normal"])
    MM["flesh"] = m
    return m


def build_part330(kind, c, MM, N=360):
    s0, s1 = c["split"][0] * 1000, c["split"][1] * 1000; H = c["h"] * 1000
    zlo, zhi = {"bot": (0.0, s0), "mid": (s0, s1), "top": (s1, H), "all": (0.0, H)}[kind]
    rows = clip_rows(can330_rows(c), zlo, zhi)
    th = np.linspace(-np.pi, np.pi, N + 1)
    V = np.array([np.stack([r * np.sin(th), -r * np.cos(th), np.full_like(th, z - zlo)], -1) / 1000.0 for r, z, m in rows])[:, :N]
    nR = len(rows); idx = np.arange(nR * N).reshape(nR, N); faces, mats, uvs = [], [], []
    u = 0.5 + th / (2 * np.pi)
    vv = [min(max((z - 8.0) / 90.0, 0), 1) for r, z, m in rows]
    # 2026-10-19 angled cuts (`can.cut_tilt: [deg_cut1, deg_cut2]`, flesh faces only): each cut is a plane through the nominal split height at
    # the label FRONT (theta 0, so the words keep their sections) rising toward the back by tan(deg) (negative = falling): z(y) = s + tan(deg) (r + y).
    # The straight wall (z 8-98 mm) of each section is remapped column by column between its two cut planes; the artwork follows the true z.
    ct = c.get("cut_tilt") if (kind != "all" and c.get("cut_face", "soda") == "flesh") else None
    if ct and any(ct):
        rb_ = c["r"] * 1000; zc = [s0 + math.tan(math.radians(ct[0])) * rb_ * (1 - np.cos(th)), s1 + math.tan(math.radians(ct[1])) * rb_ * (1 - np.cos(th))]
        Z = np.array([[z] * (N + 1) for r, z, m in rows], dtype=float)
        if kind == "bot":
            Zn = np.where(Z >= 8.0, 8.0 + (Z - 8.0) * (zc[0] - 8.0) / (s0 - 8.0), Z)
        elif kind == "mid":
            Zn = zc[0] + (Z - s0) * (zc[1] - zc[0]) / (s1 - s0)
        else:
            Zn = np.where(Z <= 98.0, zc[1] + (Z - s1) * (98.0 - zc[1]) / (98.0 - s1), Z)
        V[:, :, 2] = (Zn[:, :N] - zlo) / 1000.0
        VV = np.clip((Zn - 8.0) / 90.0, 0, 1)
        for i in range(nR - 1):
            a, b = idx[i], idx[i + 1]; faces.append(np.stack([a, np.roll(a, -1), np.roll(b, -1), b], -1)); mats += [rows[i][2]] * N
            for j in range(N):
                uvs += [(u[j], VV[i, j]), (u[j + 1], VV[i, j + 1]), (u[j + 1], VV[i + 1, j + 1]), (u[j], VV[i + 1, j])]
    else:
        ct = None
    for i in range(nR - 1 if ct is None else 0):
        a, b = idx[i], idx[i + 1]; faces.append(np.stack([a, np.roll(a, -1), np.roll(b, -1), b], -1)); mats += [rows[i][2]] * N
        for j in range(N):
            uvs += [(u[j], vv[i]), (u[j + 1], vv[i]), (u[j + 1], vv[i + 1]), (u[j], vv[i + 1])]
    faces = np.concatenate(faces)
    me = bpy.data.meshes.new("c330_" + kind); me.from_pydata(V.reshape(-1, 3).tolist(), [], faces.tolist()); me.update()
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(uvs, dtype=np.float32).ravel())
    me.polygons.foreach_set("material_index", np.array(mats, dtype=np.int32))
    for k in ("print", "label", "alu", "soda", "soda"):
        me.materials.append(MM[k])
    for _ in range(5):
        me.materials.append(MM["inside"])
    ob = bpy.data.objects.new("c330_" + kind, me); sc.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40)); ob.select_set(False)
    if kind != "all" and c.get("cut_face", "soda") == "flesh":   # sliced like the fruit: no shell, no metal rim; flush flesh caps on the cut ends
        hp = (zhi - zlo) / 1000.0; fm = flesh_mat330(MM); dome = c.get("flesh_dome", 0.0004)   # the flesh sits a hair proud at the centre
        def cap(zl, rc, up, tilt_deg=0.0):
            n_ = N; ang = np.linspace(-np.pi, np.pi, n_ + 1)[:n_]; s_ = 1.0 if up else -1.0   # same angles as the wall: the outer ring meets it exactly
            tz_ = math.tan(math.radians(tilt_deg)); pz = lambda y_: zl + tz_ * (rc + y_)   # the cut plane (flat when tilt_deg is 0)
            vs = [(0.0, 0.0, pz(0.0) + s_ * dome)]
            for ring_, f_ in ((0.55, 0.6), (1.0, 0.0)):   # the inner ring carries most of the dome, the outer ring is the wall's edge
                vs += [(rc * ring_ * math.sin(a), -rc * ring_ * math.cos(a), pz(-rc * ring_ * math.cos(a)) + s_ * dome * f_) for a in ang]
            fs = []
            for i in range(n_):
                j = (i + 1) % n_; a0, a1, b0, b1 = 1 + i, 1 + j, 1 + n_ + i, 1 + n_ + j
                fs += [(0, a0, a1), (a0, b0, b1, a1)]
            if not up:
                fs = [tuple(reversed(f)) for f in fs]
            d = bpy.data.meshes.new("cut"); d.from_pydata(vs, [], fs); d.update(); d.materials.append(fm)
            o = bpy.data.objects.new("cut_face", d); sc.collection.objects.link(o); o.parent = ob
            d.polygons.foreach_set("use_smooth", [True] * len(d.polygons))
        ct_ = ct or (0.0, 0.0)
        if kind in ("bot", "mid"):
            cap(hp, rows[-1][0] / 1000.0, True, ct_[0 if kind == "bot" else 1])
        if kind in ("mid", "top"):
            cap(0.0, rows[0][0] / 1000.0, False, ct_[0 if kind == "mid" else 1])
        return ob, hp, rows
    if kind != "all":   # a seamless can is one closed surface: no shell, no cut faces
        so = ob.modifiers.new("shell", "SOLIDIFY"); so.thickness = c["wall"]; so.offset = -1.0; so.use_even_offset = True
        so.use_rim = True; so.material_offset = 5; so.material_offset_rim = 5
    hp = (zhi - zlo) / 1000.0
    # solid cut faces (pale soda discs) at the open ends
    rd = c["r"] - c["wall"] - 0.0002
    def disc(zl, up):
        d = bpy.data.meshes.new("cut"); ang = np.linspace(0, 2 * np.pi, 96, endpoint=False)
        vs = [(0, 0, zl)] + [(rd * math.cos(a), rd * math.sin(a), zl) for a in ang]
        fs = [(0, 1 + i, 1 + (i + 1) % 96) if up else (0, 1 + (i + 1) % 96, 1 + i) for i in range(96)]
        d.from_pydata(vs, [], fs); d.update(); d.materials.append(MM["soda"]); d.polygons.foreach_set("use_smooth", [False] * len(d.polygons))
        o = bpy.data.objects.new("cut_face", d); sc.collection.objects.link(o); o.parent = ob
    if kind in ("bot", "mid"):
        disc(hp - 0.0002, True)
    if kind in ("mid", "top"):
        disc(0.0002, False)
    return ob, hp, rows


def build_tab330(top, c, origin=None):
    zl = 111.1 / 1000 - (c["split"][1] if origin is None else origin)
    def add(op, name, **kw):
        op(**kw); o = bpy.context.object; o.name = name; o.data.materials.append(LIME_MM["alu"]); o.parent = top; return o
    pl = add(bpy.ops.mesh.primitive_cube_add, "tab_plate", location=(0.004, 0, zl + 0.0007), size=1)
    pl.scale = (0.0085, 0.0040, 0.0005); b = pl.modifiers.new("b", "BEVEL"); b.width = 0.0004; b.segments = 3
    rg = add(bpy.ops.mesh.primitive_torus_add, "tab_ring", location=(-0.0055, 0, zl + 0.0007), major_radius=0.0042, minor_radius=0.0010,
             major_segments=40, minor_segments=10); rg.scale = (1.35, 1.0, 0.6)
    rv = add(bpy.ops.mesh.primitive_cylinder_add, "tab_rivet", location=(0.0085, 0, zl + 0.0009), radius=0.0016, depth=0.0008)
    for o in (pl, rg, rv):
        bpy.context.view_layer.objects.active = o; o.select_set(True); bpy.ops.object.shade_smooth(); o.select_set(False)
    return [pl, rg, rv]


LIME_MM = None


def subject_can330(sp):
    global LIME_MM
    c = {**CAN330, **sp.get("can", {})}; s0, s1 = c["split"]
    LIME_MM = make_materials330(sp.get("condensation", 1.0), sp)
    nom = {"bot": 0.0, "mid": s0, "top": s1}
    parts, hp = {}, {}
    if c.get("seamless"):   # one continuous body and label (whole-can packshots, s3/s4): a single part called "bot"
        nom = {"bot": 0.0}; parts["bot"], hp["bot"], _ = build_part330("all", c, LIME_MM); build_tab330(parts["bot"], c, 0.0)
    else:
        for k in ("bot", "mid", "top"):
            parts[k], hp[k], _ = build_part330(k, c, LIME_MM)
        build_tab330(parts["top"], c)
    ALL, sf = None, c.get("seam_from")
    if sf is not None and not c.get("seamless"):   # spec PV5: a seamless twin of the stack, shown until seam_from, then the three sections
        ALL, _, _ = build_part330("all", c, LIME_MM); build_tab330(ALL, c, 0.0)
    asm = bool(sp.get("assembled"))
    if asm:
        bk = sp.get("body", [{"t": 0, "z": 0.0}])
        zf = {k: (lambda t, k=k, f=Curve(bk, "z"): f(t) + nom[k]) for k in parts}
        tf = {k: Curve(bk, "tilt") for k in parts}; af = {k: Curve(bk, "a") for k in parts}
        bxc, brc, bzc = Curve(bk, "x"), Curve(bk, "roll"), Curve(bk, "z")
    else:
        pk = sp.get("parts", {}); zf, tf, af = {}, {}, {}
        for k in parts:
            keys = pk.get(k, [{"t": 0, "z": nom[k], "tilt": 0, "a": 0}])
            zf[k], tf[k], af[k] = Curve(keys, "z"), Curve(keys, "tilt"), Curve(keys, "a")
    # 2026-10-19 sliced sections: optional per-section `roll` (picture plane about Y, + = top to screen left) and `x` (lateral offset, m),
    # pivot = the section's centre. Only when a part key carries them, so older params keep their exact transforms.
    xr = (not asm) and any(("roll" in kk or "x" in kk) for v in (sp.get("parts") or {}).values() for kk in v)
    if xr:
        rf_ = {k: Curve(pk.get(k, [{"t": 0}]), "roll") for k in parts}; xf_ = {k: Curve(pk.get(k, [{"t": 0}]), "x") for k in parts}
    state = lambda k, t: (zf[k](t), tf[k](t), af[k](t))
    pg_roll = Curve(sp["parts_group"], "roll") if (sp.get("parts_group") and not asm) else None
    pg_dz, pg_x = ((Curve(sp["parts_group"], "dz"), Curve(sp["parts_group"], "x")) if pg_roll is not None else (None, None))
    _eul = {}

    def _vis(ob, on, f):
        for o_ in [ob] + list(ob.children):
            o_.hide_render = not on; o_.hide_viewport = not on
            o_.keyframe_insert("hide_render", frame=f); o_.keyframe_insert("hide_viewport", frame=f)
    for f in range(1, N + 1):
        t = (f - 1) / FPS + T0
        if asm:   # one rigid body: x, z, roll (in the image plane, + = top to screen left), tilt about X, yaw a; pivot = the can's centre
            tl_, a_ = math.radians(tf["bot"](t)), math.radians(af["bot"](t)); rl_ = -math.radians(brc(t))
            Rm = Euler((tl_, rl_, a_), "ZXY").to_matrix(); cen = Vector((bxc(t), 0.0, bzc(t) + c["h"] / 2))
            for k, ob in parts.items():
                ob.rotation_mode = "ZXY"; ob.rotation_euler = (tl_, rl_, a_)
                ob.location = cen + Rm @ Vector((0, 0, nom[k] - c["h"] / 2))
                ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
            continue
        if pg_roll is not None:   # parts_group: the whole stack rolls rigidly in the image plane about its centre (+ = top to screen left); dz lifts, x shifts
            dz_ = pg_dz(t)
            zs_ = [zf[k](t) + dz_ for k in parts]; zt_ = zf["top"](t) + dz_ + hp["top"] if "top" in parts else max(zs_)
            piv = Vector((0.0, 0.0, (min(zs_) + zt_) / 2)); Rr = Euler((0, -math.radians(pg_roll(t)), 0), "XYZ").to_matrix()
        for k, ob in parts.items():
            z, tilt, a = state(k, t); cc = hp[k] / 2; th_ = math.radians(tilt)
            if pg_roll is not None:
                z = z + pg_dz(t)
            ob.rotation_mode = "ZXY"; ob.rotation_euler = (th_, 0, math.radians(a))
            ob.location = (0, cc * math.sin(th_), z + cc * (1 - math.cos(th_)))
            if xr:
                rl_ = -math.radians(rf_[k](t)); ob.rotation_euler = (th_, rl_, math.radians(a))
                Cv = Vector((0.0, 0.0, cc)); ob.location = Vector((xf_[k](t), 0.0, z)) + Cv - Euler((th_, rl_, math.radians(a)), "ZXY").to_matrix() @ Cv
            if pg_roll is not None:
                Rp = Euler((th_, (-math.radians(rf_[k](t)) if xr else 0), math.radians(a)), "ZXY").to_matrix()
                ob.location = piv + Rr @ (Vector(ob.location) - piv) + Vector((pg_x(t), 0.0, 0.0))
                ob.rotation_euler = (Rr @ Rp).to_euler("ZXY", _eul.get(k, Euler((0, 0, 0), "ZXY"))); _eul[k] = Euler(ob.rotation_euler, "ZXY")
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
        if ALL is not None:
            b_ = parts["bot"]; ALL.rotation_mode = "ZXY"; ALL.location = b_.location.copy(); ALL.rotation_euler = b_.rotation_euler.copy()
            ALL.keyframe_insert("location", frame=f); ALL.keyframe_insert("rotation_euler", frame=f)
            whole = t < sf
            _vis(ALL, whole, f)
            for ob in parts.values():
                _vis(ob, not whole, f)
    if sp.get("water"):
        W = sp["water"]; px, py, zs = MEADOW.get("puddle0", (0.0, 0.0, -0.004))
        slime_init(sp.get("res", 0.0012), 0.0015, cap_p=3500)
        for m_ in (MB_P, MB_S, MB_D):
            m_.o.location = (px, py, zs)
        rnd = random.Random(P.get("seed", 7) + 11); ctx = {"c": {"r": c["r"], "tooth_h": 0.0, "teeth": 3}}
        if W.get("burst"):   # clear-water crown around the can emerging from the puddle (same generators as lime_drop)
            cr_ = {"wall_r": 0.0030, "n": 72, "m": 16, "lean": 0.04, **W["burst"]}
            if "t" not in cr_:
                cr_["t"] = cr_.pop("t0", 0.0)
            cr_["fall_by"] = cr_["t"] + cr_["fall_by"]      # duration after t
            add_crown(cr_, ctx, rnd)
        if W.get("droplets"):
            add_droplets({"clear": True, "T": (0.2, 0.34), "rad": (0.0013, 0.0032), "r0": (W.get("burst") or {}).get("r0", 0.04), **W["droplets"]}, ctx, rnd)
        add_ripples(W.get("ripples"))
        if W.get("streams_until"):   # water streaming off the sections while they rise
            sctx = dict(c=ctx["c"], nom=nom, hp=hp, asm=False, state=lambda k_, t_: (zf[k_](t_), af[k_](t_)),
                        rfun={k_: (lambda zl, rr_=c["r"]: rr_) for k_ in parts})
            for k_ in parts:
                for az_ in (-70, 20, 130):
                    add_drip({"part": k_, "az": az_, "t0": rnd.uniform(0.1, W["streams_until"])}, sctx, rnd)
    return lambda t: Vector((0, 0, 0))


def set_studio_pack():
    """Clean packshot studio: a flat light-grey backdrop (world), a big soft key front-left, a fill and a top light; the floor is a
    shadow catcher on a transparent film (the batch composites the render over the flat backdrop colour)."""
    S = P.get("set_params", {})
    bg = hexlin(S.get("bg", "#E6E6E3"))
    world(tuple(c_ * 0.55 for c_ in bg) if LOOKDEV else (0.4, 0.4, 0.4), S.get("world", 1.0))
    for name, loc, size, e in (("key", (-1.5, -1.9, 1.7), 2.4, S.get("key", 220)), ("fill", (1.8, -1.5, 0.7), 1.8, S.get("fill", 60)),
                               ("top", (0.0, -0.3, 2.0), 1.6, S.get("top", 50))):
        bpy.ops.object.light_add(type="AREA", location=loc); L = bpy.context.object; L.name = "L_" + name
        L.data.shape = "SQUARE"; L.data.size = size; L.data.energy = e if LOOKDEV else e * 0.1
        L.rotation_euler = (Vector((0, 0, S.get("aim_z", 0.07))) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, S.get("floor_z", 0.0))); fl = bpy.context.object; fl.name = "floor"
    fl.data.materials.append(mat("pv_floor", (0.8, 0.8, 0.8), 0.7))
    if S.get("transparent", True) and LOOKDEV:
        fl.is_shadow_catcher = True; sc.render.film_transparent = True


 # ====================================================================== lime10-bench: meadow set, lime_drop, fruit props
def hill_height(x, y, seed):
    rr_ = np.hypot(x, y); ph = [seed * 1.7, seed * 2.9, seed * 0.7, seed * 4.1]
    h = (1.6 * np.sin(0.11 * x + ph[0]) * np.cos(0.09 * y + ph[1]) + 0.9 * np.sin(0.05 * x - 0.07 * y + ph[2]) +
         0.35 * np.sin(0.31 * x + ph[3]) * np.sin(0.27 * y + ph[1]))
    mask = np.clip((rr_ - 2.5) / 30.0, 0, 1); mask = mask * mask * (3 - 2 * mask)
    return h * mask * 0.45 + 0.0012 * np.sin(9 * x) * np.sin(7 * y) * (1 - mask)    # fine turf bumps near the camera


def set_meadow():
    S = P.get("set_params", {}); g = S.get("ground", {}); seed = g.get("seed", 3)
    if LOOKDEV:
        world((0.30, 0.46, 0.80), 1.0)
    else:
        world((0.5, 0.5, 0.5), 1.0)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(52), 0, math.radians(-32))); sun_ = bpy.context.object
    sun_.data.energy = 3.0 if LOOKDEV else 1.5; sun_.data.angle = math.radians(8)
    puddles = S.get("puddles", [])
    # ground: a grid denser near the camera, rolling hills, dips under the puddles
    nn = 301; u = np.linspace(-1, 1, nn); L = 60.0
    xs = L * np.sign(u) * np.abs(u) ** 2.2
    ys = L * np.sign(u) * np.abs(u) ** 2.2
    X, Y = np.meshgrid(xs, ys, indexing="xy")
    Z = hill_height(X, Y, seed) if g.get("hills", True) else np.zeros_like(X)
    edges = []
    for k, pd in enumerate(puddles):   # irregular: true -> an organic, soft outline (never a circle or an oval)
        if pd.get("irregular"):
            rg = random.Random(seed * 31 + k * 17); ph = [rg.uniform(0, 6.28) for _ in range(5)]
            edges.append(lambda th, R=pd["r"], ph=ph: R * (1 + 0.13 * np.sin(2 * th + ph[0]) + 0.10 * np.sin(3 * th + ph[1]) + 0.07 * np.sin(5 * th + ph[2])
                                                           + 0.04 * np.sin(7 * th + ph[3]) + 0.025 * np.sin(11 * th + ph[4])))
        else:
            edges.append(None)
    for k, pd in enumerate(puddles):
        dx_, dy_ = X - pd["x"], Y - pd["y"]; dd = np.hypot(dx_, dy_)
        Rl = pd["r"] if edges[k] is None else edges[k](np.arctan2(dy_, dx_))
        Z = Z - 0.014 * (1 - np.clip((dd - Rl * 0.97) / (Rl * 0.35 + 0.02), 0, 1))
    idx = np.arange(nn * nn).reshape(nn, nn); faces = np.concatenate([np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)])
    me = bpy.data.meshes.new("meadow"); me.from_pydata(np.stack([X, Y, Z], -1).reshape(-1, 3).tolist(), [], faces.tolist()); me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    gm = mat("pv_turf", (0.16, 0.42, 0.06) if LOOKDEV else (0.35, 0.35, 0.35), 0.95)
    me.materials.append(gm); ob = bpy.data.objects.new("meadow", me); sc.collection.objects.link(ob)
    rnd = random.Random(seed)
    # shrubs and stones for depth cues
    sm = mat("pv_shrub", (0.05, 0.2, 0.04) if LOOKDEV else (0.45, 0.45, 0.45), 0.9)
    stm = mat("pv_stone", (0.3, 0.3, 0.28) if LOOKDEV else (0.6, 0.6, 0.6), 0.8)
    for i in range(70):
        ang = rnd.uniform(-1.2, 1.2) + math.pi / 2; dist = rnd.uniform(3.0, 42.0) if i > 8 else rnd.uniform(1.6, 3.0)
        x, y = dist * math.cos(ang), dist * math.sin(ang)
        if any(math.hypot(x - p["x"], y - p["y"]) < p["r"] + 0.3 for p in puddles):
            continue
        z0 = float(hill_height(np.array([x]), np.array([y]), seed)[0]); r_ = rnd.uniform(0.08, 0.22) * (1 + dist / 12)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r_, location=(x, y, z0 + r_ * 0.4), segments=16, ring_count=10)
        o = bpy.context.object; o.scale = (1.0, 1.0, 0.7 if i % 4 else 0.45); o.data.materials.append(stm if i % 4 == 0 else sm)
        bpy.ops.object.shade_smooth()
    # puddles: the first one is the active one (ripples, splash); the others are still discs
    for k, pd in enumerate(puddles):
        if k == 0:
            build_puddle(pd["r"], 0.01, edges[k]); po = bpy.data.objects["puddle"]; po.location = (pd["x"], pd["y"], -0.004)
            MEADOW["puddle0"] = (pd["x"], pd["y"], -0.004)
        else:
            ang = np.linspace(0, 2 * np.pi, 72, endpoint=False)
            Rf = (lambda a: pd["r"] * (1 + 0.04 * math.sin(3 * a + k))) if edges[k] is None else (lambda a: float(edges[k](np.array([a]))[0]))
            vs = [(pd["x"], pd["y"], -0.004)] + [(pd["x"] + Rf(a) * math.cos(a), pd["y"] + Rf(a) * math.sin(a), -0.004) for a in ang]
            fs = [(0, 1 + i, 1 + (i + 1) % 72) for i in range(72)]
            dm = bpy.data.meshes.new("puddle_s"); dm.from_pydata(vs, [], fs); dm.update(); dm.materials.append(MATS["puddle"])
            sc.collection.objects.link(bpy.data.objects.new("puddle_s%d" % k, dm))
    # foreground flowers: stem + head proxies
    fm = mat("pv_flower", (0.8, 0.12, 0.08) if LOOKDEV else (0.7, 0.7, 0.7), 0.6)
    for fl in S.get("flowers", []):
        for i in range(fl.get("n", 3)):
            x = fl["x"] + rnd.uniform(-0.05, 0.05); y = fl["y"] + rnd.uniform(-0.05, 0.05); h = fl["h"] * rnd.uniform(0.75, 1.1)
            z0 = float(hill_height(np.array([x]), np.array([y]), seed)[0])
            bpy.ops.mesh.primitive_cylinder_add(radius=0.0016, depth=h, location=(x, y, z0 + h / 2), vertices=8)
            bpy.context.object.data.materials.append(sm)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=fl["head_r"], location=(x, y, z0 + h), segments=16, ring_count=8)
            hd = bpy.context.object; hd.scale = (1.0, 1.0, 0.35); hd.data.materials.append(fm); bpy.ops.object.shade_smooth()


MEADOW = {}


def set_pastel_valley():
    """Stylised pastel valley (ref_05/06/07/09): one big smooth dome hill centre-back, gentle side hills, flat ground with a winding river.
    set_params {dome {x, y, r, h}, side_hills (true | false | {l|r: {x, y, rx, [ry], h}} absolute, a hill left out of the dict keeps its default), river {y, width, wind}}. Previs geometry; clay by default."""
    S = P.get("set_params", {}); dm = S.get("dome", {"x": 0.0, "y": 6.0, "r": 2.2}); rv = S.get("river")
    world((0.55, 0.7, 0.95) if LOOKDEV else (0.5, 0.5, 0.5), 1.0)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(-30))); sun_ = bpy.context.object
    sun_.data.energy = 3.0 if LOOKDEV else 1.5; sun_.data.angle = math.radians(8)
    gm = mat("pv_turf", (0.2, 0.5, 0.1) if LOOKDEV else (0.35, 0.35, 0.35), 0.95)
    bpy.ops.mesh.primitive_plane_add(size=160, location=(0, 40, 0)); bpy.context.object.data.materials.append(gm)
    def hill(x, y, rx, ry, h, name):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(x, y, -h * 0.35), segments=64, ring_count=32)
        o = bpy.context.object; o.name = name; o.scale = (rx, ry, h); o.data.materials.append(gm); bpy.ops.object.shade_smooth()
    hill(dm["x"], dm["y"], dm["r"], dm["r"], dm.get("h", dm["r"] * 0.55), "dome")
    if S.get("side_hills", True):
        sh = S["side_hills"] if isinstance(S.get("side_hills"), dict) else {}   # dict form: {l|r: {x, y, rx, ry, h}} absolute, per hill (fit to a still)
        for nm_, dx_, dy_, rx_, ry_, h_ in (("l", -7.5, -1.5, 4.5, 3.5, 1.1), ("r", 8.0, -2.0, 5.0, 3.5, 1.3)):
            q_ = sh.get(nm_)
            if q_:
                hill(q_["x"], q_["y"], q_["rx"], q_.get("ry", q_["rx"]), q_["h"], "hill_" + nm_)
            else:
                hill(dm["x"] + dx_, dm["y"] + dy_, rx_, ry_, h_, "hill_" + nm_)
    if rv:
        nn = 80; xs = np.linspace(-30, 30, nn); wd = rv.get("width", 0.6)
        yc = rv["y"] + rv.get("wind", 0.8) * np.sin(0.45 * xs); V = []
        for x_, y_ in zip(xs, yc):
            V += [(x_, y_ - wd / 2 * (1 + 0.3 * math.sin(0.9 * x_)), 0.004), (x_, y_ + wd / 2 * (1 + 0.3 * math.cos(0.7 * x_)), 0.004)]
        F = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(nn - 1)]
        me = bpy.data.meshes.new("river"); me.from_pydata(V, [], F); me.update(); me.materials.append(MATS["puddle"])
        sc.collection.objects.link(bpy.data.objects.new("river", me))


# ---------------------------------------------------------------- fruit
FRUIT = {"lime": dict(peel="#4C9A2A", flesh="#C5E07A", k=(1.0, 1.0, 0.97)), "lemon": dict(peel="#F2D12A", flesh="#F7E58F", k=(1.18, 0.94, 0.94))}


def hemi(kind, r, up, name):
    fd = FRUIT[kind]; rx, ry, rz = (r * q for q in fd["k"]); rings, seg = 14, 48
    V, F = [], []
    for i in range(rings + 1):
        th_ = (math.pi / 2) * i / rings
        for j in range(seg):
            ph_ = 2 * math.pi * j / seg
            V.append((rx * math.sin(th_) * math.cos(ph_), ry * math.sin(th_) * math.sin(ph_), rz * math.cos(th_)))
    for i in range(rings):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg
            F.append((a, a + seg, b + seg, b))
    V.append((0, 0, 0)); c = len(V) - 1; eq = rings * seg
    mats = [0] * len(F)
    for j in range(seg):
        F.append((c, eq + (j + 1) % seg, eq + j)); mats.append(1)
    if not up:
        V = [(x, y, -z) for x, y, z in V]; F = [tuple(reversed(f)) for f in F]
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], F); me.update()
    for k_, h_ in (("peel", 0), ("flesh", 1)):
        m = mat("pv_" + kind + k_, hexlin(fd[k_]) if (LOOKDEV or CLAYKEY) else (0.6, 0.6, 0.6), 0.35 if k_ == "peel" else 0.25); me.materials.append(m)
    me.polygons.foreach_set("material_index", np.array(mats, dtype=np.int32))
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True); bpy.ops.object.shade_smooth_by_angle(angle=math.radians(50)); ob.select_set(False)
    return ob


def berry_mesh(kind, r, name):
    seg, rings = 40, 24; V, F = [], []
    for i in range(rings + 1):
        th_ = math.pi * i / rings
        for j in range(seg):
            ph_ = 2 * math.pi * j / seg; rr_ = 1.0
            if kind == "raspberry":   # drupelet bumps, slightly tapered
                rr_ = 1.0 + 0.09 * (abs(math.sin(9 * th_) * math.sin(7 * ph_ + 3 * th_))) ** 0.6
                zs_ = 1.18
            else:                     # blueberry: round with a crown dimple at the top
                rr_ = 1.0 - 0.20 * max(0.0, 1 - th_ / 0.38) ** 1.5; zs_ = 0.96
            V.append((r * rr_ * math.sin(th_) * math.cos(ph_), r * rr_ * math.sin(th_) * math.sin(ph_), r * zs_ * rr_ * math.cos(th_)))
    for i in range(rings):
        for j in range(seg):
            a, b = i * seg + j, i * seg + (j + 1) % seg; F.append((a, a + seg, b + seg, b))
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], F); me.update()
    bm_ = mat("pv_" + kind, (0.75, 0.1, 0.2) if ((LOOKDEV or CLAYKEY) and kind == "raspberry") else ((0.1, 0.12, 0.3) if (LOOKDEV or CLAYKEY) else (0.6, 0.6, 0.6)), 0.4)
    if CLAYKEY and kind == "blueberry":   # keeps the push-through frames a readable dark indigo (never below Y 20)
        _bb = _principled(bm_); _bb.inputs["Emission Color"].default_value = (0.12, 0.14, 0.34, 1); _bb.inputs["Emission Strength"].default_value = 0.7
    me.materials.append(bm_)
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True); bpy.ops.object.shade_smooth(); ob.select_set(False)
    return ob


def build_props(props):
    for k, pr in enumerate(props):
        if pr.get("kind") in ("raspberry", "blueberry"):   # keys [{t, x, y, z}] + spin deg/s
            ob = berry_mesh(pr["kind"], pr["r"], f"berry{k}"); ks = pr["keys"]; cx, cy, cz = Curve(ks, "x"), Curve(ks, "y"), Curve(ks, "z")
            sp_ = pr.get("spin", 0.0)
            for f in range(1, N + 1):
                t = (f - 1) / FPS + T0
                ob.location = (cx(t), cy(t), cz(t)); ob.rotation_euler = (math.radians(0.6 * sp_ * t + 20 * k), 0, math.radians(sp_ * t))
                ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
            continue
        kind, r, x, y = pr.get("kind", "lime"), pr["r"], pr["x"], pr["y"]
        top, bot = hemi(kind, r, True, f"fruit{k}_top"), hemi(kind, r, False, f"fruit{k}_bot")
        sp_ = pr.get("split")
        if sp_:
            keys = sp_["keys"]; zc, gc, oc = Curve(keys, "z"), Curve(keys, "gap"), Curve(keys, "open_deg")
            xc, yc = Curve(keys, "x", x), Curve(keys, "y", y)   # spec PV6: x / y keys (default: the fixed x, y)
        else:
            zc, gc, oc = (lambda t, z=pr.get("z", r): z), (lambda t: 0.0), (lambda t: 0.0)
            xc, yc = (lambda t, v=x: v), (lambda t, v=y: v)
        tum = pr.get("tumble")   # {deg_s, until}: the whole fruit spins until `until`, an integer number of turns, then the cut plane is horizontal
        if tum:
            t_a = min(kk["t"] for kk in sp_["keys"]); tu = tum["until"]
            turns = round(tum["deg_s"] * (tu - t_a) / 360.0) or (1 if tum["deg_s"] > 0 else -1); th_end = turns * 360.0
        for f in range(1, N + 1):
            t = (f - 1) / FPS + T0; z, g_, o_ = zc(t), gc(t), math.radians(oc(t)); x, y = xc(t), yc(t)
            top.location = (x, y, z + g_ / 2); top.rotation_euler = (-o_, 0, 0)
            bot.location = (x, y, z - g_ / 2); bot.rotation_euler = (o_, 0, 0)
            if tum and t < tu:
                u_ = min(max((t - t_a) / (tu - t_a), 0.0), 1.0); ang = math.radians(th_end * (1 - (1 - u_) ** 2))
                for ob in (top, bot):
                    ob.rotation_euler = (ang, 0, -ang)
            for ob in (top, bot):
                ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)


# ---------------------------------------------------------------- subject lime_drop (clear-water splash proxy)
def subject_lime_drop(sp):
    """A whole lime falls into the first meadow puddle at t_hit with speed v_hit, plunges, bobs and floats; the water splash proxy is
    the crown / droplets / ripples generators with water proportions (thin beaded wall, small clear droplets). Timing and shape only."""
    S = sp.get("splash", {}); fr = sp.get("fruit", {"kind": "lime", "r": 0.029}); d = sp["drop"]; fl = sp.get("float", {})
    px, py, zs = MEADOW.get("puddle0", (0.0, 0.0, -0.004))
    slime_init(sp.get("res", 0.0012), S.get("res_puddle", 0.0015), cap_p=3500)
    for m_ in (MB_P, MB_S, MB_D):
        m_.o.location = (px, py, zs)
    rnd = random.Random(P.get("seed", 7) + 9)
    ctx = {"c": {"r": 0.03}}
    if S.get("crown"):
        cr_ = {"wall_r": 0.0030, "n": 72, "m": 16, "lean": 0.04, **S["crown"]}
        cr_["fall_by"] = cr_["t"] + cr_["fall_by"]      # water crowns: fall_by is a duration after t (lime10: 0.40 s after the hit)
        add_crown(cr_, ctx, rnd)
    if S.get("droplets"):
        add_droplets({"clear": True, "T": (0.2, 0.34), "rad": (0.0013, 0.0032), "r0": 0.035, **S["droplets"]}, ctx, rnd)
    add_ripples(S.get("ripples"))
    kind, r = fr.get("kind", "lime"), fr["r"]
    top, bot = hemi(kind, r, True, "lime_t"), hemi(kind, r, False, "lime_b")   # a whole fruit = two closed halves
    rz = r * FRUIT[kind]["k"][2]
    th, v = d["t_hit"], d["v_hit"]
    rest = zs + r * (1 - 2 * fl.get("sink", 0.65))
    keys = [{"t": th, "z": zs + rz}] + [{"t": k["t"], "z": rest + k["z"]} for k in fl.get("keys", [])]
    after = Curve(keys, "z")
    for f in range(1, N + 1):
        t = (f - 1) / FPS + T0; tp = th - t
        if tp > 0:
            hgt = v * tp - 0.5 * G_ACC * tp * tp; z = zs + rz + (hgt if tp <= v / G_ACC else 5.0)   # shown only on the way down from rest
        else:
            z = after(t)
        for ob in (top, bot):
            ob.location = (px + d.get("x", 0.0), py + d.get("y", 0.0), z); ob.rotation_euler = (0.5 * t, 0.2 * t, 0)
            ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_euler", frame=f)
            if fl.get("hide_after") is not None:   # spec PV7: the dropped lime goes under the collapsing crown and is hidden
                on_ = t <= fl["hide_after"]; ob.hide_render = not on_; ob.hide_viewport = not on_
                ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("hide_viewport", frame=f)
    return lambda t: Vector((0, 0, 0))


# ====================================================================== generic rig subject + stage set (2026-10-19: MUTE / REAL TIME tooling)
# A scene object written in animatic.yaml (`objects:`) instead of a Python builder: a tree of parts (empty pivots and primitive meshes) with keyed
# transforms in SPOT time, continuous spins, sines and generators (flurry, meshing wheels). pv_sequence.py compiles `segments[].builder: generic` +
# `objects: [names]` to  subjects: [{"subject": "rig", "role": "product"|"prop", "subject_params": {"id", "parts", "mask"}}]  and  set: "stage".
# Everything between the two pv_generic markers is pure Python (no bpy): vt.py selftest executes that slice on its own to check the geometry.
# ==== pv_generic begin ====
def g_ngon(r, n, a0=0.0):
    return [(r * math.cos(a0 + 2 * math.pi * i / n), r * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def g_extrude(outer, depth, inner=None):
    """Prism of the outline `outer` ((x, y) points, counter-clockwise, any simple polygon) between z = -depth/2 and +depth/2.
    With `inner` (same number of points, same winding) it is a ring. Returns (V, F), faces counter-clockwise seen from outside."""
    n, h = len(outer), depth / 2.0
    V = [(x, y, h) for x, y in outer] + [(x, y, -h) for x, y in outer]
    F = []
    if inner is None:
        F.append(tuple(range(n))); F.append(tuple(range(2 * n - 1, n - 1, -1)))
    else:
        assert len(inner) == n, "ring: inner and outer need the same number of points"
        V += [(x, y, h) for x, y in inner] + [(x, y, -h) for x, y in inner]
        for i in range(n):
            j = (i + 1) % n
            F.append((i, j, 2 * n + j, 2 * n + i)); F.append((3 * n + i, 3 * n + j, n + j, n + i))
            F.append((2 * n + j, 3 * n + j, 3 * n + i, 2 * n + i))                   # inner wall, normal toward the axis
    for i in range(n):
        j = (i + 1) % n
        F.append((i, n + i, n + j, j))                                                # outer wall, normal outward
    return V, F


def g_merge(*meshes):
    V, F = [], []
    for v, f in meshes:
        o = len(V); V += list(v); F += [tuple(i + o for i in fc) for fc in f]
    return V, F


def g_xf(mesh, loc=(0, 0, 0), rz_deg=0.0):
    V, F = mesh; c, s = math.cos(math.radians(rz_deg)), math.sin(math.radians(rz_deg))
    return [(x * c - y * s + loc[0], x * s + y * c + loc[1], z + loc[2]) for x, y, z in V], F


def g_box(sx, sy, sz):
    x, y, z = sx / 2.0, sy / 2.0, sz / 2.0
    V = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z), (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    return V, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def g_cyl(r, depth, seg=64, r2=None):
    """Cylinder (r2: cone frustum, r at the bottom, r2 at the top) along z, centred."""
    if r2 is None or abs(r2 - r) < 1e-12:
        return g_extrude(g_ngon(r, seg), depth)
    h = depth / 2.0; V = [(x, y, -h) for x, y in g_ngon(r, seg)] + [(x, y, h) for x, y in g_ngon(r2, seg)]
    F = [tuple(range(seg - 1, -1, -1)), tuple(range(seg, 2 * seg))]
    for i in range(seg):
        j = (i + 1) % seg; F.append((i, j, seg + j, seg + i))
    return V, F


def g_sphere(r, seg=32, rings=16):
    V = [(0, 0, r)]
    for k in range(1, rings):
        th = math.pi * k / rings
        V += [(r * math.sin(th) * math.cos(2 * math.pi * i / seg), r * math.sin(th) * math.sin(2 * math.pi * i / seg), r * math.cos(th)) for i in range(seg)]
    V.append((0, 0, -r)); F = []
    for i in range(seg):
        F.append((0, 1 + i, 1 + (i + 1) % seg))
    for k in range(rings - 2):
        for i in range(seg):
            a, b = 1 + k * seg + i, 1 + k * seg + (i + 1) % seg
            F.append((a, a + seg, b + seg, b))
    last = len(V) - 1
    for i in range(seg):
        F.append((last, 1 + (rings - 2) * seg + (i + 1) % seg, 1 + (rings - 2) * seg + i))
    return V, F


def g_torus(R, r, seg=48, rings=16):
    V = [((R + r * math.cos(2 * math.pi * j / rings)) * math.cos(2 * math.pi * i / seg), (R + r * math.cos(2 * math.pi * j / rings)) * math.sin(2 * math.pi * i / seg),
          r * math.sin(2 * math.pi * j / rings)) for i in range(seg) for j in range(rings)]
    F = []
    for i in range(seg):
        for j in range(rings):
            i2, j2 = (i + 1) % seg, (j + 1) % rings
            F.append((i * rings + j, i2 * rings + j, i2 * rings + j2, i * rings + j2))
    return V, F


def g_sector(r_out, r_in, a0, a1, depth, seg=32):
    """Arc band (r_in > 0) or pie slice (r_in == 0) from angle a0 to a1 (degrees, counter-clockwise from +x) in the XY plane, extruded along z."""
    ang = [math.radians(a0 + (a1 - a0) * i / seg) for i in range(seg + 1)]
    out = [(r_out * math.cos(a), r_out * math.sin(a)) for a in ang]
    inn = [(r_in * math.cos(a), r_in * math.sin(a)) for a in reversed(ang)] if r_in > 0 else [(0.0, 0.0)]
    pts = out + inn
    if a1 < a0:
        pts = pts[::-1]
    return g_extrude(pts, depth)


def g_wheel_outline(teeth, pitch_r, profile="spur"):
    """Outline of a toothed wheel: tooth k centred on angle 360 k / teeth. Module m = 2 pitch_r / teeth, addendum m, dedendum 1.25 m, slim
    straight-sided teeth (tip half width 0.08 pitch, root half width 0.23 pitch: a mating tooth fits the gap at every depth). profile "ratchet":
    asymmetric escape-wheel teeth. Returns (points, tip radius, root radius)."""
    m = 2.0 * pitch_r / teeth; r_tip, r_root = pitch_r + m, pitch_r - 1.25 * m; P_ = 2 * math.pi / teeth; pts = []
    for k in range(teeth):
        c = k * P_
        if profile == "ratchet":
            q = ((r_root, c - 0.30 * P_), (r_tip, c - 0.05 * P_), (r_tip, c + 0.03 * P_), (r_root, c + 0.30 * P_))
        else:
            q = ((r_root, c - 0.23 * P_), (r_tip, c - 0.08 * P_), (r_tip, c + 0.08 * P_), (r_root, c + 0.23 * P_))
        pts += [(rr * math.cos(a), rr * math.sin(a)) for rr, a in q]
    return pts, r_tip, r_root


def g_wheel(teeth=0, pitch_r=0.01, r=None, depth=0.002, rim_w=0.0, spokes=0, spoke_w=None, hub_r=0.0, profile="spur", seg=48):
    """Wheel in the XY plane, axis z. teeth > 0: toothed (see g_wheel_outline), else a smooth rim of radius r. rim_w > 0: a ring of that width
    (inside the root circle) with `spokes` arms and a hub, else a solid disc. Returns (V, F)."""
    if teeth > 0:
        out, r_tip, r_root = g_wheel_outline(teeth, pitch_r, profile)
    else:
        r_tip = r_root = r if r is not None else pitch_r; out = g_ngon(r_tip, seg)
    if rim_w <= 0:
        return g_extrude(out, depth)
    r_in = max(r_root - rim_w, 1e-5); inner = [(x * r_in / math.hypot(x, y), y * r_in / math.hypot(x, y)) for x, y in out]
    parts = [g_extrude(out, depth, inner)]
    sw = spoke_w if spoke_w is not None else rim_w * 0.6
    for k in range(spokes):
        a = 360.0 * k / spokes; L = r_in - hub_r * 0.5 + rim_w * 0.2
        parts.append(g_xf(g_box(L, sw, depth * 0.7), loc=(math.cos(math.radians(a)) * (hub_r * 0.5 + L / 2), math.sin(math.radians(a)) * (hub_r * 0.5 + L / 2), 0.0), rz_deg=a))
    if hub_r > 0:
        parts.append(g_cyl(hub_r, depth * 1.4, seg=24))
    return g_merge(*parts)


def g_shape(spec):
    """(V, F, smooth) of a part shape spec: {shape: box|cyl|sphere|torus|sector|wheel|poly|card, ...} sizes in metres."""
    k = spec["shape"]; z = lambda key, d=None: spec.get(key, d)
    if k == "box":
        return (*g_box(*z("size")), False)
    if k == "card":                    # a thin paper card w x h x t
        return (*g_box(z("w", 0.1), z("h", 0.14), z("t", 0.0006)), False)
    if k == "cyl":
        return (*g_cyl(z("r", 0.01), z("depth", 0.01), z("seg", 64), z("r2")), False)
    if k == "sphere":
        return (*g_sphere(z("r", 0.01), z("seg", 32), z("rings", 16)), True)
    if k == "torus":
        return (*g_torus(z("R", 0.02), z("r", 0.004), z("seg", 48), z("rings", 16)), True)
    if k == "sector":
        return (*g_sector(z("r_out", 0.05), z("r_in", 0.0), z("a0", 0), z("a1", 180), z("depth", 0.01), z("seg", 32)), False)
    if k == "poly":                    # an extruded outline: pts [[x, y], ...] counter-clockwise (the engine flips a clockwise one), depth
        pts = [tuple(p) for p in spec["pts"]]
        if sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) < 0:
            pts = pts[::-1]
        return (*g_extrude(pts, z("depth", 0.002)), False)
    if k == "wheel":
        return (*g_wheel(z("teeth", 0), z("pitch_r", 0.01), z("r"), z("depth", 0.002), z("rim_w", 0.0), z("spokes", 0), z("spoke_w"), z("hub_r", 0.0),
                         z("profile", "spur"), z("seg", 48)), False)
    raise ValueError(f"unknown shape {k!r}")


def g_volume(V, F):
    """Signed volume of a closed mesh (divergence theorem, fan triangulation): positive when the faces point outward."""
    vol = 0.0
    for f in F:
        a = V[f[0]]
        for i in range(1, len(f) - 1):
            b, c = V[f[i]], V[f[i + 1]]
            vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return vol


def g_open_edges(V, F):
    """Number of edges that do not belong to exactly two faces in opposite directions (0 = every shell is closed and consistently wound)."""
    cnt = {}
    for f in F:
        for i in range(len(f)):
            e = (f[i], f[(i + 1) % len(f)]); cnt[e] = cnt.get(e, 0) + 1
    return sum(1 for (a, b), c in cnt.items() if c != 1 or cnt.get((b, a), 0) != 1)


def g_mesh_with(a, b):
    """Spin of wheel `b` so that its teeth mesh with wheel `a` at every moment. a, b: {teeth, pitch_r, x, y, spin: {deg_s, phase, t0}, rz}. Wheels must be
    siblings. Contact direction phi = from a's centre to b's; a's angle is a_a(t) = rz + phase + deg_s (t - t0). Rolling without slipping gives
    deg_s_b = - deg_s_a z_a / z_b and, so that a tooth of a stands in a gap of b: phase_b = phi + 180 - (z_a / z_b)(a_a(t0) - phi) + 180 / z_b.
    Returns ({deg_s, phase, t0}, centre distance error as a fraction of the pitch-radii sum)."""
    za, zb = a["teeth"], b["teeth"]; sa = a["spin"]; t0 = sa.get("t0", 0.0)
    phi = math.degrees(math.atan2(b["y"] - a["y"], b["x"] - a["x"])); aa0 = a.get("rz", 0.0) + sa.get("phase", 0.0)
    dist = math.hypot(b["x"] - a["x"], b["y"] - a["y"]); want = a["pitch_r"] + b["pitch_r"]
    return ({"deg_s": -sa["deg_s"] * za / zb, "phase": phi + 180.0 - (za / zb) * (aa0 - phi) + 180.0 / zb, "t0": t0}, abs(dist - want) / want)


def g_wheel_polygon(teeth, pitch_r, angle_deg, cx, cy, profile="spur"):
    pts, _, _ = g_wheel_outline(teeth, pitch_r, profile); c, s = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def g_in_poly(pt, poly):
    x, y = pt; inside = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def g_mesh_interference(a, b, steps=240, span=1.0):
    """Meshing check of two wheels (g_mesh_with specs, spin at their own rates): outline points of b inside a's outline over `span` seconds.
    Returns the largest count of b outline points found inside a (0 = the teeth never overlap) and the number of outline points of b."""
    sb, worst = g_mesh_with(a, b)[0], 0; pa = lambda t: a.get("rz", 0.0) + a["spin"].get("phase", 0.0) + a["spin"]["deg_s"] * (t - a["spin"].get("t0", 0.0))
    for i in range(steps):
        t = span * i / steps; A = g_wheel_polygon(a["teeth"], a["pitch_r"], pa(t), a["x"], a["y"])
        B = g_wheel_polygon(b["teeth"], b["pitch_r"], sb["phase"] + sb["deg_s"] * (t - sb["t0"]), b["x"], b["y"])
        worst = max(worst, sum(1 for p in B if g_in_poly(p, A)))
    return worst, len(g_wheel_outline(b["teeth"], b["pitch_r"])[0])


def g_slow(t, t0, over, to):
    """Speed factor 1 -> `to` over `over` seconds from t0 (smoothstep), and its integral from 0 to t (distance in units of the initial speed)."""
    def s(u):
        if u <= t0:
            return 1.0
        x = min(1.0, (u - t0) / max(over, 1e-6)); return 1.0 - (1.0 - to) * x * x * (3 - 2 * x)
    n = max(8, int(abs(t) * 60)); h = t / n; acc = 0.0
    for i in range(n):
        acc += h * (s(i * h) + 4 * s((i + 0.5) * h) + s((i + 1) * h)) / 6.0
    return s(t), acc


def g_flurry_cards(spec):
    """Deterministic list of card parameter dicts for {count, seed, size{w,h}, region{x,y,z}, v, v_jitter, tumble{deg_s}, flutter, tints}."""
    rg = random.Random(spec.get("seed", 1)); out = []; R = spec["region"]; sz = spec.get("size", {}); vj = spec.get("v_jitter", [0, 0, 0]); tb = spec.get("tumble", {}).get("deg_s", [120, 360])
    fl = spec.get("flutter", {"amp": 0.02, "hz": [0.6, 1.4]}); tints = spec.get("tints") or ["#18C8F0", "#F020A0", "#FFD400"]
    for i in range(spec["count"]):
        w = rg.uniform(*sz.get("w", [0.10, 0.15])); hh = rg.uniform(*sz.get("h", [0.14, 0.21]))
        out.append({"i": i, "w": w, "h": hh, "t": sz.get("t", 0.0006), "p0": [rg.uniform(*R["x"]), rg.uniform(*R["y"]), rg.uniform(*R["z"])],
                    "v": [v + rg.uniform(-j, j) for v, j in zip(spec.get("v", [0, 0, 0]), vj)],
                    "rate": [rg.choice((-1, 1)) * rg.uniform(*tb) for _ in range(3)], "ph": [rg.uniform(0, 360) for _ in range(3)],
                    "fl_amp": fl.get("amp", 0.02) * rg.uniform(0.5, 1.0), "fl_hz": rg.uniform(*fl.get("hz", [0.6, 1.4])), "fl_ph": rg.uniform(0, 6.283),
                    "drift": [rg.uniform(-1, 1) for _ in range(3)], "tint": tints[i % len(tints)]})
    return out


def g_flurry_at(card, spec, t):
    """(loc, rot_deg) of a flurry card at spot time t. Motion starts at spec.t_start; after the gust (slow: {t0, over, to}) the card hangs: speed and
    tumble drop to `to` of their values and a slow residual drift (spec.drift m/s) remains."""
    ts = spec.get("t_start", 0.0); sl = spec.get("slow"); tt = t - ts
    fac, dist = g_slow(tt, sl["t0"] - ts, sl["over"], sl["to"]) if sl else (1.0, tt)
    dr = spec.get("drift", 0.0); loc = [card["p0"][k] + card["v"][k] * dist + dr * card["drift"][k] * tt for k in range(3)]
    loc[2] += card["fl_amp"] * math.sin(2 * math.pi * card["fl_hz"] * tt + card["fl_ph"]) * (0.4 + 0.6 * fac)
    rot = [card["ph"][k] + card["rate"][k] * dist for k in range(3)]
    return loc, rot
# ==== pv_generic end ====


# ---- the rig builder (needs bpy)
_GM = {}


def _gmat(part):
    """Material of a part by look: clay (take previs) = grey `shade`; clay_key / lookdev (animatic, stills) = `tint` (hex) with `rough`, `metal`, `emit`."""
    sh = float(part.get("shade", 0.55)); tint = part.get("tint")
    if LOOK == "clay" or not tint:
        key = ("g", sh); rgb, rough, metal, emit = (sh, sh, sh), 0.8, 0.0, 0.0
    else:
        rgb = hexlin(tint); rough = part.get("rough", 0.6); metal = part.get("metal", 0.0); emit = part.get("emit", 0.0); key = ("t", tint, rough, metal, emit)
    if key not in _GM:
        m = mat(f"gen_{len(_GM)}", rgb, rough); b = _principled(m)
        if metal:
            b.inputs["Metallic"].default_value = metal
        if emit:
            b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = emit
        _GM[key] = m
    return _GM[key]


def _mesh_obj(name, V, F, smooth, material):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in V], [], [tuple(f) for f in F]); me.update()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.materials.append(material); ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    return ob


def _norm_keys(keys):
    """Keys in the yaml may carry `f` (spot frame) instead of `t`, and notes: reduce to {t, channel...}."""
    out = []
    for k in keys or []:
        k = {a: b for a, b in k.items() if a not in ("note", "f")} if "t" in k else {**{a: b for a, b in k.items() if a not in ("note", "f")}, "t": k["f"] / FPS}
        out.append(k)
    return out


def subject_rig(sp):
    """A generic object: sp = {id, parts: [...], mask?}. Part keys: id, parent (id of an earlier part), shape (empty | box | card | cyl | sphere | torus | sector | wheel | poly,
    sizes in metres, see g_shape), loc [x, y, z] (local to the parent), rot [rx, ry, rz] degrees (Euler XYZ), scale, shade (clay grey) / tint, rough, metal, emit (colour looks),
    keys [{t | f, x, y, z, rx, ry, rz, sx, sy, sz, vis, hold, ease}] (monotone cubic per channel, spot time), spin {axis, deg_s, phase, t0} (continuous turn about a local axis),
    sway {ch, amp, hz, phase} (additive sine on a channel; a list is allowed), mesh_with <part id> (spin computed so the wheel's teeth mesh with that wheel), item (name of the
    group the part is scored in; default: the object id) and, for generators, `gen: flurry` (a cloud of paper cards, see g_flurry_cards) or `gen: ring` (n copies on a circle:
    n, radius, z, a0 = angle of the first copy, degrees counter-clockwise from +x, default 90 = 12 o'clock; copies run clockwise). Camera coordinates are world coordinates:
    the anchor is the world origin."""
    oid = sp.get("id", "rig"); parts = []
    for p in sp["parts"]:
        if p.get("gen") == "flurry":
            for c in g_flurry_cards(p):
                parts.append({"id": f"{p.get('id', 'fl')}{c['i']:02d}", "shape": "card", "w": c["w"], "h": c["h"], "t": c["t"], "tint": c["tint"], "shade": p.get("shade", 0.7),
                              "rough": 0.7, "_flurry": (c, p), "item": f"{p.get('id', 'fl')}{c['i']:02d}"})
        elif p.get("gen") == "ring":   # n copies of one part on a circle (dial indices, screws): angles clockwise from 12 o'clock, each long axis (local y) pointing outward
            for i in range(p["n"]):
                a = math.radians(p.get("a0", 90.0) - 360.0 * i / p["n"]); child = {k: v for k, v in p.items() if k not in ("gen", "n", "radius", "a0", "z", "id")}
                child.update(id=f"{p['id']}{i:02d}", loc=[p["radius"] * math.cos(a), p["radius"] * math.sin(a), p.get("z", 0.0)], rot=[0.0, 0.0, math.degrees(a) - 90.0])
                parts.append(child)
        else:
            parts.append(dict(p))
    byid = {p["id"]: p for p in parts}
    for p in parts:           # in list order (a partner comes earlier): spin_like = a pinion on the same shaft; mesh_with = teeth that mesh with that wheel
        if p.get("spin_like"):
            if "spin" not in byid[p["spin_like"]]:
                raise ValueError(f"{oid}.{p['id']}: spin_like {p['spin_like']} has no spin yet (it must come earlier in the list)")
            p["spin"] = dict(byid[p["spin_like"]]["spin"])
        if p.get("mesh_with"):
            a = byid[p["mesh_with"]]
            if a.get("parent") != p.get("parent"):
                raise ValueError(f"{oid}.{p['id']}: mesh_with {a['id']} needs the same parent")
            if "spin" not in a:
                raise ValueError(f"{oid}.{p['id']}: mesh_with {a['id']}: that wheel has no spin yet (it must come earlier in the list)")
            A = {"teeth": a["teeth"], "pitch_r": a["pitch_r"], "x": a["loc"][0], "y": a["loc"][1], "rz": (a.get("rot") or [0, 0, 0])[2], "spin": a["spin"]}
            B = {"teeth": p["teeth"], "pitch_r": p["pitch_r"], "x": p["loc"][0], "y": p["loc"][1]}
            p["spin"], err = g_mesh_with(A, B)
            if err > 0.03:
                raise ValueError(f"{oid}.{p['id']}: centre distance is {err:.1%} off the pitch radii sum of {a['id']} (teeth would clash or part)")
    objs, root_of_item = {}, {}
    for p in parts:
        name = f"{oid}.{p['id']}"
        if p.get("shape", "empty") == "empty":
            o = bpy.data.objects.new(name, None); sc.collection.objects.link(o)
        else:
            V, F, smooth = g_shape(p); o = _mesh_obj(name, V, F, smooth, _gmat(p))
            item = p.get("item", oid); root_of_item.setdefault(item, name); o["pv_role"] = sp.get("_role", "prop"); o["pv_root"] = root_of_item[item]
            if sp.get("mask"):
                o["pv_mask"] = 1
        o.rotation_mode = "XYZ"
        if p.get("parent"):
            o.parent = objs[p["parent"]]
        objs[p["id"]] = o
    for p in parts:           # animation: evaluated per frame at spot time t
        o = objs[p["id"]]; base_l, base_r, base_s = list(p.get("loc", [0, 0, 0])), list(p.get("rot", [0, 0, 0])), list(p.get("scale", [1, 1, 1]))
        ks = _norm_keys(p.get("keys")); cur = {}
        for ch, d in (("x", base_l[0]), ("y", base_l[1]), ("z", base_l[2]), ("rx", base_r[0]), ("ry", base_r[1]), ("rz", base_r[2]), ("sx", base_s[0]), ("sy", base_s[1]), ("sz", base_s[2]), ("vis", 1.0)):
            if ks and any(ch in k for k in ks):
                cur[ch] = Curve(ks, ch, d)
        spin = p.get("spin"); sway = p.get("sway"); sway = [sway] if isinstance(sway, dict) else (sway or []); fl = p.get("_flurry")
        if not (cur or spin or sway or fl):
            o.location, o.rotation_euler, o.scale = base_l, [math.radians(a) for a in base_r], base_s
            continue
        for f in range(1, N + 1):
            t = (f - 1) / FPS + T0
            if fl:
                loc, rot = g_flurry_at(fl[0], fl[1], t); sc_ = base_s; vis = 1.0
            else:
                g = lambda ch, d: cur[ch](t) if ch in cur else d
                loc = [g("x", base_l[0]), g("y", base_l[1]), g("z", base_l[2])]; rot = [g("rx", base_r[0]), g("ry", base_r[1]), g("rz", base_r[2])]
                sc_ = [g("sx", base_s[0]), g("sy", base_s[1]), g("sz", base_s[2])]; vis = g("vis", 1.0)
                if spin:
                    ax = {"x": 0, "y": 1, "z": 2}[spin.get("axis", "z")]; rot[ax] += spin.get("phase", 0.0) + spin["deg_s"] * (t - spin.get("t0", 0.0))
                for w_ in sway:
                    ch = w_["ch"]; v_ = w_["amp"] * math.sin(2 * math.pi * w_["hz"] * t + math.radians(w_.get("phase", 0.0)))
                    if ch in ("x", "y", "z"):
                        loc["xyz".index(ch)] += v_
                    else:
                        rot["xyz".index(ch[1])] += v_
            o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]; o.scale = sc_
            o.keyframe_insert("location", frame=f); o.keyframe_insert("rotation_euler", frame=f)
            if cur.get("sx") or cur.get("sy") or cur.get("sz"):
                o.keyframe_insert("scale", frame=f)
            if "vis" in cur:
                o.hide_render = o.hide_viewport = vis < 0.5; o.keyframe_insert("hide_render", frame=f); o.keyframe_insert("hide_viewport", frame=f)
    return lambda t: Vector((0, 0, 0))


# ---- the stage set: ground, blocks and building rows from set_params
def set_stage():
    """set_params: world {rgb, strength}, sun {rot [deg x3], energy}, ground {size, z, shade, tint, centre [x, y]}, blocks [{shape: box|cyl, x, y, z0, w, d, h | r, shade, tint, rough, metal}],
    rows [{p0, p1, step, w [lo, hi], d [lo, hi], h [lo, hi], gap, seed, shade, tint}] (building rows along a line), lights [{loc, energy (energy_clay for the clay looks), size, rgb, aim}]. Clay unless the look has tints."""
    S = P.get("set_params", {}); wd = S.get("world", {})
    world(tuple(wd.get("rgb", (0.5, 0.5, 0.5))), wd.get("strength", 1.0))
    sn = S.get("sun", {"rot": [52, 0, -32], "energy": 1.5})
    if sn.get("energy", 1.5) > 0:
        sun(sn.get("rot", [52, 0, -32]), sn.get("energy", 1.5))
    g = S.get("ground", {})
    if g is not None and g.get("size", 1) != 0:
        gs = g.get("size", 400.0); c = g.get("centre", [0.0, 0.0])
        V, F = g_box(gs, gs, 0.2); _mesh_obj("stage_ground", [(x + c[0], y + c[1], z + g.get("z", 0.0) - 0.1) for x, y, z in V], F, False, _gmat({"shade": g.get("shade", 0.35), "tint": g.get("tint"), "rough": g.get("rough", 0.9)}))
    for i, b in enumerate(S.get("blocks", [])):
        z0 = b.get("z0", 0.0)
        if b.get("shape", "box") == "cyl":
            V, F = g_cyl(b["r"], b["h"], 24); V = [(x + b["x"], y + b["y"], z + z0 + b["h"] / 2.0) for x, y, z in V]; sm = False
        else:
            V, F = g_box(b["w"], b["d"], b["h"]); V = [(x + b["x"], y + b["y"], z + z0 + b["h"] / 2.0) for x, y, z in V]
        _mesh_obj(f"stage_block{i}", V, F, False, _gmat(b))
    for j, rw in enumerate(S.get("rows", [])):
        rg = random.Random(rw.get("seed", 1)); (x0, y0), (x1, y1) = rw["p0"], rw["p1"]; L = math.hypot(x1 - x0, y1 - y0); ux, uy = (x1 - x0) / L, (y1 - y0) / L; s = 0.0; k = 0
        while s < L:
            d = rg.uniform(*rw.get("d", [5, 9])); w = rg.uniform(*rw.get("w", [4, 6])); h = rg.uniform(*rw.get("h", [7, 18])); mid = s + d / 2.0
            V, F = g_box(w, d, h)
            ang = math.degrees(math.atan2(uy, ux)) - 90.0
            V, F = g_xf((V, F), loc=(x0 + ux * mid, y0 + uy * mid, h / 2.0 + rw.get("z0", 0.0)), rz_deg=ang)
            _mesh_obj(f"stage_row{j}_{k}", V, F, False, _gmat(rw)); s += d + rw.get("gap", 0.3); k += 1
    for i, l in enumerate(S.get("lights", [])):
        bpy.ops.object.light_add(type="AREA", location=tuple(l["loc"])); L_ = bpy.context.object; L_.data.energy = (l.get("energy_clay", l.get("energy", 100)) if not LOOKDEV else l.get("energy", 100)); L_.data.size = l.get("size", 1.0)
        L_.data.color = tuple(l.get("rgb", (1, 1, 1))); L_.rotation_euler = (Vector(l.get("aim", (0, 0, 0))) - Vector(l["loc"])).to_track_quat("-Z", "Y").to_euler()


_SETF = {"street": set_street, "rooftop": set_rooftop, "studio_dark": set_studio_dark, "boxes": set_boxes,
         "slime_pool": set_slime_pool, "studio_pack": set_studio_pack, "meadow": set_meadow, "pastel_valley": set_pastel_valley, "stage": set_stage}[P.get("set", "boxes")]
_before_set = set(bpy.data.objects)
_SETF()
if P.get("set_offset"):   # per-segment world offset of the set (the camera and subjects keep their world coordinates)
    _so = P["set_offset"]; _ov = Vector((_so.get("x", 0.0), _so.get("y", 0.0), _so.get("z", 0.0)))
    for _o in bpy.data.objects:
        if _o not in _before_set and _o.parent is None:
            _o.location = _o.location + _ov
    if "puddle0" in MEADOW:
        MEADOW["puddle0"] = tuple(a_ + b_ for a_, b_ in zip(MEADOW["puddle0"], _ov))
def subject_proxy(sp):
    """Stand-in for a person (classic previs blocking): a plain capsule of her size, no limbs, so the previs carries
    only framing, distance and the camera move; her performance comes from the still and the prompt (the director
    2026-10-15: previs is for camera moves, not for human motion). height m, width m, pose standing|seated (seated =
    a shorter block on the 0.55 m wall), speed m/s toward the camera (-Y, 0 = still), y start offset."""
    hgt, wid = sp.get("height", 1.65), sp.get("width", 0.5)
    seated = sp.get("pose", "standing") == "seated"
    v, y0 = sp.get("speed", 0.0), sp.get("y", 0.0)
    body_h = hgt * (0.62 if seated else 1.0); base = 0.55 if seated else 0.0
    bpy.ops.mesh.primitive_cylinder_add(radius=wid / 2, depth=body_h - wid, location=(0, 0, base + body_h / 2))
    col = bpy.context.object; col.data.materials.append(BODY)
    for z in (base + wid / 2, base + body_h - wid / 2):   # rounded ends (capsule)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=wid / 2, location=(0, 0, z)); bpy.context.object.data.materials.append(BODY)
    root = bpy.data.objects.new("proxy", None); sc.collection.objects.link(root)
    for o in [o for o in bpy.data.objects if o.type == "MESH" and o.data.materials and o.data.materials[0] == BODY]:
        o.parent = root
    for f in range(1, N + 1):
        t = (f - 1) / FPS + T0
        root.location = (0, y0 - v * t, 0); root.keyframe_insert("location", frame=f)
    return lambda t: Vector((0, y0 - v * t, 0))


SUBJECTS = {"walker": subject_walker, "sitter": subject_sitter, "hanger_hoodie": subject_hanger_hoodie,
            "proxy": subject_proxy, "none": lambda sp: (lambda t: Vector((0, 0, 0))),
            "can3": subject_can3, "slime_drip": subject_slime_drip, "slime_impact": subject_slime_impact, "can330": subject_can330, "lime_drop": subject_lime_drop,
            "rig": subject_rig}
# roles for the scene-data export (vt.py animatic-score): the objects a subject builder creates are tagged with a role and the name of their
# root object. product = the thing being sold / shown (default for the subject types below), prop = everything else; params.json `roles`
# {subject: product|prop|none} overrides, objects of `props` are props. Untagged objects (set, lights, camera) are not tracked.
PRODUCT_SUBJECTS = {"can3", "can330", "hanger_hoodie", "walker", "sitter", "proxy"}


def _tag_new(before, role):
    new = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    names = {o.name for o in new}
    for o in new:
        if "pv_role" in o:   # tagged by its builder (the generic rig groups its parts into items itself)
            continue
        r = o
        while r.parent is not None and r.parent.name in names:
            r = r.parent
        o["pv_role"], o["pv_root"] = role, r.name


def _role(subject):
    return (P.get("roles") or {}).get(subject) or ("product" if subject in PRODUCT_SUBJECTS else "prop")


if P.get("subjects"):   # several subjects in one scene (the first is the anchor); the old single `subject` still works
    _anch = []
    for sj in P["subjects"]:
        _b = set(bpy.data.objects); _sp = sj.get("subject_params", {})
        if sj["subject"] == "rig":   # generic objects carry their own role (product | prop) in the subject entry
            _sp = {**_sp, "_role": sj.get("role") or "prop"}
        _anch.append(SUBJECTS[sj["subject"]](_sp)); _tag_new(_b, sj.get("role") or _role(sj["subject"]))
    anchor = _anch[0]
else:
    _b = set(bpy.data.objects); anchor = SUBJECTS[P.get("subject", "none")](P.get("subject_params", {})); _tag_new(_b, _role(P.get("subject", "none")))
if P.get("props"):
    _b = set(bpy.data.objects); build_props(P["props"]); _tag_new(_b, "prop")

# ---------------------------------------------------------------- camera
C = P["camera"]
KEYS = ("d", "a_deg", "z", "lens", "tx", "tz")
if "keys" in C:   # keyframes [{t, d, a_deg, z, lens, tx, tz}, ...]; missing fields carry over from the previous key
    keys, last = [], {}
    for k in sorted(C["keys"], key=lambda k: k["t"]):
        last = {**last, **k}; keys.append(dict(last))
else:             # start -> end form: {d: [a, b], ...} eased over ease=[t0, t1]
    e0, e1 = C.get("ease", [0.0, (N - 1) / FPS])
    keys = [{"t": e0, **{k: C[k][0] for k in KEYS}}, {"t": e1, **{k: C[k][1] for k in KEYS}}]


def cam_at(t):
    """Smooth (ease in/out) interpolation between consecutive keys; holds before the first and after the last."""
    if t <= keys[0]["t"]:
        return keys[0]
    for k0, k1 in zip(keys, keys[1:]):
        if t <= k1["t"]:
            u = smooth(k0["t"], k1["t"], t)
            return {k: k0[k] + (k1[k] - k0[k]) * u for k in KEYS}
    return keys[-1]


if C.get("interp") == "cubic":   # spec PV3: per-channel monotone cubic through the keys (continuous velocity, hold: true = stop)
    _CH = KEYS + ("roll_deg", "tr"); _ck = sorted(C["keys"], key=lambda k: k["t"]); _cc = {ch: Curve(_ck, ch, 0.0) for ch in _CH}   # tr: look-at offset to the camera's right (m)

    def cam_at(t):
        return {ch: _cc[ch](t) for ch in _CH}


HH = C.get("handheld", 0.0)   # handheld sway amplitude (metres; ~0.01 subtle, ~0.03 strong)
cam_data = bpy.data.cameras.new("cam"); cam_data.sensor_fit = "VERTICAL"; cam_data.sensor_height = 36
if "clip_start" in C or P.get("set") in ("slime_pool", "studio_pack", "meadow", "pastel_valley", "stage"):   # close products: Blender's 0.1 m default clips them (P6)
    cam_data.clip_start = C.get("clip_start", 0.005)
if C.get("dof"):                                          # {focus: m, fstop: f}
    cam_data.dof.use_dof = True; cam_data.dof.focus_distance = C["dof"]["focus"]; cam_data.dof.aperture_fstop = C["dof"].get("fstop", 2.8)
cam = bpy.data.objects.new("cam", cam_data); sc.collection.objects.link(cam); sc.camera = cam
for f in range(1, N + 1):
    t = (f - 1) / FPS + T0; K = cam_at(t); A = anchor(t)
    d, a = K["d"], math.radians(K["a_deg"])
    sway = Vector((HH * (math.sin(t * 1.7) + 0.5 * math.sin(t * 4.3)), HH * 0.5 * math.sin(t * 2.3),
                   HH * 0.7 * (math.sin(t * 2.9 + 1) + 0.4 * math.sin(t * 6.1))))
    cam.location = Vector((A.x + d * math.sin(a), A.y - d * math.cos(a), K["z"])) + sway
    tgt = Vector((A.x + K["tx"], A.y, K["tz"]))
    if K.get("tr"):   # look-at shifted along the camera's right axis (keeps a product in the right or left third on an arc)
        tgt = tgt + Vector((math.cos(a), math.sin(a), 0.0)) * K["tr"]
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    if K.get("roll_deg"):   # camera roll about the view axis
        cam.rotation_euler = ((tgt - cam.location).to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), math.radians(K["roll_deg"]))).to_euler()
    cam_data.lens = K["lens"]
    if C.get("dof", {}).get("follow"):   # focus distance tracks the look-at point (plus the offset it had at frame 1)
        dist_ = (tgt - cam.location).length
        if f == 1:
            FOLLOW_OFF = C["dof"]["focus"] - dist_
        cam_data.dof.focus_distance = dist_ + FOLLOW_OFF; cam_data.dof.keyframe_insert("focus_distance", frame=f)
    if C.get("dof", {}).get("fstop_keys"):   # f-stop over time (e.g. stop down for a push-through object right at the lens)
        _fk = C["dof"].setdefault("_curve", Curve(C["dof"]["fstop_keys"], "fstop", C["dof"].get("fstop", 4.0)))
        cam_data.dof.aperture_fstop = _fk(t); cam_data.dof.keyframe_insert("aperture_fstop", frame=f)
    cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f); cam_data.keyframe_insert("lens", frame=f)

# ---------------------------------------------------------------- scene data (vt.py animatic-score, 2026-10-19)
def export_scene_data():
    """PREVIS_DATA=1|only: per-frame world / camera-space / screen-space numbers of the camera, the products (c330_* roots, children
    merged) and the props (fruit halves, berries), read from the keyed scene with frame_set, no render. Written to OUT/data.json.
    Screen coordinates are fractions of the frame (x from the left, y from the top; may leave 0..1), sensor_fit VERTICAL 36 mm."""
    import numpy as np
    from mathutils import Matrix as _M

    groups = {}   # (role, root object name) -> mesh objects of that root (children merged); roles are set where the subject builders run
    for ob in bpy.data.objects:
        if ob.type == "MESH" and ob.get("pv_role") in ("product", "prop"):
            groups.setdefault((ob["pv_role"], ob["pv_root"]), []).append(ob)
    loc_v = {}
    for ob in sum(groups.values(), []):
        n = len(ob.data.vertices); a = np.empty(n * 3, dtype=np.float32); ob.data.vertices.foreach_get("co", a)
        a = a.reshape(-1, 3).astype(np.float64); loc_v[ob.name] = a[:: max(1, n // 500)]
    out = {"fps": FPS, "w": W, "h": H, "time_offset": T0, "spot_frame0": int(round(T0 * FPS)), "frames": []}
    r5 = lambda v: [round(float(x), 5) for x in v]
    r8 = lambda v: [round(float(x), 9) for x in v]      # quaternions: small turn angles need the digits
    for f in range(1, N + 1):
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
        cm = cam.evaluated_get(dg).matrix_world; R = np.array(cm.to_3x3()); R = R / np.linalg.norm(R, axis=0); cl = np.array(cm.translation)
        lens = float(cam_data.lens); k = lens / 36.0
        rec = {"f": out["spot_frame0"] + f - 1, "cam": {"loc": r5(cl), "quat": r8(_M(R.tolist()).to_quaternion()), "lens": round(lens, 4),
                                                       "aim": r5(-R[:, 2])}, "items": {}}
        for (kind, name), obs in groups.items():
            root = next(o for o in obs if o.name == name)
            if root.hide_render:
                rec["items"][name] = {"kind": kind, "vis": False}; continue
            pts = []
            for o in obs:
                m = np.array(o.evaluated_get(dg).matrix_world); pts.append(loc_v[o.name] @ m[:3, :3].T + m[:3, 3])
            P_ = np.concatenate(pts); pc = (P_ - cl) @ R; depth = -pc[:, 2]; ok = depth > 1e-4
            if ok.sum() < 3:
                rec["items"][name] = {"kind": kind, "vis": False}; continue
            pc, depth, Pw = pc[ok], depth[ok], P_[ok]
            sx = 0.5 + pc[:, 0] / depth * k * (H / W); sy = 0.5 - pc[:, 1] / depth * k
            mr = np.array(root.evaluated_get(dg).matrix_world.to_3x3()); mr = mr / np.linalg.norm(mr, axis=0)
            rc = R.T @ mr; q = _M(rc.tolist()).to_quaternion(); zax = rc[:, 2]
            inside = (sx >= 0) & (sx <= 1) & (sy >= 0) & (sy <= 1)
            rec["items"][name] = {"kind": kind, "vis": True, "bbox": r5([sx.min(), sy.min(), sx.max(), sy.max()]),
                                  "c": r5([(sx.min() + sx.max()) / 2, (sy.min() + sy.max()) / 2]),
                                  "depth": r5([depth.min(), float(np.median(depth))]), "in_frame": round(float(inside.mean()), 3),
                                  "above_ground": round(float((Pw[:, 2] > 0.004).mean()), 3), "world_c": r5(Pw.mean(0)),
                                  "world_zrange": r5([Pw[:, 2].min(), Pw[:, 2].max()]), "quat_cam": r8(q),
                                  "axis_deg": round(math.degrees(math.atan2(zax[0], zax[1])), 3)}
        out["frames"].append(rec)
    sc.frame_set(1)
    json.dump(out, open(OUT + "data.json", "w"))
    print("PREVIS_DATA", len(out["frames"]), "frames", len(groups), "items", flush=True)


if os.environ.get("PREVIS_DATA"):
    export_scene_data()
    if os.environ["PREVIS_DATA"] == "only":
        print("PREVIS_DONE", flush=True)
        raise SystemExit(0)

# ---------------------------------------------------------------- render: beauty + normalised depth
sc.render.engine = "CYCLES";sc.cycles.samples, sc.cycles.use_denoising = SAMPLES, True
sc.cycles.device = "CPU"
if P.get("motion_blur"):   # spec PV4: Cycles blur on camera and object transforms (all keyed every frame)
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = P["motion_blur"].get("shutter", 0.5)
if os.environ.get("PREVIS_DEVICE") == "GPU":   # OptiX on the 4090 (run_previs.sh --gpu, on a GPU machine)
    cp = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            cp.compute_device_type = kind; cp.get_devices()
            devs = [d for d in cp.devices if d.type == kind]
        except Exception:
            devs = []
        if devs:
            for d in cp.devices:
                d.use = d.type == kind
            sc.cycles.device = "GPU"; print("PREVIS_DEVICE", kind, [d.name for d in devs], flush=True)
            if kind == "OPTIX":
                sc.cycles.denoiser = "OPTIX"   # the default OIDN denoiser ran on CPU in the container: ~4 s/frame
            break
    else:
        print("PREVIS_DEVICE no GPU found, CPU", flush=True)
if P.get("set") in ("slime_pool", "studio_pack", "meadow", "stage"):
    if LOOKDEV:
        sc.view_settings.view_transform = "Standard"
        sc.cycles.max_bounces, sc.cycles.transmission_bounces, sc.cycles.glossy_bounces = 12, 8, 8
        sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False; sc.cycles.sample_clamp_indirect = 8
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.01
    if P.get("set_params", {}).get("exposure"):
        sc.view_settings.exposure = P["set_params"]["exposure"]
sc.view_layers[0].use_pass_z = True
sc.use_nodes = True; tree = sc.node_tree
for nd in list(tree.nodes):
    tree.nodes.remove(nd)
rl = tree.nodes.new("CompositorNodeRLayers"); comp = tree.nodes.new("CompositorNodeComposite")
tree.links.new(rl.outputs["Image"], comp.inputs["Image"])
D = P.get("depth", {})
mr = tree.nodes.new("CompositorNodeMapRange")
mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = D.get("near", 1.0), D.get("far", 30.0)
mr.inputs["To Min"].default_value, mr.inputs["To Max"].default_value = 1.0, 0.0; mr.use_clamp = True
tree.links.new(rl.outputs["Depth"], mr.inputs["Value"])
fo = tree.nodes.new("CompositorNodeOutputFile"); fo.base_path = OUT; fo.file_slots[0].path = "depth_"
fo.format.file_format, fo.format.color_mode = "PNG", "BW"
if not os.environ.get("PREVIS_NODEPTH"):   # animatic drafts need no depth video
    tree.links.new(mr.outputs[0], fo.inputs[0])
if os.environ.get("PREVIS_MASK"):   # exact product mask (vt.py accept): object-index pass of the can330 objects and their children -> mask_NNNN.png (white = product)
    def _is_product(o):
        while o is not None:
            if o.name.startswith("c330_") or o.get("pv_mask"):
                return True
            o = o.parent
        return False
    for _o in bpy.data.objects:
        _o.pass_index = 1 if _is_product(_o) else 0
    sc.view_layers[0].use_pass_object_index = True
    idm = tree.nodes.new("CompositorNodeIDMask"); idm.index = 1; idm.use_antialiasing = True
    tree.links.new(rl.outputs["IndexOB"], idm.inputs[0])
    fm = tree.nodes.new("CompositorNodeOutputFile"); fm.base_path = OUT; fm.file_slots[0].path = "mask_"
    fm.format.file_format, fm.format.color_mode = "PNG", "BW"; tree.links.new(idm.outputs[0], fm.inputs[0])
sc.render.filepath = OUT + "beauty_"; sc.render.image_settings.file_format = "PNG"
if os.environ.get("PREVIS_START"):
    sc.frame_start = int(os.environ["PREVIS_START"])
if os.environ.get("PREVIS_ONE"):
    sc.frame_end = 1
if os.environ.get("PREVIS_FRAME"):   # one frame n (1-based), for checks of a later beat
    sc.frame_start = sc.frame_end = int(os.environ["PREVIS_FRAME"])
if P.get("set") == "slime_pool":
    link_lights()
if FRAME_HOOKS:   # slime / puddle / coat updaters run before every frame (also once now, for the first frame)
    bpy.app.handlers.frame_change_pre.append(slime_frame_update)
    sc.frame_set(sc.frame_start); slime_frame_update(sc)
bpy.ops.render.render(animation=True)
print("PREVIS_DONE", flush=True)
