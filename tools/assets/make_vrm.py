#!/usr/bin/env python3
"""Builds Vee, the sample's 3D character, as a VRM avatar, and her motions as VRM animations.

Vee is a World character played by a VRM avatar (KAGEnvCharacterVRM.tjs; doc/world.txt, "VRM
Characters"), drawn by the krkrthreepp plugin. She's made here from shapes, as Pip is drawn from
signed distance fields, so the sample has a VRM of its own: no third-party model. This writes:

- data/fgimage/vee.vrm: the avatar, a VRM 1.0 file (glTF binary with VRMC_vrm). A girl in a
  lavender dress with twin tails, about 1.37 m tall, in the T-pose VRM asks for, facing +Z. Every
  part is a surface of revolution, an ellipsoid or a capsule skinned to its bones (the body and
  the twin tails with weights that blend along them), coloured by MToon materials
  (VRMC_materials_mtoon) with a navy outline, the theme's (make_ui.py). Her face is shapes on the
  head (eyes, lashes, brows, mouth, blush), and her expressions move them (morph targets): the
  VRM presets happy, angry, sad, relaxed, surprised, the mouths aa, ih, ou, ee, oh, blink,
  blinkLeft, blinkRight, and blush of her own. Her twin tails swing (VRMC_springBone).
- data/fgimage/vee_<motion>.vrma: her motions, VRM animations (glTF with VRMC_vrm_animation):
  idle and think go on (loops), wave, nod, bow and cheer play once. Each is sampled 30 times a
  second from the functions below; the arms are aimed (a shortest turn from the bone's rest
  direction), the rest turned by angles.

- data/fgimage/star3d.glb (`prop`): a glTF model for the layer demo, the emblem's star made puffy
  (a five-pointed star whose faces rise to a point front and back), violet and a little metallic,
  with two animations of its own: spin (it turns about its axis) and hop (it jumps and turns).

The numbers are fixed, so the files come out the same each time. `speech` makes her voice line
(data/voice/vee000001.ogg, the 【vee】 line after `voice=1` in anim.ks) with eSpeak NG, a formant
synthesizer (rules and a model of the vocal tract, no voice learned from recordings), as
make_hiyori.py makes Hiyori's: US English's anika variant, a little higher and slower, and ffmpeg
(ESPEAK_NG names espeak-ng when it isn't on the PATH); kagex-lipsync then makes its lip track
(`kagex-lipsync --cli make vee000001.ogg`).

usage: python3 tools/assets/make_vrm.py [model] [motions] [prop] [speech]
"""
import json, math, os, re, shutil, struct, subprocess, sys, tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "fgimage")
VOICE = os.path.join(ROOT, "data", "voice")
SCRIPT = os.path.join(ROOT, "data", "scenario", "anim.ks")
NAME = "vee"

# eSpeak NG's voice for her: US English, the anika variant, pitched up (Hiyori has it as it is)
ESPEAK_VOICE = "en-us+anika"
ESPEAK_SPEED = 160
ESPEAK_PITCH = 68

# ---------------------------------------------------------------------------
# colours (sRGB 0-255), in the theme's (make_ui.py)
# ---------------------------------------------------------------------------
SKIN = (255, 230, 216)
SKIN_SHADE = (240, 184, 178)
HAIR = (92, 62, 150)
HAIR_SHADE = (52, 30, 104)
DRESS = (166, 144, 255)
DRESS_SHADE = (112, 84, 220)
VIOLET = (80, 37, 255)
VIOLET_SHADE = (48, 18, 170)
WHITE = (255, 255, 255)
WHITE_SHADE = (196, 190, 232)
NAVY = (1, 0, 98)
IRIS = (112, 72, 236)
PUPIL = (28, 12, 92)
LASH = (30, 14, 70)
MOUTH = (150, 46, 84)
BLUSH = (255, 128, 160)

# ---------------------------------------------------------------------------
# the skeleton: name, parent, translation from the parent (metres). The VRM humanoid bones are
# the first; the twin tails' bones swing (spring bones)
# ---------------------------------------------------------------------------
BONES = [
    ("hips", None, (0, 0.60, 0)),
    ("spine", "hips", (0, 0.07, 0)),
    ("chest", "spine", (0, 0.14, 0)),
    ("neck", "chest", (0, 0.17, 0)),
    ("head", "neck", (0, 0.06, 0)),
    ("leftShoulder", "chest", (0.02, 0.135, 0)),
    ("leftUpperArm", "leftShoulder", (0.10, 0, 0)),
    ("leftLowerArm", "leftUpperArm", (0.19, 0, 0)),
    ("leftHand", "leftLowerArm", (0.17, 0, 0)),
    ("rightShoulder", "chest", (-0.02, 0.135, 0)),
    ("rightUpperArm", "rightShoulder", (-0.10, 0, 0)),
    ("rightLowerArm", "rightUpperArm", (-0.19, 0, 0)),
    ("rightHand", "rightLowerArm", (-0.17, 0, 0)),
    ("leftUpperLeg", "hips", (0.075, -0.05, 0)),
    ("leftLowerLeg", "leftUpperLeg", (0, -0.25, 0)),
    ("leftFoot", "leftLowerLeg", (0, -0.25, 0)),
    ("rightUpperLeg", "hips", (-0.075, -0.05, 0)),
    ("rightLowerLeg", "rightUpperLeg", (0, -0.25, 0)),
    ("rightFoot", "rightLowerLeg", (0, -0.25, 0)),
]
HUMANOID = [b[0] for b in BONES]
TAIL = 4          # bones in each twin tail
TAIL_STEP = 0.095 # metres between them
for side, s in (("L", 1), ("R", -1)):
    BONES.append((f"tail{side}0", "head", (s * 0.165, 0.215, -0.07)))
    for i in range(1, TAIL):
        BONES.append((f"tail{side}{i}", f"tail{side}{i - 1}", (s * 0.012, -TAIL_STEP, -0.004)))
    BONES.append((f"tail{side}{TAIL}", f"tail{side}{TAIL - 1}", (s * 0.004, -TAIL_STEP * 0.8, 0)))

BONE_INDEX = {b[0]: i for i, b in enumerate(BONES)}


def bone_world():
    """Each bone's rest position (the rest rotations are all none)."""
    pos = {}
    for name, parent, t in BONES:
        p = np.array(t, dtype=np.float64)
        if parent is not None:
            p = p + pos[parent]
        pos[name] = p
    return pos


WORLD = bone_world()
HEAD_C = WORLD["head"] + np.array([0, 0.14, 0.0])   # the centre of the head's ellipsoid
HEAD_R = np.array([0.185, 0.175, 0.170])            # its radii


# ---------------------------------------------------------------------------
# meshes
# ---------------------------------------------------------------------------
class Part:
    """Vertices, triangles, skin weights and morph target offsets of one primitive."""

    def __init__(self, pos, tri, joints=None, weights=None, normals=None):
        self.pos = np.asarray(pos, dtype=np.float64).reshape(-1, 3)
        self.tri = np.asarray(tri, dtype=np.int64).reshape(-1, 3)
        n = len(self.pos)
        self.joints = np.zeros((n, 4), dtype=np.int64) if joints is None else np.asarray(joints)
        self.weights = np.zeros((n, 4), dtype=np.float64) if weights is None else np.asarray(weights, dtype=np.float64)
        if weights is None:
            self.weights[:, 0] = 1.0
        self.normals = normals
        self.targets = {}

    def rigid(self, bone):
        self.joints[:, :] = 0
        self.joints[:, 0] = BONE_INDEX[bone]
        self.weights[:, :] = 0
        self.weights[:, 0] = 1.0
        return self

    def smooth_normals(self):
        if self.normals is not None:
            return self.normals
        p, t = self.pos, self.tri
        fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
        n = np.zeros_like(p)
        for k in range(3):
            np.add.at(n, t[:, k], fn)
        # vertices that share a place (a seam, a pole) share a normal
        key = np.round(p * 1e5).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        acc = np.zeros((inv.max() + 1, 3))
        np.add.at(acc, inv, n)
        n = acc[inv]
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        ln[ln == 0] = 1
        self.normals = n / ln
        return self.normals


def orient(part, ref=None):
    """Turns a part's triangles to face out from ref (its centre by default): the materials that
    aren't double-sided draw only the side a triangle's winding faces."""
    p, t = part.pos, part.tri
    c = p.mean(axis=0) if ref is None else np.asarray(ref)
    fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
    if np.sum(np.einsum("ij,ij->i", fn, p[t].mean(axis=1) - c)) < 0:
        part.tri = part.tri[:, [0, 2, 1]]
    return part


def merge(parts, oriented=False):
    pos, tri, joints, weights, normals = [], [], [], [], []
    off = 0
    for p in parts:
        if not oriented:
            orient(p)
        pos.append(p.pos)
        tri.append(p.tri + off)
        joints.append(p.joints)
        weights.append(p.weights)
        normals.append(p.smooth_normals())
        off += len(p.pos)
    m = Part(np.concatenate(pos), np.concatenate(tri), np.concatenate(joints), np.concatenate(weights),
             np.concatenate(normals))
    return m


def grid_tris(nu, nv, wrap_u=True):
    """Triangles of a (nv+1) x nu grid of vertices (rows v, columns u), u wrapping around."""
    tris = []
    cols = nu if wrap_u else nu - 1
    for j in range(nv):
        for i in range(cols):
            a = j * nu + i
            b = j * nu + (i + 1) % nu
            c = (j + 1) * nu + i
            d = (j + 1) * nu + (i + 1) % nu
            tris.append((a, c, b))
            tris.append((b, c, d))
    return np.array(tris)


def lathe(profile, seg=48, zscale=1.0, center=(0, 0, 0), outward=True):
    """A surface of revolution around Y: profile is [(radius, y)] from top to bottom."""
    prof = np.array(profile, dtype=np.float64)
    th = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    pos = []
    for r, y in prof:
        for a in th:
            pos.append((center[0] + r * math.sin(a), center[1] + y, center[2] + r * math.cos(a) * zscale))
    tri = grid_tris(seg, len(prof) - 1)
    if not outward:
        tri = tri[:, [0, 2, 1]]
    return Part(pos, tri)


def ellipsoid(center, radii, nu=40, nv=24):
    pos = []
    for j in range(nv + 1):
        lat = math.pi / 2 - math.pi * j / nv
        for i in range(nu):
            lon = 2 * math.pi * i / nu
            pos.append((center[0] + radii[0] * math.cos(lat) * math.sin(lon),
                        center[1] + radii[1] * math.sin(lat),
                        center[2] + radii[2] * math.cos(lat) * math.cos(lon)))
    p = Part(pos, grid_tris(nu, nv))
    # analytic normals of an ellipsoid
    c = np.array(center)
    q = (p.pos - c) / np.array(radii) ** 2
    ln = np.linalg.norm(q, axis=1, keepdims=True)
    ln[ln == 0] = 1
    p.normals = q / ln
    return p


def capsule(a, b, r, nu=24, nv=16, rb=None):
    """A capsule from a to b, radius r (rb at b when the capsule tapers)."""
    rb = r if rb is None else rb
    a, b = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
    axis = b - a
    length = np.linalg.norm(axis)
    d = axis / length
    # a frame around the axis
    up = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    e1 = np.cross(d, up)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    pos, nrm = [], []
    half = nv // 2
    for j in range(nv + 2):
        # rows 0..half: the cap at a (from its pole); half+1..nv+1: the cap at b
        if j <= half:
            phi = -math.pi / 2 + (math.pi / 2) * j / half
            base, rad = a, r
        else:
            phi = (math.pi / 2) * (j - half - 1) / half
            base, rad = b, rb
        for i in range(nu):
            th = 2 * math.pi * i / nu
            radial = e1 * math.cos(th) + e2 * math.sin(th)
            n = radial * math.cos(phi) + d * math.sin(phi)
            pos.append(base + n * rad)
            nrm.append(n)
    p = Part(pos, grid_tris(nu, nv + 1))
    p.normals = np.array(nrm)
    return p


# ---------------------------------------------------------------------------
# the body
# ---------------------------------------------------------------------------
def band_weights(part, bands):
    """Skin weights that blend between bones by height: bands is [(y, bone)] from top to
    bottom; a vertex between two takes both, by how near it is."""
    ys = np.array([b[0] for b in bands])
    for v in range(len(part.pos)):
        y = part.pos[v, 1]
        part.joints[v] = 0
        part.weights[v] = 0
        if y >= ys[0]:
            part.joints[v, 0] = BONE_INDEX[bands[0][1]]
            part.weights[v, 0] = 1
            continue
        if y <= ys[-1]:
            part.joints[v, 0] = BONE_INDEX[bands[-1][1]]
            part.weights[v, 0] = 1
            continue
        for k in range(len(bands) - 1):
            if ys[k + 1] <= y <= ys[k]:
                t = (ys[k] - y) / (ys[k] - ys[k + 1])
                t = t * t * (3 - 2 * t)
                part.joints[v, 0] = BONE_INDEX[bands[k][1]]
                part.weights[v, 0] = 1 - t
                part.joints[v, 1] = BONE_INDEX[bands[k + 1][1]]
                part.weights[v, 1] = t
                break
    return part


def body_parts():
    """{material: [parts]}"""
    parts = {k: [] for k in ("skin", "dress", "white", "violet", "hair")}
    w = WORLD
    # head and neck
    parts["skin"].append(ellipsoid(HEAD_C, HEAD_R, 56, 36).rigid("head"))
    parts["skin"].append(capsule(w["neck"] + [0, -0.03, 0], w["head"] + [0, 0.04, 0], 0.036).rigid("neck"))
    # the dress: chest, waist and a skirt that flares, deeper side to side than front to back
    dress = lathe([(0.040, 0.985), (0.070, 0.972), (0.096, 0.952), (0.108, 0.925), (0.110, 0.885),
                   (0.103, 0.83), (0.092, 0.765), (0.088, 0.72), (0.100, 0.665), (0.128, 0.60),
                   (0.165, 0.53), (0.200, 0.465), (0.222, 0.425), (0.214, 0.418), (0.196, 0.43)],
                  seg=64, zscale=0.82)
    band_weights(dress, [(0.90, "chest"), (0.80, "chest"), (0.70, "spine"), (0.62, "hips")])
    parts["dress"].append(dress)
    # a white collar over the shoulders, and a violet bow at its front
    collar = lathe([(0.044, 0.992), (0.078, 0.978), (0.108, 0.956), (0.122, 0.937), (0.112, 0.932),
                    (0.098, 0.948)], seg=64, zscale=0.86)
    parts["white"].append(collar.rigid("chest"))
    bow_c = np.array([0, 0.935, 0.098])
    for s in (1, -1):
        loop = ellipsoid(bow_c + [s * 0.030, 0.002, 0], (0.030, 0.019, 0.010), 24, 12)
        parts["violet"].append(loop.rigid("chest"))
        tail = capsule(bow_c + [s * 0.008, -0.006, 0.004], bow_c + [s * 0.024, -0.050, 0.006], 0.008, 12, 8)
        parts["violet"].append(tail.rigid("chest"))
    parts["violet"].append(ellipsoid(bow_c + [0, 0, 0.004], (0.013, 0.014, 0.011), 16, 10).rigid("chest"))
    # a violet sash at the waist
    sash = lathe([(0.093, 0.745), (0.095, 0.735), (0.095, 0.71), (0.093, 0.70)], seg=64, zscale=0.82)
    for v in range(len(sash.pos)):
        sash.pos[v, 0] *= 1.03
        sash.pos[v, 2] *= 1.03
    parts["violet"].append(band_weights(sash, [(0.75, "chest"), (0.69, "spine")]))
    for s, side in ((1, "left"), (-1, "right")):
        # arms: puffed sleeves, then skin
        ua, la, hd = w[side + "UpperArm"], w[side + "LowerArm"], w[side + "Hand"]
        sleeve = ellipsoid(ua + [s * 0.045, 0, 0], (0.068, 0.055, 0.055), 28, 16)
        parts["dress"].append(sleeve.rigid(side + "UpperArm"))
        cuff = lathe([(0.050, 0.0), (0.052, -0.012), (0.042, -0.016)], seg=28)
        # the cuff is around the arm (along X): turn the lathe's Y onto the arm
        cp = cuff.pos.copy()
        cuff.pos = np.stack([ua[0] + s * (0.10 - cp[:, 1]), ua[1] + cp[:, 0], ua[2] + cp[:, 2]], axis=1)
        parts["white"].append(cuff.rigid(side + "UpperArm"))
        parts["skin"].append(capsule(ua + [s * 0.05, 0, 0], la, 0.028).rigid(side + "UpperArm"))
        parts["skin"].append(capsule(la, hd + [s * -0.005, 0, 0], 0.026, rb=0.024).rigid(side + "LowerArm"))
        hand = ellipsoid(hd + [s * 0.032, 0, 0.004], (0.036, 0.024, 0.032), 24, 14)
        parts["skin"].append(hand.rigid(side + "Hand"))
        thumb = capsule(hd + [s * 0.012, -0.004, 0.022], hd + [s * 0.040, -0.006, 0.040], 0.010, 12, 8)
        parts["skin"].append(thumb.rigid(side + "Hand"))
        # legs: skin, white knee socks, violet shoes
        ul, ll, ft = w[side + "UpperLeg"], w[side + "LowerLeg"], w[side + "Foot"]
        parts["skin"].append(capsule(ul + [0, 0.02, 0], ll, 0.047, rb=0.040).rigid(side + "UpperLeg"))
        parts["white"].append(capsule(ll + [0, -0.03, 0], ft + [0, 0.01, 0], 0.040, rb=0.034).rigid(side + "LowerLeg"))
        sock_top = lathe([(0.043, 0.0), (0.044, -0.012), (0.042, -0.018)], seg=28,
                         center=(ll[0], ll[1] - 0.025, ll[2]))
        parts["white"].append(sock_top.rigid(side + "LowerLeg"))
        shoe = ellipsoid(ft + [0, -0.012, 0.032], (0.048, 0.040, 0.082), 28, 16)
        # a flat sole
        shoe.pos[:, 1] = np.maximum(shoe.pos[:, 1], 0.002)
        shoe.normals = None
        parts["violet"].append(shoe.rigid(side + "Foot"))
    return parts


def hair_parts():
    """The hair: a shell over the head that leaves the face (bangs in front, locks at the sides,
    a bob at the back), and twin tails on the tails' bones."""
    parts = {"hair": [], "violet": []}
    nu, nv = 144, 40

    def edge(az):
        # how far down the hair reaches (latitude, degrees) at an azimuth (0 = the front)
        a = abs(az)
        if a <= 42:
            # bangs: scallops, their points lower
            k = 7
            u = (az + 42) / 84 * k
            f = u - math.floor(u)
            return 31 - 13 * (1 - abs(2 * f - 1)) ** 1.6
        if a <= 62:
            t = (a - 42) / 20
            t = t * t * (3 - 2 * t)
            return 27 + (-48 - 27) * t
        if a <= 110:
            t = (a - 62) / 48
            return -48 + (-30 + 48) * t * t * (3 - 2 * t)
        t = min(1.0, (a - 110) / 40)
        return -30 + (-74 + 30) * t * t * (3 - 2 * t)

    pos = []
    for j in range(nv + 1):
        t = j / nv
        for i in range(nu):
            az = -180 + 360 * i / nu
            lat = math.radians(90 - t * (90 - edge(az)))
            lon = math.radians(az)
            # fuller toward the ends
            sx = 1.075 + 0.05 * t * t
            sy = 1.06
            p = HEAD_C + np.array([HEAD_R[0] * sx * math.cos(lat) * math.sin(lon),
                                   HEAD_R[1] * sy * math.sin(lat) + 0.006,
                                   HEAD_R[2] * sx * math.cos(lat) * math.cos(lon) - 0.004])
            pos.append(p)
    shell = orient(Part(pos, grid_tris(nu, nv)), HEAD_C)
    parts["hair"].append(shell.rigid("head"))
    # an ahoge: a lock standing up on the crown
    tip = HEAD_C + [0.0, HEAD_R[1] * 1.06 + 0.075, 0.02]
    lock = capsule(HEAD_C + [0.0, HEAD_R[1] * 1.02, 0.0], tip, 0.016, 16, 10, rb=0.003)
    parts["hair"].append(lock.rigid("head"))
    # twin tails: a teardrop along each chain of tail bones, blended between them
    for side in ("L", "R"):
        names = [f"tail{side}{i}" for i in range(TAIL + 1)]
        pts = [WORLD[n] for n in names]
        prof = []
        total = sum(np.linalg.norm(pts[i + 1] - pts[i]) for i in range(TAIL))
        steps = 40
        seg = 28
        verts, joints, weights = [], [], []
        for k in range(steps + 1):
            u = k / steps
            dist = u * total
            # where along the chain
            acc = 0
            for i in range(TAIL):
                l = np.linalg.norm(pts[i + 1] - pts[i])
                if dist <= acc + l or i == TAIL - 1:
                    f = min(1.0, (dist - acc) / l)
                    c = pts[i] + (pts[i + 1] - pts[i]) * f
                    d = (pts[i + 1] - pts[i]) / l
                    bi, fi = i, f
                    break
                acc += l
            r = 0.026 + 0.05 * math.sin(math.pi * min(1.0, u * 1.25)) ** 0.8 * (1 - u) ** 0.35
            r = max(r, 0.002)
            if u > 0.97:
                r = 0.002
            up = np.array([0, 0, 1.0])
            e1 = np.cross(d, up)
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(d, e1)
            for a in range(seg):
                th = 2 * math.pi * a / seg
                verts.append(c + (e1 * math.cos(th) + e2 * math.sin(th) * 0.75) * r)
                # weight between the bone at the start of this stretch and the next
                ja, jb = BONE_INDEX[names[bi]], BONE_INDEX[names[bi + 1]]
                wb = fi * fi * (3 - 2 * fi) if bi + 1 < TAIL else 0.0
                joints.append((ja, jb, 0, 0))
                weights.append((1 - wb, wb, 0, 0))
        tri = grid_tris(seg, steps)
        parts["hair"].append(Part(verts, tri, np.array(joints), np.array(weights)))
        # a scrunchie where it's tied
        root = pts[0] + [0, -0.012, 0]
        tie = ellipsoid(root, (0.034, 0.024, 0.034), 24, 12)
        parts["violet"].append(tie.rigid(names[0]))
    return parts


# ---------------------------------------------------------------------------
# the face: shapes on the head, and their expressions (morph targets)
# ---------------------------------------------------------------------------
EXPRESSIONS = ["blink", "blinkLeft", "blinkRight", "happy", "angry", "sad", "relaxed", "surprised",
               "aa", "ih", "ou", "ee", "oh", "blush"]


def on_head(x, y, lift):
    """A point of the face (x, y from the head's centre) on the head's surface, lift above it."""
    rx, ry, rz = HEAD_R + lift
    q = 1 - (x / rx) ** 2 - (y / ry) ** 2
    z = rz * math.sqrt(max(q, 0.0))
    return HEAD_C + np.array([x, y, z])


def disc_grid(rings, segs):
    """A disc's grid: a centre then rings; returns [(r, th)] and the triangles."""
    rt = [(0.0, 0.0)]
    for j in range(1, rings + 1):
        for i in range(segs):
            rt.append((j / rings, 2 * math.pi * i / segs))
    tri = []
    for i in range(segs):
        tri.append((0, 1 + i, 1 + (i + 1) % segs))
    for j in range(1, rings):
        b0 = 1 + (j - 1) * segs
        b1 = 1 + j * segs
        for i in range(segs):
            a, b = b0 + i, b0 + (i + 1) % segs
            c, d = b1 + i, b1 + (i + 1) % segs
            tri.append((a, c, b))
            tri.append((b, c, d))
    return rt, np.array(tri)


def band(curve, half, r, th):
    """A point of a thin band along a curve (s from -1 to 1): the grid's r, th map onto it, its
    centre to the curve's middle, so a disc and a band morph into each other."""
    s = r * math.cos(th)
    x, y = curve(s)
    # the curve's normal, by a small step
    x2, y2 = curve(min(1.0, s + 1e-3))
    x1, y1 = curve(max(-1.0, s - 1e-3))
    tx, ty = x2 - x1, y2 - y1
    ln = math.hypot(tx, ty) or 1
    nx, ny = -ty / ln, tx / ln
    h = half(s) if callable(half) else half
    return x + nx * h * r * math.sin(th), y + ny * h * r * math.sin(th)


def ellipse(a, b, cx=0.0, cy=0.0):
    return lambda r, th: (cx + a * r * math.cos(th), cy + b * r * math.sin(th))


def lidded(shape, lid):
    """A shape with what's above the lid line (lid(x)) pressed down onto it."""
    def f(r, th):
        x, y = shape(r, th)
        l = lid(x)
        if y > l:
            y = l + (y - l) * 0.1
        return x, y
    return f


def point(x, y):
    return lambda r, th: (x, y)


EYE_A, EYE_B = 0.029, 0.040     # the open eye's half width and height
EYE_Y = -0.012                  # its centre below the head's centre
EYE_X = 0.066


def eye_shapes(side):
    """{target: {part: shape(r, th) -> (x, y)}} for one eye, x outward positive (side mirrors it);
    "base" is the open eye."""
    a, b = EYE_A, EYE_B
    lash_curve = lambda s: (1.04 * a * math.sin(1.22 * s), 1.04 * b * math.cos(1.22 * s))
    lash_half = lambda s: 0.0042 + 0.0016 * max(0.0, s * side)   # thicker at the outer corner
    closed = lambda s: (a * 1.02 * s, -0.012 - 0.008 * (1 - s * s))
    happy = lambda s: (a * 0.98 * s, -0.008 + 0.014 * (1 - s * s))
    shapes = {}
    shapes["base"] = {
        "iris": ellipse(a, b),
        "pupil": ellipse(0.58 * a, 0.58 * b, 0, -0.006),
        "lash": lambda r, th: band(lash_curve, lash_half, r, th),
        "hl1": ellipse(0.0095, 0.0105, -0.011, 0.016),
        "hl2": ellipse(0.0042, 0.0042, 0.010, -0.019),
    }
    def to_curve(curve, thick):
        return {
            "iris": lambda r, th: band(curve, thick, r, th),
            "pupil": lambda r, th: band(curve, thick * 0.6, r, th),
            "lash": lambda r, th: band(lambda s: curve(0.95 * s), 0.0038, r, th),
            "hl1": point(*curve(0)),
            "hl2": point(*curve(0)),
        }
    shapes["blink"] = to_curve(closed, 0.0032)
    shapes["happy"] = to_curve(happy, 0.0034)
    # half shut, the lid flat
    lid = lambda x: 0.004
    shapes["relaxed"] = {
        "iris": lidded(ellipse(a, b), lid),
        "pupil": lidded(ellipse(0.58 * a, 0.58 * b, 0, -0.006), lid),
        "lash": lambda r, th: band(lambda s: (1.02 * a * s, 0.004 + 0.003 * (1 - s * s)), 0.0040, r, th),
        "hl1": point(-0.011, 0.002),
        "hl2": ellipse(0.0042, 0.0042, 0.010, -0.019),
    }
    # angry: the lids slant down toward the nose; sad: down toward the ears
    for name, l0, slope in (("angry", 0.014, 0.42), ("sad", 0.016, -0.36)):
        lid = (lambda l0, slope: lambda x: l0 + slope * x * side)(l0, slope)
        shapes[name] = {
            "iris": lidded(ellipse(a, b), lid),
            "pupil": lidded(ellipse(0.58 * a, 0.58 * b, 0, -0.006), lid),
            "lash": (lambda lid: lambda r, th: band(lambda s: (1.0 * a * s, lid(1.0 * a * s) + 0.002), 0.0042, r, th))(lid),
            "hl1": ellipse(0.0085, 0.0090, -0.011, min(0.006, lid(-0.011) - 0.008)),
            "hl2": ellipse(0.0042, 0.0042, 0.010, -0.019),
        }
    k = 1.14
    shapes["surprised"] = {
        "iris": ellipse(a * k, b * k, 0, 0.002),
        "pupil": ellipse(0.46 * a, 0.46 * b, 0, -0.002),
        "lash": lambda r, th: band(lambda s: (1.04 * k * a * math.sin(1.22 * s), 0.002 + 1.04 * k * b * math.cos(1.22 * s)), lash_half, r, th),
        "hl1": ellipse(0.011, 0.012, -0.012, 0.020),
        "hl2": ellipse(0.0048, 0.0048, 0.011, -0.020),
    }
    return shapes


def brow_shapes(side):
    curve0 = lambda s: (0.026 * s, 0.0045 * (1 - s * s))
    half = lambda s: 0.0034 - 0.0012 * s * side   # thicker toward the nose
    def moved(dy0, slope, arch=1.0):
        # slope raises the outer end
        return lambda r, th: band(lambda s: (0.026 * s, arch * 0.0045 * (1 - s * s) + dy0 + slope * s * side), half, r, th)
    return {
        "base": {"brow": lambda r, th: band(curve0, half, r, th)},
        "angry": {"brow": moved(-0.006, 0.0075, 0.4)},
        "sad": {"brow": moved(0.002, -0.0065, 0.6)},
        "surprised": {"brow": moved(0.011, 0.0, 1.5)},
        "happy": {"brow": moved(0.004, 0.0)},
        "relaxed": {"brow": moved(-0.002, -0.002, 0.7)},
    }


def mouth_shapes():
    rest = lambda s: (0.017 * s, -0.0045 * (1 - s * s))
    def oval(a, b, cy, smile=0.0):
        return lambda r, th: (a * r * math.cos(th), cy + b * r * math.sin(th) - smile * (1 - (r * math.cos(th)) ** 2))
    def d_shape(a, b, cy):
        def f(r, th):
            s = math.sin(th)
            return a * r * math.cos(th), cy + (b * r * s if s < 0 else 0.22 * b * r * s) - 0.004 * (1 - (r * math.cos(th)) ** 2)
        return f
    return {
        "base": {"mouth": lambda r, th: band(rest, 0.0019, r, th)},
        "aa": {"mouth": oval(0.021, 0.024, -0.009)},
        "ih": {"mouth": oval(0.025, 0.009, -0.003, 0.002)},
        "ou": {"mouth": oval(0.010, 0.012, -0.004)},
        "ee": {"mouth": oval(0.023, 0.014, -0.005, 0.002)},
        "oh": {"mouth": oval(0.016, 0.020, -0.007)},
        "happy": {"mouth": d_shape(0.022, 0.021, -0.002)},
        "angry": {"mouth": lambda r, th: band(lambda s: (0.016 * s, -0.002 + 0.0045 * (1 - s * s)), 0.0019, r, th)},
        "sad": {"mouth": lambda r, th: band(lambda s: (0.012 * s, -0.003 + 0.0065 * (1 - s * s)), 0.0018, r, th)},
        "surprised": {"mouth": oval(0.010, 0.013, -0.006)},
        "relaxed": {"mouth": lambda r, th: band(lambda s: (0.019 * s, -0.0055 * (1 - s * s)), 0.0019, r, th)},
    }


def face_parts():
    """{material: Part} for the face, each with its morph targets (EXPRESSIONS)."""
    out = {}

    def add(material, center, shapes, part, lift, mirror, rings=6, segs=32):
        rt, tri = disc_grid(rings, segs)
        base = shapes["base"][part]
        def place(shape):
            pts = []
            for r, th in rt:
                x, y = shape(r, th)
                pts.append(on_head(center[0] + x, center[1] + y, lift))
            return np.array(pts)
        p0 = place(base)
        prt = Part(p0, tri)
        # the triangles face the viewer (+Z); the mirrored side keeps the same winding: its
        # shapes are built in the same frame
        prt.rigid("head")
        nrm = (p0 - HEAD_C) / (HEAD_R + lift) ** 2
        prt.normals = nrm / np.linalg.norm(nrm, axis=1, keepdims=True)
        for name in EXPRESSIONS:
            prt.targets[name] = np.zeros_like(p0)
        for name, sh in shapes.items():
            if name == "base" or part not in sh:
                continue
            prt.targets[name] = place(sh[part]) - p0
        return prt

    groups = {}
    for side, s in (("left", 1), ("right", -1)):
        ec = (s * EYE_X, EYE_Y)
        es = eye_shapes(s)
        # this eye's blink, and a one-eyed blink for this side only
        for part in ("iris", "pupil", "lash", "hl1", "hl2"):
            lift = {"iris": 0.0016, "pupil": 0.0022, "lash": 0.0028, "hl1": 0.0034, "hl2": 0.0034}[part]
            mat = {"iris": "iris", "pupil": "pupil", "lash": "lash", "hl1": "white_face", "hl2": "white_face"}[part]
            rings, segs = (6, 32) if part in ("iris", "pupil", "lash") else (3, 16)
            prt = add(mat, ec, es, part, lift, s, rings, segs)
            prt.targets["blink" + ("Left" if s > 0 else "Right")] = prt.targets["blink"].copy()
            groups.setdefault(mat, []).append(prt)
        bc = (s * 0.066, 0.050)
        prt = add("brow", bc, brow_shapes(s), "brow", 0.0018, s, 4, 24)
        groups.setdefault("brow", []).append(prt)
        # blush: nothing (a point) until happy, relaxed or blush shows it
        cc = (s * 0.104, -0.062)
        blush = {"base": {"b": point(0, 0)}}
        for name in ("happy", "relaxed", "blush"):
            blush[name] = {"b": ellipse(0.028, 0.013)}
        prt = add("blush", cc, blush, "b", 0.0010, s, 4, 24)
        groups.setdefault("blush", []).append(prt)
    prt = add("mouth", (0.0, -0.088), mouth_shapes(), "mouth", 0.0016, 1, 6, 32)
    groups.setdefault("mouth", []).append(prt)

    for mat, plist in groups.items():
        m = merge(plist, oriented=True)
        m.targets = {name: np.concatenate([p.targets[name] for p in plist]) for name in EXPRESSIONS}
        out[mat] = m
    return out


# ---------------------------------------------------------------------------
# glTF writing
# ---------------------------------------------------------------------------
class GLB:
    def __init__(self):
        self.json = {"asset": {"version": "2.0", "generator": "kagex tools/assets/make_vrm.py"},
                     "buffers": [{"byteLength": 0}], "bufferViews": [], "accessors": []}
        self.bin = bytearray()

    def view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target is not None:
            v["target"] = target
        self.bin += data
        self.json["bufferViews"].append(v)
        return len(self.json["bufferViews"]) - 1

    def accessor(self, arr, type_, ctype, target=None, minmax=False):
        dt = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}[ctype]
        a = np.ascontiguousarray(np.asarray(arr).astype(dt))
        acc = {"bufferView": self.view(a.tobytes(), target), "componentType": ctype,
               "count": int(a.shape[0]), "type": type_}
        if minmax:
            flat = a.reshape(a.shape[0], -1)
            acc["min"] = [float(x) for x in flat.min(axis=0)]
            acc["max"] = [float(x) for x in flat.max(axis=0)]
        self.json["accessors"].append(acc)
        return len(self.json["accessors"]) - 1

    def write(self, path):
        while len(self.bin) % 4:
            self.bin.append(0)
        self.json["buffers"][0]["byteLength"] = len(self.bin)
        js = json.dumps(self.json, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        while len(js) % 4:
            js += b" "
        total = 12 + 8 + len(js) + 8 + len(self.bin)
        with open(path, "wb") as f:
            f.write(struct.pack("<4sII", b"glTF", 2, total))
            f.write(struct.pack("<I4s", len(js), b"JSON"))
            f.write(js)
            f.write(struct.pack("<I4s", len(self.bin), b"BIN\0"))
            f.write(self.bin)


def linear(c):
    """A colour factor, 0-1, as it should look. glTF's factors are linear, but krkrthreepp's MToon
    shader draws them as given, without converting them to the screen's sRGB (as it does a
    texture's colours, which VRoid's models use with factors of 1), so they're written as sRGB:
    linear ones came out dark."""
    return [round(v / 255.0, 5) for v in c]


MATERIALS = {
    # name: (lit, shade, outline, alpha, double sided)
    "skin": (SKIN, SKIN_SHADE, True, None, False),
    "dress": (DRESS, DRESS_SHADE, True, None, True),
    "white": (WHITE, WHITE_SHADE, True, None, True),
    "violet": (VIOLET, VIOLET_SHADE, True, None, False),
    "hair": (HAIR, HAIR_SHADE, True, None, True),
    "iris": (IRIS, IRIS, False, None, False),
    "pupil": (PUPIL, PUPIL, False, None, False),
    "lash": (LASH, LASH, False, None, False),
    "white_face": (WHITE, WHITE, False, None, False),
    "brow": (HAIR_SHADE, HAIR_SHADE, False, None, False),
    "mouth": (MOUTH, MOUTH, False, None, False),
    "blush": (BLUSH, BLUSH, False, 0.55, False),
}


def material(name):
    lit, shade, outline, alpha, double = MATERIALS[name]
    m = {"name": name,
         "pbrMetallicRoughness": {"baseColorFactor": linear(lit) + [alpha if alpha is not None else 1.0],
                                  "metallicFactor": 0.0, "roughnessFactor": 1.0},
         "alphaMode": "BLEND" if alpha is not None else "OPAQUE",
         "doubleSided": double,
         "extensions": {"VRMC_materials_mtoon": {
             "specVersion": "1.0",
             "transparentWithZWrite": False,
             "renderQueueOffsetNumber": 0,
             "shadeColorFactor": linear(shade),
             "shadingShiftFactor": -0.1 if outline else 0.0,
             "shadingToonyFactor": 0.92,
             "giEqualizationFactor": 0.9,
             "matcapFactor": [0, 0, 0],
             "parametricRimColorFactor": [0, 0, 0],
             "rimLightingMixFactor": 1.0,
             "parametricRimFresnelPowerFactor": 5.0,
             "parametricRimLiftFactor": 0.0,
             "outlineWidthMode": "worldCoordinates" if outline else "none",
             "outlineWidthFactor": 0.0032 if outline else 0.0,
             "outlineColorFactor": linear(NAVY),
             "outlineLightingMixFactor": 1.0,
             "uvAnimationScrollXSpeedFactor": 0.0,
             "uvAnimationScrollYSpeedFactor": 0.0,
             "uvAnimationRotationSpeedFactor": 0.0}}}
    if not outline:
        # the face's shapes: lit evenly, so they look drawn on
        m["extensions"]["VRMC_materials_mtoon"]["shadingToonyFactor"] = 1.0
        m["extensions"]["VRMC_materials_mtoon"]["shadingShiftFactor"] = -1.0
    return m


def add_mesh(g, name, prims, targets=None):
    """prims: [(material index, Part)]; every Part has the same targets (names) or none."""
    out = {"name": name, "primitives": []}
    for mi, p in prims:
        pos = p.pos.astype(np.float32)
        attrs = {
            "POSITION": g.accessor(pos, "VEC3", 5126, 34962, True),
            "NORMAL": g.accessor(p.smooth_normals().astype(np.float32), "VEC3", 5126, 34962),
            "JOINTS_0": g.accessor(p.joints.astype(np.uint16), "VEC4", 5123, 34962),
            "WEIGHTS_0": g.accessor((p.weights / p.weights.sum(axis=1, keepdims=True)).astype(np.float32), "VEC4", 5126, 34962),
        }
        prim = {"attributes": attrs, "indices": g.accessor(p.tri.reshape(-1).astype(np.uint32), "SCALAR", 5125, 34963),
                "material": mi, "mode": 4}
        if targets:
            prim["targets"] = [{"POSITION": g.accessor(p.targets[t].astype(np.float32), "VEC3", 5126, 34962, True)}
                               for t in targets]
        out["primitives"].append(prim)
    if targets:
        out["extras"] = {"targetNames": list(targets)}
        out["weights"] = [0.0] * len(targets)
    g.json.setdefault("meshes", []).append(out)
    return len(g.json["meshes"]) - 1


def bone_nodes(g, with_tails=True):
    """The skeleton's nodes; returns {bone: node index} and the root node's index."""
    nodes = g.json.setdefault("nodes", [])
    index = {}
    names = [b for b in BONES if with_tails or not b[0].startswith("tail")]
    for name, parent, t in names:
        index[name] = len(nodes)
        nodes.append({"name": name, "translation": [float(x) for x in t]})
    for name, parent, t in names:
        if parent is not None:
            nodes[index[parent]].setdefault("children", []).append(index[name])
    root = len(nodes)
    nodes.append({"name": "Root", "children": [index["hips"]]})
    return index, root


def build_model(path):
    g = GLB()
    index, root = bone_nodes(g)
    mats = list(MATERIALS)
    g.json["materials"] = [material(m) for m in mats]
    # the body
    body = {}
    for k, v in body_parts().items():
        body.setdefault(k, []).extend(v)
    for k, v in hair_parts().items():
        body.setdefault(k, []).extend(v)
    body_mesh = add_mesh(g, "Body", [(mats.index(k), merge(v)) for k, v in body.items() if v])
    face = face_parts()
    face_order = [m for m in mats if m in face]
    face_mesh = add_mesh(g, "Face", [(mats.index(m), face[m]) for m in face_order], EXPRESSIONS)
    # the skin: every bone a joint (VRM's bones are found among them), bound where it stands
    joints = [index[b[0]] for b in BONES]
    ibm = []
    for b in BONES:
        m = np.eye(4)
        m[:3, 3] = -WORLD[b[0]]
        ibm.append(m.T.reshape(-1))   # column-major
    g.json["skins"] = [{"name": "Armature", "joints": joints, "skeleton": index["hips"],
                        "inverseBindMatrices": g.accessor(np.array(ibm), "MAT4", 5126)}]
    nodes = g.json["nodes"]
    body_node = len(nodes)
    nodes.append({"name": "Body", "mesh": body_mesh, "skin": 0})
    face_node = len(nodes)
    nodes.append({"name": "Face", "mesh": face_mesh, "skin": 0})
    nodes[root]["children"] += [body_node, face_node]
    g.json["scenes"] = [{"name": "Scene", "nodes": [root]}]
    g.json["scene"] = 0

    # VRM: who she is, her bones, her expressions
    def binds(*names):
        return [{"node": face_node, "index": EXPRESSIONS.index(n), "weight": 1.0} for n in names]
    preset = {}
    for n in ("happy", "angry", "sad", "relaxed", "surprised", "aa", "ih", "ou", "ee", "oh",
              "blink", "blinkLeft", "blinkRight"):
        e = {"morphTargetBinds": binds(n), "isBinary": False,
             "overrideBlink": "none", "overrideLookAt": "none", "overrideMouth": "none"}
        if n in ("happy", "angry", "sad", "relaxed", "surprised"):
            # their lids are where a blink would take them: a blink fades out as they show
            e["overrideBlink"] = "blend"
        preset[n] = e
    preset["neutral"] = {"morphTargetBinds": [], "isBinary": False, "overrideBlink": "none",
                         "overrideLookAt": "none", "overrideMouth": "none"}
    custom = {"blush": {"morphTargetBinds": binds("blush"), "isBinary": False, "overrideBlink": "none",
                        "overrideLookAt": "none", "overrideMouth": "none"}}
    vrm = {
        "specVersion": "1.0",
        "meta": {
            "name": "Vee", "version": "1.0", "authors": ["kagex"],
            "copyrightInformation": "kagex sample (tools/assets/make_vrm.py)",
            "contactInformation": "https://github.com/krkren/kagex",
            "licenseUrl": "https://vrm.dev/licenses/1.0/",
            "avatarPermission": "everyone",
            "allowExcessivelyViolentUsage": False,
            "allowExcessivelySexualUsage": False,
            "commercialUsage": "corporation",
            "allowPoliticalOrReligiousUsage": False,
            "allowAntisocialOrHateUsage": False,
            "creditNotation": "unnecessary",
            "allowRedistribution": True,
            "modification": "allowModificationRedistribution",
        },
        "humanoid": {"humanBones": {b: {"node": index[b]} for b in HUMANOID}},
        "expressions": {"preset": preset, "custom": custom},
    }
    # the twin tails swing; the head and the body keep them out
    colliders = [
        {"node": index["head"], "shape": {"sphere": {"offset": [float(x) for x in (HEAD_C - WORLD["head"])], "radius": 0.19}}},
        {"node": index["chest"], "shape": {"capsule": {"offset": [0, 0.0, 0], "radius": 0.11, "tail": [0, 0.13, 0]}}},
        {"node": index["leftUpperArm"], "shape": {"capsule": {"offset": [0.02, 0, 0], "radius": 0.05, "tail": [0.17, 0, 0]}}},
        {"node": index["rightUpperArm"], "shape": {"capsule": {"offset": [-0.02, 0, 0], "radius": 0.05, "tail": [-0.17, 0, 0]}}},
    ]
    springs = []
    for side in ("L", "R"):
        springs.append({"name": "tail" + side, "colliderGroups": [0],
                        "joints": [{"node": index[f"tail{side}{i}"], "hitRadius": 0.035,
                                    "stiffness": 0.9 if i < TAIL else 0.0, "gravityPower": 0.35,
                                    "gravityDir": [0, -1, 0], "dragForce": 0.35}
                                   for i in range(TAIL + 1)]})
    g.json["extensions"] = {
        "VRMC_vrm": vrm,
        "VRMC_springBone": {"specVersion": "1.0", "colliders": colliders,
                            "colliderGroups": [{"name": "body", "colliders": [0, 1, 2, 3]}],
                            "springs": springs},
    }
    g.json["extensionsUsed"] = ["VRMC_vrm", "VRMC_springBone", "VRMC_materials_mtoon"]
    g.write(path)
    return os.path.getsize(path)


# ---------------------------------------------------------------------------
# motions
# ---------------------------------------------------------------------------
def quat_axis(axis, deg):
    a = math.radians(deg) / 2
    v = np.array(axis, dtype=np.float64)
    v = v / np.linalg.norm(v)
    return np.array([v[0] * math.sin(a), v[1] * math.sin(a), v[2] * math.sin(a), math.cos(a)])


def qmul(a, b):
    x1, y1, z1, w1 = a
    x2, y2, z2, w2 = b
    return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
                     w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])


def qconj(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])


def qrot(q, v):
    p = np.array([v[0], v[1], v[2], 0.0])
    r = qmul(qmul(q, p), qconj(q))
    return r[:3]


def euler(x=0, y=0, z=0):
    """A turn about X, then Y, then Z (degrees), in the parent's frame."""
    return qmul(quat_axis((0, 0, 1), z), qmul(quat_axis((0, 1, 0), y), quat_axis((1, 0, 0), x)))


def arc(a, b):
    """The shortest turn taking direction a to b."""
    a = np.asarray(a, dtype=np.float64) / np.linalg.norm(a)
    b = np.asarray(b, dtype=np.float64) / np.linalg.norm(b)
    c = np.cross(a, b)
    d = float(np.dot(a, b))
    if d < -0.999999:
        axis = np.cross(a, [0, 1, 0])
        if np.linalg.norm(axis) < 1e-6:
            axis = np.cross(a, [1, 0, 0])
        return quat_axis(axis, 180)
    q = np.array([c[0], c[1], c[2], 1 + d])
    return q / np.linalg.norm(q)


def norm(v):
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return np.asarray(a, dtype=np.float64) + (np.asarray(b, dtype=np.float64) - np.asarray(a, dtype=np.float64)) * t


def idle_pose(t, period=4.0):
    """A pose: {bone: euler degrees or ("aim", world direction)}, and the hips' offset."""
    w = math.sin(2 * math.pi * t / period)
    w2 = math.sin(2 * math.pi * t / period + 1.3)
    pose = {
        "hips": ("euler", (0, 1.5 * w2, 0.8 * w)),
        "spine": ("euler", (0.6 * w, 0, -0.5 * w)),
        "chest": ("euler", (1.2 * w, 0, -0.6 * w)),
        "neck": ("euler", (0, 0, 0)),
        "head": ("euler", (1.5 * w2 - 2, 4 * math.sin(2 * math.pi * t / period * 0.5 + 0.4), 2.2 * w2)),
    }
    for s, side in ((1, "left"), (-1, "right")):
        pose[side + "UpperArm"] = ("aim", (s * (0.30 + 0.02 * w), -1, 0.06))
        pose[side + "LowerArm"] = ("aim", (s * 0.18, -1, 0.28))
        pose[side + "Hand"] = ("aim", (s * 0.12, -1, 0.22))
        pose[side + "UpperLeg"] = ("aim", (s * 0.02, -1, 0))
        pose[side + "LowerLeg"] = ("aim", (s * 0.02, -1, 0))
        pose[side + "Foot"] = ("aim", (0, -1, 0))
    return pose, (0, 0.002 * w, 0)


def think_pose(t):
    pose, hips = idle_pose(t)
    w = math.sin(2 * math.pi * t / 4.0)
    pose["head"] = ("euler", (4 + 1.5 * w, -8, 9 + 1.5 * w))
    pose["neck"] = ("euler", (0, -3, 3))
    # the right hand at her chin, the left holding that elbow
    pose["rightUpperArm"] = ("aim", (-0.15, -0.6, 0.78))
    pose["rightLowerArm"] = ("to", WORLD["head"] + [0.0, -0.01, 0.13])
    pose["rightHand"] = ("aim", (0.15, 0.95, 0.25))
    pose["leftUpperArm"] = ("aim", (0.22, -0.92, 0.32))
    pose["leftLowerArm"] = ("aim", (-0.95, 0.05, 0.30))
    pose["leftHand"] = ("aim", (-0.9, 0.2, 0.35))
    return pose, hips


def blend_pose(a, b, t):
    """Pose a turned toward pose b by t (after both are made into local turns)."""
    return (a, b, t)


def wave_pose(t, dur=2.6):
    base, hips = idle_pose(t)
    k = smooth(t / 0.45) * smooth((dur - t) / 0.45)
    if k <= 0:
        return base, hips
    wave = dict(base)
    sway = math.sin(2 * math.pi * 2.2 * max(0.0, t - 0.3))
    wave["rightUpperArm"] = ("aim", (-0.75, 0.55, 0.20))
    wave["rightLowerArm"] = ("aim", (-0.15 + 0.38 * sway, 1, 0.12))
    wave["rightHand"] = ("aim", (-0.15 + 0.5 * sway, 1, 0.10))
    wave["head"] = ("euler", (-2, -6, -6 + 2 * sway))
    wave["chest"] = ("euler", (0, -4, -3))
    return ("blend", base, wave, k), hips


def nod_pose(t, dur=1.4):
    base, hips = idle_pose(t)
    n = dict(base)
    a = math.sin(math.pi * min(1.0, t / dur) * 2) ** 2 if t < dur else 0
    n["head"] = ("euler", (16 * a, 0, 0))
    n["neck"] = ("euler", (5 * a, 0, 0))
    return n, hips


def bow_pose(t, dur=2.4):
    base, hips = idle_pose(t)
    k = smooth(t / 0.6) * smooth((dur - t) / 0.7)
    b = dict(base)
    b["spine"] = ("euler", (12, 0, 0))
    b["chest"] = ("euler", (14, 0, 0))
    b["head"] = ("euler", (12, 0, 0))
    for s, side in ((1, "left"), (-1, "right")):
        # hands together in front
        b[side + "UpperArm"] = ("aim", (s * 0.16, -1, 0.48))
        b[side + "LowerArm"] = ("aim", (-s * 0.55, -0.85, 0.35))
        b[side + "Hand"] = ("aim", (-s * 0.5, -0.9, 0.2))
    return ("blend", base, b, k), hips


def cheer_pose(t, dur=1.8):
    base, hips = idle_pose(t)
    k = smooth(t / 0.3) * smooth((dur - t) / 0.4)
    c = dict(base)
    # a hop: down, up, down
    hop = 0.0
    crouch = 0.0
    if 0.25 <= t <= 1.45:
        u = (t - 0.25) / 1.2
        hop = max(0.0, math.sin(math.pi * 2 * u)) * 0.07
        crouch = max(0.0, -math.sin(math.pi * 2 * u)) * 1.0
    for s, side in ((1, "left"), (-1, "right")):
        c[side + "UpperArm"] = ("aim", (s * 0.55, 0.85, 0.15))
        c[side + "LowerArm"] = ("aim", (s * 0.30, 1, 0.10))
        c[side + "Hand"] = ("aim", (s * 0.25, 1, 0.05))
        c[side + "UpperLeg"] = ("aim", (s * 0.02, -1, 0.35 * crouch))
        c[side + "LowerLeg"] = ("aim", (s * 0.02, -1, -0.35 * crouch))
        c[side + "Foot"] = ("aim", (0, -1, 0))
    c["head"] = ("euler", (-6, 0, 0))
    hy = hop - 0.028 * crouch
    return ("blend", base, c, k), (0, hy * k, 0)


MOTIONS = {
    # name: (pose function, length in seconds, loops)
    "idle": (idle_pose, 4.0, True),
    "think": (think_pose, 4.0, True),
    "wave": (wave_pose, 2.6, False),
    "nod": (nod_pose, 1.4, False),
    "bow": (bow_pose, 2.4, False),
    "cheer": (cheer_pose, 1.8, False),
}

REST_DIR = {}
for _name, _parent, _t in BONES:
    for _child, _p2, _t2 in BONES:
        if _p2 == _name and not _child.startswith("tail"):
            REST_DIR.setdefault(_name, norm(_t2))
REST_DIR["leftHand"] = norm((1, 0, 0))
REST_DIR["rightHand"] = norm((-1, 0, 0))
REST_DIR["leftFoot"] = norm((0, -1, 0))
REST_DIR["rightFoot"] = norm((0, -1, 0))


def local_turns(pose):
    """{bone: local quaternion} for a pose (aims made into turns along the chain)."""
    if isinstance(pose, tuple) and pose[0] == "blend":
        _, a, b, k = pose
        qa, qb = local_turns(a), local_turns(b)
        out = {}
        for n in qa:
            x, y = qa[n], qb.get(n, qa[n])
            if np.dot(x, y) < 0:
                y = -y
            q = x + (y - x) * k
            out[n] = q / np.linalg.norm(q)
        return out
    world_rot = {}
    world_pos = {}
    out = {}
    for name, parent, t in BONES:
        if name.startswith("tail"):
            continue
        prot = world_rot[parent] if parent is not None else np.array([0, 0, 0, 1.0])
        ppos = world_pos[parent] if parent is not None else np.zeros(3)
        pos = ppos + qrot(prot, t)
        spec = pose.get(name, ("euler", (0, 0, 0)))
        if spec[0] == "euler":
            q = euler(*spec[1])
        else:
            if spec[0] == "aim":
                d = norm(spec[1])
            else:   # "to": aim at a point
                d = norm(np.asarray(spec[1]) - pos)
            # the direction in the parent's frame, from the bone's rest direction
            q = arc(REST_DIR[name], qrot(qconj(prot), d))
        out[name] = q
        world_rot[name] = qmul(prot, q)
        world_pos[name] = pos
    return out


def build_motion(path, fn, length, loops):
    g = GLB()
    names = [b for b in BONES if not b[0].startswith("tail")]
    nodes = g.json.setdefault("nodes", [])
    index = {}
    for name, parent, t in names:
        index[name] = len(nodes)
        nodes.append({"name": name, "translation": [float(x) for x in t]})
    for name, parent, t in names:
        if parent is not None:
            nodes[index[parent]].setdefault("children", []).append(index[name])
    g.json["scenes"] = [{"nodes": [index["hips"]]}]
    g.json["scene"] = 0
    fps = 30
    n = int(round(length * fps)) + 1
    times = np.array([i / fps for i in range(n)], dtype=np.float64)
    times[-1] = length
    rots = {b[0]: [] for b in names}
    hips = []
    prev = {}
    for i, t in enumerate(times):
        tt = t if not loops or i < n - 1 else 0.0   # a loop ends where it began
        pose, off = fn(tt)
        turns = local_turns(pose)
        for b in rots:
            q = turns[b]
            # keep each track on one side of the sphere, so it interpolates the short way
            if b in prev and np.dot(prev[b], q) < 0:
                q = -q
            prev[b] = q
            rots[b].append(q)
        hips.append(WORLD["hips"] + np.array(off))
    t_acc = g.accessor(times.astype(np.float32), "SCALAR", 5126, None, True)
    samplers, channels = [], []
    for b in rots:
        samplers.append({"input": t_acc, "output": g.accessor(np.array(rots[b]), "VEC4", 5126),
                         "interpolation": "LINEAR"})
        channels.append({"sampler": len(samplers) - 1, "target": {"node": index[b], "path": "rotation"}})
    samplers.append({"input": t_acc, "output": g.accessor(np.array(hips), "VEC3", 5126), "interpolation": "LINEAR"})
    channels.append({"sampler": len(samplers) - 1, "target": {"node": index["hips"], "path": "translation"}})
    g.json["animations"] = [{"name": os.path.splitext(os.path.basename(path))[0], "samplers": samplers,
                             "channels": channels}]
    g.json["extensionsUsed"] = ["VRMC_vrm_animation"]
    g.json["extensions"] = {"VRMC_vrm_animation": {
        "specVersion": "1.0", "humanoid": {"humanBones": {b: {"node": index[b]} for b in HUMANOID}}}}
    g.write(path)
    return os.path.getsize(path)


def build_prop(path):
    """A puffy five-pointed star, its two animations, as a glTF binary."""
    g = GLB()
    outer, inner, depth = 0.5, 0.21, 0.17
    rim = []
    for k in range(10):
        a = math.pi / 2 + k * math.pi / 5
        r = outer if k % 2 == 0 else inner
        rim.append((r * math.cos(a), r * math.sin(a), 0.0))
    pos, nrm = [], []
    for front in (1, -1):
        tip = (0.0, 0.0, front * depth)
        for k in range(10):
            a, b = rim[k], rim[(k + 1) % 10]
            tri = (tip, a, b) if front > 0 else (tip, b, a)
            n = np.cross(np.subtract(tri[1], tri[0]), np.subtract(tri[2], tri[0]))
            n = n / np.linalg.norm(n)
            for v in tri:
                pos.append(v)
                nrm.append(n)
    pos = np.array(pos, dtype=np.float32)
    nrm = np.array(nrm, dtype=np.float32)
    idx = np.arange(len(pos), dtype=np.uint32)
    g.json["materials"] = [{"name": "star", "pbrMetallicRoughness": {
        "baseColorFactor": [round(c / 255.0, 5) for c in VIOLET] + [1.0], "metallicFactor": 0.35, "roughnessFactor": 0.35},
        "emissiveFactor": [0.06, 0.02, 0.2]}]
    g.json["meshes"] = [{"name": "Star", "primitives": [{
        "attributes": {"POSITION": g.accessor(pos, "VEC3", 5126, 34962, True),
                       "NORMAL": g.accessor(nrm, "VEC3", 5126, 34962)},
        "indices": g.accessor(idx, "SCALAR", 5125, 34963), "material": 0}]}]
    g.json["nodes"] = [{"name": "Star", "mesh": 0}]
    g.json["scenes"] = [{"nodes": [0]}]
    g.json["scene"] = 0
    def track(name, length, rot, move):
        n = int(length * 30) + 1
        times = np.linspace(0, length, n)
        out = {"name": name, "samplers": [], "channels": []}
        q = np.array([quat_axis((0, 1, 0), rot(t)) for t in times])
        out["samplers"].append({"input": g.accessor(times.astype(np.float32), "SCALAR", 5126, None, True),
                                "output": g.accessor(q, "VEC4", 5126), "interpolation": "LINEAR"})
        out["channels"].append({"sampler": 0, "target": {"node": 0, "path": "rotation"}})
        if move:
            t3 = np.array([(0.0, move(t), 0.0) for t in times])
            out["samplers"].append({"input": out["samplers"][0]["input"], "output": g.accessor(t3, "VEC3", 5126),
                                    "interpolation": "LINEAR"})
            out["channels"].append({"sampler": 1, "target": {"node": 0, "path": "translation"}})
        return out
    g.json["animations"] = [
        track("spin", 3.0, lambda t: 360 * t / 3.0, None),
        track("hop", 1.2, lambda t: 360 * smooth(t / 1.2), lambda t: 0.28 * math.sin(math.pi * t / 1.2)),
    ]
    g.write(path)
    return os.path.getsize(path)


def lines():
    """{voice number: text} of anim.ks's voiced 【vee】 lines"""
    out, voice = {}, None
    with open(SCRIPT, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"\[vee\b[^\]]*\bvoice=(\d+)", line)
            if m:
                voice = int(m.group(1))
            elif line.startswith("【vee】") and voice is not None:
                out[voice] = line[len("【vee】"):]
                voice = None
    return out


def speech():
    espeak = os.environ.get("ESPEAK_NG") or shutil.which("espeak-ng")
    if not espeak:
        sys.exit("make_vrm.py speech needs eSpeak NG (espeak-ng on the PATH, or ESPEAK_NG)")
    if not shutil.which("ffmpeg"):
        sys.exit("make_vrm.py speech needs ffmpeg (with libvorbis)")
    todo = lines()
    if not todo:
        sys.exit("no voiced 【vee】 lines in " + SCRIPT)
    print(subprocess.run([espeak, "--version"], capture_output=True, text=True).stdout.strip())
    with tempfile.TemporaryDirectory() as tmp:
        for n, text in sorted(todo.items()):
            wav = os.path.join(tmp, "line.wav")
            subprocess.run([espeak, "-v", ESPEAK_VOICE, "-s", str(ESPEAK_SPEED), "-p", str(ESPEAK_PITCH),
                            "-w", wav, text], check=True)
            out = os.path.join(VOICE, "vee%06d.ogg" % n)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "4",
                            "-ar", "48000", "-ac", "1", "-map_metadata", "-1", "-fflags", "+bitexact",
                            "-flags:a", "+bitexact", out], check=True)
            print("%s: %s" % (os.path.relpath(out, ROOT), text))
    print("Now make their lip tracks: kagex-lipsync --cli make " +
          " ".join("vee%06d.ogg" % n for n in sorted(todo)))


def main(argv):
    what = [a for a in argv if not a.startswith("-")] or ["model", "motions", "prop"]
    os.makedirs(OUT, exist_ok=True)
    if "speech" in what:
        speech()
    if "model" in what:
        path = os.path.join(OUT, NAME + ".vrm")
        print(f"{path}: {build_model(path)} bytes")
    if "prop" in what:
        path = os.path.join(OUT, "star3d.glb")
        print(f"{path}: {build_prop(path)} bytes")
    if "motions" in what:
        for name, (fn, length, loops) in MOTIONS.items():
            path = os.path.join(OUT, f"{NAME}_{name}.vrma")
            print(f"{path}: {build_motion(path, fn, length, loops)} bytes")


if __name__ == "__main__":
    main(sys.argv[1:])
