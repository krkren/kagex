#!/usr/bin/env python3
"""Read and write Effekseer runtime effects (the "SKFE" binary, ``.efk``).

The layout follows the C++ runtime loader of Effekseer at commit b6035eb
(``EffectImplemented::LoadBody``, ``EffectNodeImplemented::LoadParameter``,
the ``EffectNode*::LoadRendererParameter`` functions and ``Parameter/``).
Each structure is described once, by a layout function that both reads and
writes (see ``_Codec``), so the reader and the writer cannot drift apart.

    read_efk(data) -> Effect     SKFE versions 1500, 1600-1610 and 1700-1710;
                                 also takes a whole .efkefc (first BIN_ chunk)
    write_efk(effect) -> bytes   always writes version 1610 (Effekseer 1.6)

Standard library only.  ``python3 efkformat.py --selftest <dir>`` checks the
codec against a folder of .efkefc files.

Writing an effect
=================

An ``Effect`` holds resource lists (paths of textures, models, ...) and the
top-level nodes.  A node is ``Node`` (a group that draws nothing), ``Sprite``,
``Ribbon``, ``Ring``, ``Track`` or ``Model``; nodes nest through ``children``.
Every field has the default of the Effekseer editor, so only what differs
needs writing::

    from efkformat import *

    effect = Effect(
        textures=["Texture/particle.png"],          # texture index 0
        nodes=[
            Sprite(
                texture=0, blend=ADD,
                max_generation=INFINITE,            # emit for ever
                generation_time=6,                  # one particle every 6 frames
                life=(30, 40),                      # frames, random in [30, 40]
                translation=PVA(velocity=((-0.05, 0.05), (0.1, 0.2), 0)),
                scale=Easing(start=(1, 1, 1), end=(0.2, 0.2, 1), ease=EASE_OUT_QUAD),
                color=ColorEasing(start=(255, 255, 255, 255), end=(255, 128, 64, 0)),
                fade_out=Fade(frames=10),
            ),
        ],
    )
    open("sparks.efk", "wb").write(write_efk(effect))

Value conventions
-----------------
* Units are those of the binary: distances in Effekseer units, times in
  frames (60 per second), **rotations and spawn angles in radians** (use
  ``deg(...)``: ``rotation=Fixed(deg((0, 0, 45)))``), ring angles in degrees.
* A random range is ``(min, max)``; a plain number means ``(n, n)``.
* A random vector is one ``(min, max)`` pair (or number) per axis:
  ``((-1, 1), (2, 3), 0)``.  A plain vector is ``(x, y, z)``.
* Colors are ``(r, g, b, a)`` with 0-255 ints (``(r, g, b)`` gets a = 255).
* Easing curves (``Easing``, ``FloatEasing``) take ``ease=`` one of the
  ``EASE_*`` constants; the default ``EASE_SPEED`` uses ``params`` (a, b, c of
  ``a*t^3 + b*t^2 + c*t``, linear by default; ``speed(start, end)`` makes them
  from the editor's start/end speed settings, e.g. ``speed(10, -10)``).
  ``ColorEasing``, ``Fade`` and ``RingEasing`` only have ``params``.

Transforms
----------
``translation`` / ``rotation`` / ``scale`` take one of:

* ``Fixed(value)``                        (default: no offset / scale 1)
* ``PVA(value, velocity, acceleration)``  random vectors, per frame
* ``Easing(start, end, middle=None, ease=..., params=...)``
* ``FCurve3(x=FCurve(...), y=..., z=...)``
* translation only: ``NurbsCurve(...)``, ``ViewOffset(distance)``
* rotation only: ``AxisPVA(axis, rotation, velocity, acceleration)``,
  ``AxisEasing(axis, easing=FloatEasing(...))``, ``RotateToViewpoint()``,
  ``RotateToVelocity(axis)``
* scale only: ``SinglePVA(value, velocity, acceleration)`` (uniform),
  ``FloatEasing(start, end, ...)`` (uniform), ``FCurve1(s=FCurve(...))``

``value`` / ``start`` / ``end`` left at ``None`` mean 0 for translation and
rotation and 1 for scale.

Spawning
--------
``max_generation`` (``INFINITE`` = for ever), ``life``, ``generation_time``
(frames between spawns), ``generation_offset`` (delay), ``bind_translation``
/ ``bind_rotation`` / ``bind_scale`` (``BIND_*``), ``remove_when_life_ends``,
``remove_when_parent_removed``, ``remove_when_children_removed``.
``spawn`` is ``Point(location)``, ``Sphere(radius, rotation_x, rotation_y)``,
``Circle(division, radius, angle_start, angle_end, order, axis, angle_noise)``,
``Line(division, start, end, noise, order)`` or ``ModelSpawn(...)``;
``spawn_rotation=True`` turns particles to the spawn direction.

Rendering (all node types)
--------------------------
``texture`` (index into ``Effect.textures``, -1 = none), ``blend``
(``OPACITY``, ``BLEND``, ``ADD``, ``SUB``, ``MUL``), ``filter``
(``NEAREST``/``LINEAR``), ``wrap`` (``REPEAT``/``CLAMP``/``MIRROR``),
``ztest``, ``zwrite``, ``fade_in`` / ``fade_out`` (``Fade(frames, params,
mode)``; fade-out ``mode`` ``FADEOUT_WITHIN_LIFETIME`` or
``FADEOUT_AFTER_REMOVED``), ``uv`` (``None`` or ``UVFixed``,
``UVAnimation``, ``UVScroll``, ``UVFCurve``), ``color_bind`` (inherit the
parent's color), ``drawing_priority``, ``depth_offset``, ``zsort``,
``material`` (``MATERIAL_DEFAULT``, ``MATERIAL_DISTORTION``,
``MATERIAL_LIGHTING``; ``MATERIAL_FILE`` with ``material_file``),
``alpha_cutoff`` (``AlphaCutoff``), ``falloff``, ``sound`` (``Sound``).

Node-specific
-------------
* ``Sprite``: ``billboard`` (``BILLBOARD``, ``BILLBOARD_Y_AXIS``,
  ``BILLBOARD_FIXED``, ``BILLBOARD_ROTATED``, ``BILLBOARD_DIRECTIONAL``),
  ``color``, ``vertex_colors`` (ll, lr, ul, ur) or None, ``vertex_positions``.
* ``Ribbon``: ``color``, ``vertex_colors`` (left, right), ``vertex_positions``
  (left, right), ``viewpoint_dependent``, ``spline_division``,
  ``texture_uv`` (``TextureUV``).
* ``Ring``: ``billboard`` (default fixed), ``vertex_count``, ``shape``
  (``None`` = donut, or ``Crescent(...)``), ``outer`` / ``inner`` (a fixed
  ``(radius, height)`` or ``RingPVA`` / ``RingEasing``), ``center_ratio``,
  ``outer_color`` / ``center_color`` / ``inner_color``; single values are a
  number, a ``(min, max)`` range or a ``FloatEasing``.
* ``Track``: ``size_front`` / ``size_middle`` / ``size_back``, the six
  ``color_*``, ``spline_division``, ``texture_uv``.
* ``Model``: ``model`` (index into ``Effect.models``), ``billboard``,
  ``culling``, ``color``.

``color`` (all-type color) is a fixed ``(r, g, b, a)``, ``ColorRandom(min,
max, hsv=False)``, ``ColorEasing(start, end, params)``, ``FCurveRGBA(...)``
or ``Gradient(colors, alphas)``.

Reading
=======
``read_efk`` returns the same classes, with every field filled in.  Fields of
newer or older versions than the file's keep their defaults.  ``describe(x)``
prints an object's non-default fields.  ``write_efk`` writes 1610: it turns
the 1.5 "location abs" setting into a force field (as the runtime does), and
drops the 1.7-only settings (triggers, LODs, kill rules, material gradients)
with a warning when they are set.

Not supported: versions below 1500 and from 1800 (GPU particles, collisions),
and node fields that only exist there.
"""

from __future__ import annotations

import copy
import dataclasses
import math
import os
import struct
import sys
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable

__all__ = [
    # API
    "read_efk", "write_efk", "read_efkefc_chunks", "describe", "deg", "speed",
    "FormatError", "VERSION", "INFINITE", "FLT_MAX",
    # containers
    "Effect", "Node", "Sprite", "Ribbon", "Ring", "Track", "Model",
    # values
    "Fixed", "PVA", "Easing", "FloatEasing", "SinglePVA", "AxisPVA", "AxisEasing",
    "RotateToViewpoint", "RotateToVelocity", "NurbsCurve", "ViewOffset",
    "FCurve", "FCurve1", "FCurve2", "FCurve3", "FCurveRGBA",
    "Point", "Sphere", "Circle", "Line", "ModelSpawn",
    "ColorRandom", "ColorEasing", "Gradient",
    "UVFixed", "UVAnimation", "UVScroll", "UVFCurve", "Fade", "TextureUV",
    "AlphaCutoff", "AlphaCutoffFourPoint", "Falloff", "CustomData", "MaterialFile",
    "ForceField", "LocationAbs", "KillRules", "Sound", "Crescent", "RingPVA",
    "RingEasing", "CullingSphere", "ProceduralModel",
]

VERSION = 1610          # what write_efk writes
MIN_READ_VERSION = 1500
MAX_READ_VERSION = 1710
INFINITE = 2**31 - 1    # max_generation: emit for ever
FLT_MAX = struct.unpack("<f", b"\xff\xff\x7f\x7f")[0]

# ---------------------------------------------------------------- constants
# node types
NODE_ROOT, NODE_NONE, NODE_SPRITE, NODE_RIBBON, NODE_RING, NODE_MODEL, NODE_TRACK = -1, 0, 2, 3, 4, 5, 6
# alpha blend
OPACITY, BLEND, ADD, SUB, MUL = 0, 1, 2, 3, 4
# texture filter / wrap
NEAREST, LINEAR = 0, 1
REPEAT, CLAMP, MIRROR = 0, 1, 2
# parent binding (bind_translation also takes the 3 extra values)
BIND_NOT, BIND_WHEN_CREATING, BIND_ALWAYS, BIND_NOT_ROOT = 0, 1, 2, 3
BIND_NOT_FOLLOW_PARENT, BIND_WHEN_CREATING_FOLLOW_PARENT = 4, 5
# billboard
BILLBOARD, BILLBOARD_Y_AXIS, BILLBOARD_FIXED, BILLBOARD_ROTATED, BILLBOARD_DIRECTIONAL = 0, 1, 2, 3, 4
# material
MATERIAL_DEFAULT, MATERIAL_DISTORTION, MATERIAL_LIGHTING, MATERIAL_FILE = 0, 6, 7, 128
# fade
FADEIN_ON = 1
FADEOUT_WITHIN_LIFETIME, FADEOUT_AFTER_REMOVED = 1, 2
# z sort
ZSORT_NONE, ZSORT_NORMAL, ZSORT_REVERSE = 0, 1, 2
# rendering order
ORDER_FIRST_CREATED_FIRST, ORDER_FIRST_CREATED_LAST = 0, 1
# spawn order (circle/line)
SPAWN_RANDOM, SPAWN_ORDER, SPAWN_REVERSE_ORDER = 0, 1, 2
AXIS_X, AXIS_Y, AXIS_Z = 0, 1, 2
# easing types (Easing3Type)
EASE_SPEED, EASE_LINEAR = 0, 1
EASE_IN_QUAD, EASE_OUT_QUAD, EASE_IN_OUT_QUAD = 10, 11, 12
EASE_IN_CUBIC, EASE_OUT_CUBIC, EASE_IN_OUT_CUBIC = 20, 21, 22
EASE_IN_QUART, EASE_OUT_QUART, EASE_IN_OUT_QUART = 30, 31, 32
EASE_IN_QUINT, EASE_OUT_QUINT, EASE_IN_OUT_QUINT = 40, 41, 42
EASE_IN_BACK, EASE_OUT_BACK, EASE_IN_OUT_BACK = 50, 51, 52
EASE_IN_BOUNCE, EASE_OUT_BOUNCE, EASE_IN_OUT_BOUNCE = 60, 61, 62
# fcurve edges and timeline
FCURVE_CONSTANT, FCURVE_LOOP, FCURVE_LOOP_INVERSELY = 0, 1, 2
TIMELINE_TIME, TIMELINE_PERCENT = 0, 1
# UV animation loop
UV_LOOP_ONCE, UV_LOOP, UV_LOOP_REVERSE = 0, 1, 2
# ribbon/track texture UV
UV_STRETCH, UV_TILE_PER_PARTICLE, UV_TILE = 0, 1, 2
# force fields
FF_NONE, FF_TURBULENCE, FF_FORCE, FF_WIND, FF_VORTEX, FF_DRAG, FF_GRAVITY, FF_ATTRACTIVE = 0, 1, 2, 3, 4, 7, 8, 9
FALLOFF_NONE, FALLOFF_SPHERE, FALLOFF_TUBE, FALLOFF_CONE = 0, 1, 2, 3
# custom data
CUSTOM_FIXED2D, CUSTOM_RANDOM2D, CUSTOM_EASING2D, CUSTOM_FCURVE2D = 20, 21, 22, 23
CUSTOM_FIXED4D, CUSTOM_FCURVE_COLOR, CUSTOM_DYNAMIC_INPUT = 40, 53, 60
# model culling
CULL_FRONT, CULL_BACK, CULL_DOUBLE = 0, 1, 2

__all__ += [k for k in list(globals()) if k.isupper() and k not in __all__]

_LIST_MAX = 1024


class FormatError(ValueError):
    """The data does not follow the layout the runtime loader expects."""


# ------------------------------------------------------------- normalizers
def _isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _f32(v):
    """Round to the nearest 32-bit float (what the file will hold)."""
    return struct.unpack("<f", struct.pack("<f", v))[0]


def _frange(v):
    if _isnum(v):
        return (float(v), float(v))
    a, b = v
    return (float(a), float(b))


def _irange(v):
    if _isnum(v):
        return (int(v), int(v))
    a, b = v
    return (int(a), int(b))


def _vec(n):
    def norm(v):
        if _isnum(v):
            return (float(v),) * n
        v = tuple(float(x) for x in v)
        if len(v) != n:
            raise ValueError(f"expected {n} components, got {v!r}")
        return v
    return norm


def _rvec(n):
    def norm(v):
        if _isnum(v):
            return ((float(v), float(v)),) * n
        v = tuple(v)
        if len(v) != n:
            raise ValueError(f"expected {n} (min, max) pairs, got {v!r}")
        return tuple(_frange(x) for x in v)
    return norm


def _rgba(v):
    v = tuple(int(x) for x in v)
    if len(v) == 3:
        v += (255,)
    if len(v) != 4 or not all(0 <= x <= 255 for x in v):
        raise ValueError(f"bad color {v!r}")
    return v


def _color_param(v):          # all-type color: fixed tuple or an object
    return _rgba(v) if isinstance(v, (tuple, list)) else v


def _ring_single(v):          # ring single value: number, (min, max) or FloatEasing
    if _isnum(v):
        return float(v)
    if isinstance(v, (tuple, list)):
        return _frange(v)
    return v


def _ring_location(v):        # ring location: (x, y) or RingPVA / RingEasing
    return _vec(2)(v) if isinstance(v, (tuple, list)) else v


def _rcolor(v):               # ColorEasing start/end: color or ColorRandom
    if isinstance(v, (tuple, list)):
        c = _rgba(v)
        return ColorRandom(min=c, max=c)
    return v


def _floats(n):
    return _vec(n)


def deg(v):
    """Degrees to radians, for numbers and (nested) tuples of numbers."""
    if _isnum(v):
        return math.radians(v)
    return type(v)(deg(x) for x in v) if isinstance(v, tuple) else [deg(x) for x in v]


def speed(start=0.0, end=0.0):
    """Easing params (a, b, c) from the editor's start/end speed (-30..30).

    Mirrors the editor's MathUtl.Easing: 0/0 is linear, a positive start
    speed starts fast, a negative end speed ends slowly.
    """
    g1 = _f32(math.tan((start + 45.0) / 180.0 * math.pi))
    g2 = _f32(math.tan((end + 45.0) / 180.0 * math.pi))
    c = g1
    a = _f32(g2 - g1 - _f32((1.0 - c) * 2.0))
    b = _f32((g2 - g1 - _f32(a * 3.0)) / 2.0)
    return (a, b, c)


def F(default=None, norm=None):
    """A dataclass field with a default and an input normalizer."""
    meta = {"norm": norm} if norm else {}
    if isinstance(default, list):
        return field(default_factory=lambda d=default: copy.deepcopy(d), metadata=meta)
    if dataclasses.is_dataclass(default):
        return field(default_factory=lambda d=default: copy.deepcopy(d), metadata=meta)
    return field(default=default, metadata=meta)


class _Base:
    def __post_init__(self):
        for f in dataclasses.fields(self):
            norm = f.metadata.get("norm")
            if norm is not None:
                v = getattr(self, f.name)
                if v is not None:
                    setattr(self, f.name, norm(v))


_REF = (-1, -1)               # dynamic equation reference (min, max): none
_Z3 = ((0.0, 0.0),) * 3
WHITE = (255, 255, 255, 255)

# ------------------------------------------------------------ value classes


@dataclass(eq=True)
class FCurve(_Base):
    """One F-curve channel: ``keys`` sampled every ``freq`` frames."""
    keys: list = F([], lambda v: [float(x) for x in v])
    start: int = FCURVE_CONSTANT     # behaviour before the curve
    end: int = FCURVE_CONSTANT       # behaviour after the curve
    offset: tuple = F((0.0, 0.0), _frange)   # random offset added to the values
    offset_frame: int = 0            # frame of the first key
    length: int = 0                  # frames covered by the keys
    freq: int = 10                   # sampling interval in frames


@dataclass(eq=True)
class FCurve1(_Base):
    s: FCurve = F(FCurve())
    timeline: int = TIMELINE_TIME


@dataclass(eq=True)
class FCurve2(_Base):
    x: FCurve = F(FCurve())
    y: FCurve = F(FCurve())
    timeline: int = TIMELINE_TIME


@dataclass(eq=True)
class FCurve3(_Base):
    x: FCurve = F(FCurve())
    y: FCurve = F(FCurve())
    z: FCurve = F(FCurve())
    timeline: int = TIMELINE_TIME


@dataclass(eq=True)
class FCurveRGBA(_Base):
    r: FCurve = F(FCurve())
    g: FCurve = F(FCurve())
    b: FCurve = F(FCurve())
    a: FCurve = F(FCurve())
    timeline: int = TIMELINE_TIME


@dataclass(eq=True)
class Fixed(_Base):
    """Fixed translation / rotation (radians) / scale."""
    value: tuple = F(None, _vec(3))
    ref: int = -1                    # dynamic equation index


@dataclass(eq=True)
class PVA(_Base):
    """Random initial value, velocity and acceleration (per frame)."""
    value: tuple = F(None, _rvec(3))
    velocity: tuple = F(_Z3, _rvec(3))
    acceleration: tuple = F(_Z3, _rvec(3))
    ref_value: tuple = F(_REF, _irange)
    ref_velocity: tuple = F(_REF, _irange)
    ref_acceleration: tuple = F(_REF, _irange)


@dataclass(eq=True)
class Easing(_Base):
    """Vector easing from ``start`` to ``end`` (random vectors) over the life."""
    start: tuple = F(None, _rvec(3))
    end: tuple = F(None, _rvec(3))
    middle: tuple = F(None, _rvec(3))   # None: no middle point
    ease: int = EASE_SPEED
    params: tuple = F((0.0, 0.0, 1.0), _floats(3))   # used when ease == EASE_SPEED
    channels: int = 0                # random group per axis, 8 bits each
    individual: tuple = None         # per-axis ease types (3), or None
    ref_start: tuple = F(_REF, _irange)
    ref_end: tuple = F(_REF, _irange)
    ref_middle: tuple = F(_REF, _irange)


@dataclass(eq=True)
class FloatEasing(_Base):
    """Scalar easing (uniform scale, ring values, axis rotation, alpha cutoff)."""
    start: tuple = F(None, _frange)
    end: tuple = F(None, _frange)
    middle: tuple = F(None, _frange)
    ease: int = EASE_SPEED
    params: tuple = F((0.0, 0.0, 1.0), _floats(3))
    channels: int = 0
    individual: int = None           # ease type override, or None
    ref_start: tuple = F(_REF, _irange)
    ref_end: tuple = F(_REF, _irange)
    ref_middle: tuple = F(_REF, _irange)


SingleEasing = FloatEasing


@dataclass(eq=True)
class SinglePVA(_Base):
    """Uniform scale: random value, velocity, acceleration."""
    value: tuple = F((1.0, 1.0), _frange)
    velocity: tuple = F((0.0, 0.0), _frange)
    acceleration: tuple = F((0.0, 0.0), _frange)


@dataclass(eq=True)
class AxisPVA(_Base):
    """Rotation around a (random) axis, angle/velocity/acceleration in radians."""
    axis: tuple = F(((0.0, 0.0), (1.0, 1.0), (0.0, 0.0)), _rvec(3))
    rotation: tuple = F((0.0, 0.0), _frange)
    velocity: tuple = F((0.0, 0.0), _frange)
    acceleration: tuple = F((0.0, 0.0), _frange)


@dataclass(eq=True)
class AxisEasing(_Base):
    axis: tuple = F(((0.0, 0.0), (1.0, 1.0), (0.0, 0.0)), _rvec(3))
    easing: FloatEasing = F(FloatEasing(start=0, end=0))


@dataclass(eq=True)
class RotateToViewpoint(_Base):
    pass


@dataclass(eq=True)
class RotateToVelocity(_Base):
    axis: int = 0                    # 0 +X, 1 -X, 2 +Y, 3 -Y, 4 +Z, 5 -Z


@dataclass(eq=True)
class NurbsCurve(_Base):
    index: int = -1                  # into Effect.curves
    scale: float = 1.0
    move_speed: float = 1.0
    loop_type: int = 0


@dataclass(eq=True)
class ViewOffset(_Base):
    distance: tuple = F((3.0, 3.0), _frange)


# spawn shapes
@dataclass(eq=True)
class Point(_Base):
    location: tuple = F(_Z3, _rvec(3))


@dataclass(eq=True)
class Sphere(_Base):
    radius: tuple = F((0.0, 0.0), _frange)
    rotation_x: tuple = F((0.0, 0.0), _frange)     # radians
    rotation_y: tuple = F((0.0, 0.0), _frange)


@dataclass(eq=True)
class Circle(_Base):
    division: int = 8
    radius: tuple = F((0.0, 0.0), _frange)
    angle_start: tuple = F((0.0, 0.0), _frange)    # radians
    angle_end: tuple = F((_f32(2 * math.pi),) * 2, _frange)
    order: int = SPAWN_RANDOM
    axis: int = AXIS_Z
    angle_noise: tuple = F((0.0, 0.0), _frange)


@dataclass(eq=True)
class Line(_Base):
    division: int = 8
    start: tuple = F(_Z3, _rvec(3))
    end: tuple = F(_Z3, _rvec(3))
    noise: tuple = F((0.0, 0.0), _frange)
    order: int = SPAWN_RANDOM


@dataclass(eq=True)
class ModelSpawn(_Base):
    reference: int = 0               # 0 file, 1 procedural, 2 external
    index: int = -1
    mode: int = 0                    # 0 random, 1 vertex, 2 vertex random, 3 face, 4 face random


# colors
@dataclass(eq=True)
class ColorRandom(_Base):
    min: tuple = F(WHITE, _rgba)
    max: tuple = F(WHITE, _rgba)
    hsv: bool = False


@dataclass(eq=True)
class ColorEasing(_Base):
    start: ColorRandom = F(ColorRandom(), _rcolor)
    end: ColorRandom = F(ColorRandom(), _rcolor)
    params: tuple = F((0.0, 0.0, 1.0), _floats(3))


@dataclass(eq=True)
class Gradient(_Base):
    """Color keys ``(position, (r, g, b), intensity)`` (0-1 floats) and alpha
    keys ``(position, alpha)``, at most 8 of each."""
    colors: list = F([], lambda v: [(float(p), _vec(3)(c), float(i)) for p, c, i in v])
    alphas: list = F([], lambda v: [(float(p), float(a)) for p, a in v])


# UV
@dataclass(eq=True)
class UVFixed(_Base):
    rect: tuple = F((0.0, 0.0, 1.0, 1.0), _floats(4))   # x, y, w, h (0-1)


@dataclass(eq=True)
class UVAnimation(_Base):
    rect: tuple = F((0.0, 0.0, 1.0, 1.0), _floats(4))   # first frame
    frame_length: int = 1            # frames per cell (INFINITE // 100 = infinite)
    frames_x: int = 1
    frames_y: int = 1
    loop: int = UV_LOOP_ONCE
    start_frame: tuple = F((0, 0), _irange)
    interpolation: int = 0           # 1: blend between cells (first UV only)


@dataclass(eq=True)
class UVScroll(_Base):
    position: tuple = F(((0.0, 0.0), (0.0, 0.0)), _rvec(2))
    size: tuple = F(((1.0, 1.0), (1.0, 1.0)), _rvec(2))
    speed: tuple = F(((0.0, 0.0), (0.0, 0.0)), _rvec(2))


@dataclass(eq=True)
class UVFCurve(_Base):
    position: FCurve2 = F(FCurve2())
    size: FCurve2 = F(FCurve2())


@dataclass(eq=True)
class Fade(_Base):
    """Fade in/out over ``frames``; fade-out ``mode`` 1 within the lifetime,
    2 after the particle is removed."""
    frames: float = 1.0
    params: tuple = F((0.0, 0.0, 1.0), _floats(3))
    mode: int = 1


@dataclass(eq=True)
class TextureUV(_Base):
    """How ribbons and tracks map the texture."""
    type: int = UV_STRETCH
    tile_length: float = 1.0         # UV_TILE
    edge_head: int = 0               # UV_TILE_PER_PARTICLE
    edge_tail: int = 0
    loop_area: tuple = F((0.0, 1.0), _floats(2))


@dataclass(eq=True)
class AlphaCutoffFourPoint(_Base):
    begin: tuple = F((0.0, 0.0), _frange)
    transition_frames: tuple = F((0, 0), _irange)
    no2: tuple = F((0.0, 0.0), _frange)
    no3: tuple = F((0.0, 0.0), _frange)
    transition_frames2: tuple = F((0, 0), _irange)
    end: tuple = F((0.0, 0.0), _frange)


@dataclass(eq=True)
class AlphaCutoff(_Base):
    """``threshold``: a number, ``AlphaCutoffFourPoint``, ``FloatEasing`` or ``FCurve1``."""
    threshold: Any = 0.0
    ref: int = -1                    # dynamic equation (fixed threshold only)
    edge_threshold: float = 0.0
    edge_color: tuple = F(WHITE, _rgba)
    edge_color_scaling: float = 1.0


@dataclass(eq=True)
class Falloff(_Base):
    blend: int = 0                   # 0 add, 1 sub, 2 mul
    begin: tuple = F((0, 0, 0, 255), _rgba)
    end: tuple = F(WHITE, _rgba)
    pow: float = 1.0


@dataclass(eq=True)
class CustomData(_Base):
    """``type`` is a ``CUSTOM_*`` constant; ``value``: (x, y), random 2D,
    (start, end, params), FCurve2, (x, y, z, w), FCurveRGBA or None."""
    type: int = CUSTOM_FIXED2D
    value: Any = (0.0, 0.0)


@dataclass(eq=True)
class MaterialFile(_Base):
    index: int = -1                  # into Effect.materials
    textures: list = F([])           # (type, texture index)
    uniforms: list = F([])           # (x, y, z, w)
    gradients: list = F([])          # Gradient (1.7)


@dataclass(eq=True)
class ForceField(_Base):
    """A local force field; which fields matter depends on ``type`` (FF_*)."""
    type: int = FF_NONE
    power: float = 1.0
    position: tuple = F((0.0, 0.0, 0.0), _vec(3))
    rotation: tuple = F((0.0, 0.0, 0.0), _vec(3))
    gravitation: bool = False        # FF_FORCE
    subtype: int = 0                 # FF_VORTEX (1 constant speed) / FF_TURBULENCE (1 complicated)
    seed: int = 0                    # FF_TURBULENCE
    scale: float = 1.0
    strength: float = 1.0            # FF_TURBULENCE, files before 1601 only
    octave: int = 1
    gravity: tuple = F((0.0, 0.0, 0.0), _vec(3))   # FF_GRAVITY
    control: float = 1.0             # FF_ATTRACTIVE
    min_range: float = 0.0
    max_range: float = 0.0
    falloff: int = FALLOFF_NONE
    falloff_power: float = 1.0
    falloff_max_distance: float = 0.0
    falloff_min_distance: float = 0.0
    falloff_shape: tuple = F((1.0, 0.0, 0.0), _floats(3))   # tube radius / cone angle: power, max, min


@dataclass(eq=True)
class LocationAbs(_Base):
    """Gravity / attraction of files up to 1600 (later a force field)."""
    type: int = 1                    # 1 gravity, 2 attractive force
    gravity: tuple = F((0.0, 0.0, 0.0), _vec(3))
    force: float = 0.0
    control: float = 0.0
    min_range: float = 0.0
    max_range: float = 0.0


@dataclass(eq=True)
class KillRules(_Base):
    """1.7 kill rules: type 1 box, 2 plane, 3 sphere."""
    type: int = 0
    scale_and_rotation_applied: bool = True
    center: tuple = F((0.0, 0.0, 0.0), _vec(3))
    size: tuple = F((0.0, 0.0, 0.0), _vec(3))
    plane_axis: tuple = F((0.0, 1.0, 0.0), _vec(3))
    plane_offset: float = 0.0
    radius: float = 0.0
    kill_inside: bool = False


@dataclass(eq=True)
class Sound(_Base):
    wave: int = -1                   # into Effect.sounds
    volume: tuple = F((1.0, 1.0), _frange)
    pitch: tuple = F((0.0, 0.0), _frange)
    pan_type: int = 0                # 0 2D, 1 3D
    pan: tuple = F((0.0, 0.0), _frange)
    distance: float = 10.0
    delay: tuple = F((0, 0), _irange)


@dataclass(eq=True)
class Crescent(_Base):
    starting_fade: float = 0.0
    ending_fade: float = 0.0
    starting_angle: Any = F(0.0, _ring_single)     # degrees
    ending_angle: Any = F(360.0, _ring_single)


@dataclass(eq=True)
class RingPVA(_Base):
    location: tuple = F(((0.0, 0.0), (0.0, 0.0)), _rvec(2))
    velocity: tuple = F(((0.0, 0.0), (0.0, 0.0)), _rvec(2))
    acceleration: tuple = F(((0.0, 0.0), (0.0, 0.0)), _rvec(2))


@dataclass(eq=True)
class RingEasing(_Base):
    start: tuple = F(((0.0, 0.0), (0.0, 0.0)), _rvec(2))
    end: tuple = F(((0.0, 0.0), (0.0, 0.0)), _rvec(2))
    params: tuple = F((0.0, 0.0, 1.0), _floats(3))


@dataclass(eq=True)
class CullingSphere(_Base):
    radius: float = 1.0
    location: tuple = F((0.0, 0.0, 0.0), _vec(3))


@dataclass(eq=True)
class ProceduralModel(_Base):
    """A procedural mesh (1.6).  ``shape`` holds the type-specific values in
    file order: mesh (angle_begin, angle_end, div_x, div_y, rotate) or ribbon
    (cross_section, rotate, vertices, sizes(2), angles(2), noises(2), count);
    ``primitive_params``: sphere (radius, depth_min, depth_max), cone (radius,
    depth), cylinder (radius1, radius2, depth) or spline4 (8 floats)."""
    type: int = 0                    # 0 mesh, 1 ribbon
    shape: tuple = (0.0, 360.0, 10, 10, 0.0)
    primitive: int = 0               # 0 sphere, 1 cone, 2 cylinder, 3 spline4
    primitive_params: tuple = (1.0, -1.0, 1.0)
    axis: int = AXIS_Y
    tilt_noise: tuple = ((0.0, 0.0),) * 3       # frequency, offset, power
    wave_noise: tuple = ((0.0, 0.0, 0.0),) * 3
    curl_noise: tuple = ((0.0, 0.0, 0.0),) * 3
    colors: tuple = (WHITE,) * 9                # upper l/c/r, middle l/c/r, lower l/c/r
    color_center_position: tuple = (0.5, 0.5)
    color_center_area: tuple = (0.0, 0.0)
    vertex_color_noise: tuple = ((0.0, 0.0, 0.0),) * 3
    uv_position: tuple = (0.0, 0.5)
    uv_size: tuple = (1.0, 1.0)


# ------------------------------------------------------------------- nodes
@dataclass(eq=True)
class Node(_Base):
    """A node that draws nothing (grouping); base of the drawing nodes."""
    TYPE = NODE_NONE

    children: list = F([])
    visible: bool = True             # IsRendered
    rendering_priority: int = None   # None: computed by write_efk

    # common values
    max_generation: int = 1
    life: tuple = F((100, 100), _irange)
    generation_time: tuple = F((1.0, 1.0), _frange)
    generation_offset: tuple = F((0.0, 0.0), _frange)
    bind_translation: int = BIND_ALWAYS
    bind_rotation: int = BIND_ALWAYS
    bind_scale: int = BIND_ALWAYS
    remove_when_life_ends: bool = True
    remove_when_parent_removed: bool = False
    remove_when_children_removed: bool = False
    ref_max_generation: int = -1
    ref_life: tuple = F(_REF, _irange)
    ref_generation_time: tuple = F(_REF, _irange)
    ref_generation_offset: tuple = F(_REF, _irange)
    steering_max_follow_speed: tuple = F((10.0, 10.0), _frange)   # bind_translation 4/5
    steering_speed: tuple = F((30.0, 30.0), _frange)
    trigger_start: tuple = None      # 1.7: (type, index)
    trigger_stop: tuple = None
    trigger_remove: tuple = None
    lod_matching: int = 0b1111       # 1.7
    lod_behaviour: int = 0

    # transform
    translation: Any = F(Fixed())
    force_fields: list = F([])
    location_abs: LocationAbs = None  # files up to 1600
    rotation: Any = F(Fixed())
    scale: Any = F(Fixed())
    spawn: Any = F(Point())
    spawn_rotation: bool = False

    # depth
    depth_offset: float = 0.0
    depth_offset_scaled_with_camera: bool = False
    depth_offset_scaled_with_particle_scale: bool = False
    depth_scale_suppression: float = 1.0
    depth_clipping: float = FLT_MAX
    zsort: int = ZSORT_NONE
    drawing_priority: int = 0
    soft_particle: float = 1.0
    kill_rules: KillRules = None     # 1.7

    # renderer common
    material: int = MATERIAL_DEFAULT
    emissive: float = 1.0
    texture: int = -1
    normal_texture: int = -1
    alpha_texture: int = -1
    uv_distortion_texture: int = -1
    blend_texture: int = -1
    blend_alpha_texture: int = -1
    blend_uv_distortion_texture: int = -1
    material_file: MaterialFile = None
    blend: int = BLEND
    filter: int = LINEAR
    wrap: int = REPEAT
    filter2: int = LINEAR
    wrap2: int = REPEAT
    filters_extra: tuple = ((LINEAR, REPEAT),) * 5   # alpha, uv dist., blend, blend alpha, blend uv dist.
    ztest: bool = True
    zwrite: bool = False
    fade_in: Fade = None
    fade_out: Fade = None
    uv: Any = None
    alpha_uv: Any = None
    uv_distortion_uv: Any = None
    uv_distortion_intensity: float = 0.0
    blend_uv: Any = None
    texture_blend_type: int = -1
    blend_alpha_uv: Any = None
    blend_uv_distortion_uv: Any = None
    blend_uv_distortion_intensity: float = 0.0
    color_bind: int = BIND_NOT
    distortion_intensity: float = 1.0
    custom_data1: CustomData = None
    custom_data2: CustomData = None
    alpha_cutoff: AlphaCutoff = None
    falloff: Falloff = None
    soft_particle_far: float = 0.0
    soft_particle_near: float = 0.0
    soft_particle_near_offset: float = 0.0

    sound: Sound = None


@dataclass(eq=True)
class Sprite(Node):
    TYPE = NODE_SPRITE
    rendering_order: int = ORDER_FIRST_CREATED_FIRST
    billboard: int = BILLBOARD
    color: Any = F(WHITE, _color_param)
    vertex_colors: tuple = None      # (ll, lr, ul, ur) colors, or None
    position_type: int = 1           # 1 fixed (the editor always writes 1)
    vertex_positions: tuple = ((-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5))


@dataclass(eq=True)
class Ribbon(Node):
    TYPE = NODE_RIBBON
    texture_uv: TextureUV = F(TextureUV())
    time_type: int = 0               # 1.7
    viewpoint_dependent: bool = False
    color: Any = F(WHITE, _color_param)
    vertex_colors: tuple = None      # (left, right) colors, or None
    position_type: int = 1
    vertex_positions: tuple = (-0.5, 0.5)
    spline_division: int = 1


@dataclass(eq=True)
class Ring(Node):
    TYPE = NODE_RING
    rendering_order: int = ORDER_FIRST_CREATED_FIRST
    billboard: int = BILLBOARD_FIXED
    shape: Crescent = None           # None: donut
    vertex_count: int = 16
    viewing_angle: Any = F(360.0, _ring_single)   # legacy, kept for old runtimes
    outer: Any = F((2.0, 0.0), _ring_location)    # (radius, height)
    inner: Any = F((1.0, 0.0), _ring_location)
    center_ratio: Any = F(0.5, _ring_single)
    outer_color: Any = F((255, 255, 255, 0), _color_param)
    center_color: Any = F(WHITE, _color_param)
    inner_color: Any = F((255, 255, 255, 0), _color_param)


@dataclass(eq=True)
class Model(Node):
    TYPE = NODE_MODEL
    model_mode: int = 0              # 0 file, 1 procedural, 2 external
    model_magnification: float = 1.0
    model: int = -1
    billboard: int = BILLBOARD_FIXED
    culling: int = CULL_FRONT
    color: Any = F(WHITE, _color_param)
    legacy_falloff: Falloff = None   # files 1600-1601


@dataclass(eq=True)
class Track(Node):
    TYPE = NODE_TRACK
    texture_uv: TextureUV = F(TextureUV())
    size_front: float = 1.0
    size_middle: float = 1.0
    size_back: float = 1.0
    spline_division: int = 1
    smoothing: int = 0               # 1.7
    time_type: int = 0               # 1.7
    color_left: Any = F(WHITE, _color_param)
    color_left_middle: Any = F(WHITE, _color_param)
    color_center: Any = F(WHITE, _color_param)
    color_center_middle: Any = F(WHITE, _color_param)
    color_right: Any = F(WHITE, _color_param)
    color_right_middle: Any = F(WHITE, _color_param)


_NODE_CLASSES = {c.TYPE: c for c in (Node, Sprite, Ribbon, Ring, Model, Track)}


@dataclass(eq=True)
class Effect(_Base):
    nodes: list = F([])              # children of the root node
    textures: list = F([])           # color texture paths (index = texture)
    normal_textures: list = F([])
    distortion_textures: list = F([])
    sounds: list = F([])
    models: list = F([])             # .efkmodel paths
    materials: list = F([])          # .efkmat paths
    curves: list = F([])             # .efkcurve paths
    procedural_models: list = F([])
    dynamic_inputs: list = F([])
    dynamic_equations: list = F([])  # compiled bytecode (bytes)
    rendering_node_count: int = None     # None: computed by write_efk
    rendering_node_threshold: int = None
    magnification: float = 1.0
    random_seed: int = -1
    culling: CullingSphere = None
    lod_distances: tuple = (0.0, 0.0, 0.0)   # 1.7
    version: int = VERSION           # version of the file read


# ------------------------------------------------------------------- codec
_ST = {k: struct.Struct("<" + k) for k in ("i", "I", "B", "H", "f")}


class _Codec:
    """Reads (``data`` given) or writes (``data`` None) one structure at a time.

    Every method takes the value to write and returns the value read or
    written, so a layout is written ``obj.x = c.i32(obj.x)``.
    """

    def __init__(self, data=None, version=VERSION):
        self.reading = data is not None
        self.buf = bytes(data) if self.reading else bytearray()
        self.pos = 0
        self.end = len(self.buf)
        self.version = version
        self.where = []

    # errors
    def fail(self, msg):
        where = "/".join(self.where)
        raise FormatError(f"{msg} (offset {self.pos}{', ' + where if where else ''})")

    def push(self, name):
        self.where.append(name)

    def pop(self):
        self.where.pop()

    # primitives
    def _one(self, k, v):
        st = _ST[k]
        if self.reading:
            if self.pos + st.size > self.end:
                self.fail("unexpected end of data")
            r = st.unpack_from(self.buf, self.pos)[0]
            self.pos += st.size
            return r
        self.buf += st.pack(float(v) if k == "f" else int(v))
        return v

    def i32(self, v=0):
        return self._one("i", v)

    def u32(self, v=0):
        return self._one("I", v)

    def u8(self, v=0):
        return self._one("B", v)

    def f32(self, v=0.0):
        r = self._one("f", v)
        return r if self.reading else v

    def bool(self, v=False):
        r = self.i32(int(v) if not self.reading else 0)
        if self.reading:
            return bool(r) if r in (0, 1) else r
        return v

    def f32s(self, v, n):
        return tuple(self.f32(v[i] if not self.reading else 0) for i in range(n))

    def i32s(self, v, n):
        return tuple(self.i32(v[i] if not self.reading else 0) for i in range(n))

    def u8s(self, v, n):
        return tuple(self.u8(v[i] if not self.reading else 0) for i in range(n))

    def tuple(self, v, n, fn):
        return tuple(fn(v[i] if not self.reading else None) for i in range(n))

    # Effekseer random types: max is stored before min; we keep (min, max)
    def rf(self, v=(0.0, 0.0)):
        hi = self.f32(v[1] if not self.reading else 0)
        lo = self.f32(v[0] if not self.reading else 0)
        return (lo, hi)

    def ri(self, v=(0, 0)):
        hi = self.i32(v[1] if not self.reading else 0)
        lo = self.i32(v[0] if not self.reading else 0)
        return (lo, hi)

    ref = ri                    # RefMinMax: Max, Min

    def rv(self, v, n):         # random_vector2d/3d: max xyz, min xyz
        hi = self.f32s([p[1] for p in v] if not self.reading else None, n)
        lo = self.f32s([p[0] for p in v] if not self.reading else None, n)
        return tuple(zip(lo, hi))

    def rgba(self, v=WHITE):
        return self.u8s(v, 4)

    def utf16(self, v=""):
        """Path: int32 length in chars (with the terminating 0), UTF-16LE."""
        if self.reading:
            n = self.i32()
            if n < 0 or n > _LIST_MAX:
                self.fail(f"bad string length {n}")
            raw = self.raw(None, n * 2)
            s = raw.decode("utf-16-le")
            if not s.endswith("\0"):
                self.fail(f"string {s!r} is not 0-terminated")
            return s[:-1]
        enc = (v + "\0").encode("utf-16-le")
        self.i32(len(enc) // 2)
        self.raw(enc, len(enc))
        return v

    def raw(self, v, n):
        if self.reading:
            if self.pos + n > self.end:
                self.fail("unexpected end of data")
            r = self.buf[self.pos:self.pos + n]
            self.pos += n
            return r
        assert len(v) == n
        self.buf += v
        return v

    def blob(self, v=b""):
        n = self.i32(len(v) if not self.reading else 0)
        if self.reading and (n < 0 or n > 102400):
            self.fail(f"bad blob size {n}")
        return self.raw(v, n)

    def list(self, items, fn, unsigned=False, limit=_LIST_MAX):
        prim = self.u32 if unsigned else self.i32
        n = prim(len(items) if not self.reading else 0)
        if self.reading:
            if n < 0 or n > limit:
                self.fail(f"bad element count {n}")
            return [fn(None) for _ in range(n)]
        for it in items:
            fn(it)
        return items

    def sized(self, body, what):
        """An int32 byte count, then the block it counts."""
        if self.reading:
            size = self.i32()
            start = self.pos
            if size < 0 or start + size > self.end:
                self.fail(f"{what}: bad block size {size}")
            saved, self.end = self.end, start + size
            try:
                r = body()
            finally:
                self.end = saved
            if self.pos != start + size:
                self.fail(f"{what}: block of {size} bytes, layout read {self.pos - start}")
            return r
        at = len(self.buf)
        self.buf += b"\0\0\0\0"
        r = body()
        struct.pack_into("<i", self.buf, at, len(self.buf) - at - 4)
        return r

    def obj(self, o, cls):
        """The object to fill: a new ``cls`` when reading."""
        if self.reading:
            return cls()
        if not isinstance(o, cls):
            raise TypeError(f"expected {cls.__name__}, got {type(o).__name__}")
        return o

    def tag(self, o, table, what):
        """Write the tag of ``o``'s variant or read one.  ``table`` maps tags
        to a type or a predicate."""
        if self.reading:
            t = self.i32()
            if t not in table:
                self.fail(f"{what}: unsupported type {t}")
            return t
        for t, kind in table.items():
            if (isinstance(kind, type) and isinstance(o, kind)) or \
                    (not isinstance(kind, type) and kind(o)):
                self.i32(t)
                return t
        raise TypeError(f"{what}: cannot write {o!r}")

    def at_version(self, version, fn):
        saved, self.version = self.version, version
        try:
            return fn()
        finally:
            self.version = saved


def _d(v, default):
    return default if v is None else v


def _is_none(v):
    return v is None


# ----------------------------------------------------------------- layouts
def _l_fcurve(c, f):
    f = c.obj(f, FCurve)
    f.start = c.i32(f.start)
    f.end = c.i32(f.end)
    f.offset = c.rf(f.offset)
    f.offset_frame = c.i32(f.offset_frame)
    f.length = c.i32(f.length)
    f.freq = c.i32(f.freq)
    n = c.i32(len(f.keys) if not c.reading else 0)
    if 0 <= n <= 65536 and f.freq > 0:
        f.keys = [c.f32(f.keys[i] if not c.reading else 0) for i in range(n)]
    elif c.reading:
        f.keys = []
        f.freq_note = n
    elif f.keys:
        raise ValueError("an FCurve with keys needs freq > 0")
    return f


def _l_fcurve_n(c, o, cls, names, timeline_version=1500):
    o = c.obj(o, cls)
    if c.version >= timeline_version:
        o.timeline = c.i32(o.timeline)
    for n in names:
        setattr(o, n, _l_fcurve(c, getattr(o, n)))
    return o


def _l_fcurve1(c, o):
    return _l_fcurve_n(c, o, FCurve1, ("s",), 1600)


def _l_fcurve2(c, o):
    return _l_fcurve_n(c, o, FCurve2, ("x", "y"))


def _l_fcurve3(c, o):
    return _l_fcurve_n(c, o, FCurve3, ("x", "y", "z"))


def _l_fcurve_rgba(c, o):
    return _l_fcurve_n(c, o, FCurveRGBA, ("r", "g", "b", "a"))


def _l_easing_body(c, e, n, default, min_dyn, min_app):
    """ParameterEasing<T>::Load (n = 1 float, 3 vector)."""
    rnd = c.rf if n == 1 else (lambda v: c.rv(v, 3))
    if c.version >= min_dyn:
        e.ref_start = c.ref(e.ref_start)
        e.ref_end = c.ref(e.ref_end)
    e.start = rnd(_d(e.start, default))
    e.end = rnd(_d(e.end, default))
    if c.version >= min_app:
        mid = c.i32(1 if e.middle is not None else 0)
        if mid > 0:
            e.ref_middle = c.ref(e.ref_middle)
            e.middle = rnd(e.middle)
        elif c.reading:
            e.middle = None
        e.ease = c.i32(e.ease)
        if e.ease == EASE_SPEED:
            e.params = c.f32s(e.params, 3)
        e.channels = c.i32(e.channels)
        ind = c.i32(1 if e.individual is not None else 0)
        if ind > 0:
            if n == 1:
                e.individual = c.i32(e.individual)
            else:
                e.individual = c.i32s(e.individual, 3)
        elif c.reading:
            e.individual = None
    else:
        e.params = c.f32s(e.params, 3)
    return e


def _l_float_easing(c, e, default=(0.0, 0.0), min_version=1608):
    """A ParameterEasingFloat in a size-prefixed block."""
    e = c.obj(e, FloatEasing)
    return c.sized(lambda: _l_easing_body(c, e, 1, default, min_version, min_version), "float easing")


def _l_float_easing_compat(c, e, default=(0.0, 0.0)):
    """LoadFloatEasing: sized from 1608, a bare easing_float before."""
    e = c.obj(e, FloatEasing)
    if c.version >= 1608:
        return c.sized(lambda: _l_easing_body(c, e, 1, default, 1608, 1608), "float easing")
    return _l_easing_body(c, e, 1, default, 1608, 1608)


def _l_vec3_easing(c, e, default):
    e = c.obj(e, Easing)
    return c.sized(lambda: _l_easing_body(c, e, 3, default, 14, 1600), "easing")


def _l_fixed(c, o, default):
    o = c.obj(o, Fixed)

    def body():
        o.ref = c.i32(o.ref)
        o.value = c.f32s(_d(o.value, default), 3)
    return c.sized(body, "fixed")


def _l_pva(c, o, default):
    o = c.obj(o, PVA)

    def body():
        o.ref_value = c.ref(o.ref_value)
        o.ref_velocity = c.ref(o.ref_velocity)
        o.ref_acceleration = c.ref(o.ref_acceleration)
        o.value = c.rv(_d(o.value, default), 3)
        o.velocity = c.rv(o.velocity, 3)
        o.acceleration = c.rv(o.acceleration, 3)
    return c.sized(body, "pva")


_ZERO3 = (0.0, 0.0, 0.0)
_ONE3 = (1.0, 1.0, 1.0)


def _l_translation(c, t):
    tag = c.tag(t, {0: Fixed, 1: PVA, 2: Easing, 3: FCurve3, 4: NurbsCurve, 5: ViewOffset}, "translation")
    if tag == 0:
        return _l_fixed(c, t, _ZERO3)
    if tag == 1:
        return _l_pva(c, t, _Z3)
    if tag == 2:
        return _l_vec3_easing(c, t, _Z3)
    if tag == 3:
        return c.sized(lambda: _l_fcurve3(c, t), "translation fcurve")
    if tag == 4:
        t = c.obj(t, NurbsCurve)
        t.index = c.i32(t.index)
        t.scale = c.f32(t.scale)
        t.move_speed = c.f32(t.move_speed)
        t.loop_type = c.i32(t.loop_type)
        return t
    t = c.obj(t, ViewOffset)
    t.distance = c.rf(t.distance)
    return t


def _l_rotation(c, r):
    tag = c.tag(r, {0: Fixed, 1: PVA, 2: Easing, 3: AxisPVA, 4: AxisEasing, 5: FCurve3,
                    6: RotateToViewpoint, 7: RotateToVelocity}, "rotation")
    if tag == 0:
        return _l_fixed(c, r, _ZERO3)
    if tag == 1:
        return _l_pva(c, r, _Z3)
    if tag == 2:
        return _l_vec3_easing(c, r, _Z3)
    if tag == 3:
        r = c.obj(r, AxisPVA)

        def body():
            r.axis = c.rv(r.axis, 3)
            r.rotation = c.rf(r.rotation)
            r.velocity = c.rf(r.velocity)
            r.acceleration = c.rf(r.acceleration)
        c.sized(body, "axis pva")
        return r
    if tag == 4:
        r = c.obj(r, AxisEasing)

        def body():
            r.axis = c.rv(r.axis, 3)
            r.easing = _l_float_easing_compat(c, r.easing)
        c.sized(body, "axis easing")
        return r
    if tag == 5:
        return c.sized(lambda: _l_fcurve3(c, r), "rotation fcurve")
    if tag == 6:
        # the loader reads the size and does not skip it: it must be 0
        if c.i32(0) != 0:
            c.fail("rotate-to-viewpoint block must be empty")
        return c.obj(r, RotateToViewpoint)
    r = c.obj(r, RotateToVelocity)

    def body():
        r.axis = c.i32(r.axis)
    c.sized(body, "rotate to velocity")
    return r


def _l_scaling(c, s):
    tag = c.tag(s, {0: Fixed, 1: PVA, 2: Easing, 3: SinglePVA, 4: FloatEasing, 5: FCurve3, 6: FCurve1},
                "scaling")
    if tag == 0:
        return _l_fixed(c, s, _ONE3)
    if tag == 1:
        return _l_pva(c, s, ((1.0, 1.0),) * 3)
    if tag == 2:
        return _l_vec3_easing(c, s, ((1.0, 1.0),) * 3)
    if tag == 3:
        s = c.obj(s, SinglePVA)

        def body():
            s.value = c.rf(s.value)
            s.velocity = c.rf(s.velocity)
            s.acceleration = c.rf(s.acceleration)
        c.sized(body, "single pva")
        return s
    if tag == 4:
        return _l_float_easing(c, s, (1.0, 1.0))
    if tag == 5:
        return c.sized(lambda: _l_fcurve3(c, s), "scaling fcurve")
    return c.sized(lambda: _l_fcurve1(c, s), "single scaling fcurve")


def _l_force_field(c, f):
    f = c.obj(f, ForceField)
    v = c.version
    f.type = c.i32(f.type)
    if v >= 1600:
        f.power = c.f32(f.power)
        f.position = c.f32s(f.position, 3)
        f.rotation = c.f32s(f.rotation, 3)
    t = f.type
    if t == FF_FORCE:
        f.gravitation = c.bool(f.gravitation)
    elif t == FF_VORTEX:
        if v >= 1601:
            f.subtype = c.i32(f.subtype)
    elif t == FF_TURBULENCE:
        if v >= 1601:
            f.subtype = c.i32(f.subtype)
        f.seed = c.i32(f.seed)
        f.scale = c.f32(f.scale)
        if v < 1601:
            f.strength = c.f32(f.strength)
        f.octave = c.i32(f.octave)
    elif t == FF_GRAVITY:
        f.gravity = c.f32s(f.gravity, 3)
    elif t == FF_ATTRACTIVE:
        f.control = c.f32(f.control)
        f.min_range = c.f32(f.min_range)
        f.max_range = c.f32(f.max_range)
    if v >= 1600:
        f.falloff = c.i32(f.falloff)
        if f.falloff not in (0, 1, 2, 3):
            c.fail(f"unsupported force field falloff {f.falloff}")
        if f.falloff != FALLOFF_NONE:
            f.falloff_power = c.f32(f.falloff_power)
            f.falloff_max_distance = c.f32(f.falloff_max_distance)
            f.falloff_min_distance = c.f32(f.falloff_min_distance)
        if f.falloff in (FALLOFF_TUBE, FALLOFF_CONE):
            f.falloff_shape = c.f32s(f.falloff_shape, 3)
    return f


def _l_location_abs(c, a):
    tag = c.tag(a, {0: _is_none, 1: lambda o: o.type == 1, 2: lambda o: o.type == 2}, "location abs")
    if tag == 0:
        if c.i32(0) != 0:
            c.fail("location abs 'none' must be empty")
        return None
    a = c.obj(a, LocationAbs)
    a.type = tag

    def body():
        if tag == 1:
            a.gravity = c.f32s(a.gravity, 3)
        else:
            a.force = c.f32(a.force)
            a.control = c.f32(a.control)
            a.min_range = c.f32(a.min_range)
            a.max_range = c.f32(a.max_range)
    c.sized(body, "location abs")
    return a


def _l_spawn(c, n):
    n.spawn_rotation = c.bool(n.spawn_rotation)
    s = n.spawn
    tag = c.tag(s, {0: Point, 1: Sphere, 2: ModelSpawn, 3: Circle, 4: Line}, "spawn")
    if tag == 0:
        s = c.obj(s, Point)
        s.location = c.rv(s.location, 3)
    elif tag == 1:
        s = c.obj(s, Sphere)
        s.radius = c.rf(s.radius)
        s.rotation_x = c.rf(s.rotation_x)
        s.rotation_y = c.rf(s.rotation_y)
    elif tag == 2:
        s = c.obj(s, ModelSpawn)
        if c.version >= 1602:
            s.reference = c.i32(s.reference)
        s.index = c.i32(s.index)
        s.mode = c.i32(s.mode)
    elif tag == 3:
        s = c.obj(s, Circle)
        s.division = c.i32(s.division)
        s.radius = c.rf(s.radius)
        s.angle_start = c.rf(s.angle_start)
        s.angle_end = c.rf(s.angle_end)
        s.order = c.i32(s.order)
        s.axis = c.i32(s.axis)
        s.angle_noise = c.rf(s.angle_noise)
    else:
        s = c.obj(s, Line)
        s.division = c.i32(s.division)
        s.start = c.rv(s.start, 3)
        s.end = c.rv(s.end, 3)
        s.noise = c.rf(s.noise)
        s.order = c.i32(s.order)
    n.spawn = s


def _l_kill_rules(c, n):
    k = n.kill_rules if n.kill_rules is not None else KillRules()
    if c.reading:
        k = KillRules()
    k.type = c.i32(k.type)
    k.scale_and_rotation_applied = c.bool(k.scale_and_rotation_applied)
    if k.type == 1:
        k.center = c.f32s(k.center, 3)
        k.size = c.f32s(k.size, 3)
        k.kill_inside = c.bool(k.kill_inside)
    elif k.type == 2:
        k.plane_axis = c.f32s(k.plane_axis, 3)
        k.plane_offset = c.f32(k.plane_offset)
    elif k.type == 3:
        k.center = c.f32s(k.center, 3)
        k.radius = c.f32(k.radius)
        k.kill_inside = c.bool(k.kill_inside)
    elif k.type != 0:
        c.fail(f"unsupported kill rule {k.type}")
    if c.reading:
        n.kill_rules = None if k == KillRules() else k


def _l_gradient(c, g):
    g = c.obj(g, Gradient)

    def color_key(k):
        k = k if k is not None else (0.0, (0.0, 0.0, 0.0), 0.0)
        pos = c.f32(k[0])
        rgb = c.f32s(k[1], 3)
        inten = c.f32(k[2])
        return (pos, rgb, inten)

    def alpha_key(k):
        k = k if k is not None else (0.0, 0.0)
        return (c.f32(k[0]), c.f32(k[1]))
    g.colors = c.list(g.colors, color_key, limit=8)
    g.alphas = c.list(g.alphas, alpha_key, limit=8)
    return g


def _l_rcolor(c, r):
    """random_color: u8 mode, u8 reserved, max color, min color."""
    r = c.obj(r, ColorRandom)
    mode = c.u8(1 if r.hsv else 0)
    if mode not in (0, 1):
        c.fail(f"bad color mode {mode}")
    r.hsv = bool(mode)
    if c.u8(0) != 0:
        c.fail("reserved color byte is not 0")
    r.max = c.rgba(r.max)
    r.min = c.rgba(r.min)
    return r


def _l_color(c, col):
    """AllTypeColorParameter."""
    tag = c.tag(col, {0: lambda o: isinstance(o, tuple), 1: ColorRandom, 2: ColorEasing,
                      3: FCurveRGBA, 4: Gradient}, "color")
    if tag == 0:
        return c.rgba(col)
    if tag == 1:
        return _l_rcolor(c, col)
    if tag == 2:
        e = c.obj(col, ColorEasing)
        e.start = _l_rcolor(c, e.start)
        e.end = _l_rcolor(c, e.end)
        e.params = c.f32s(e.params, 3)
        return e
    if tag == 3:
        return _l_fcurve_rgba(c, col)
    return _l_gradient(c, col)


def _l_fade(c, f):
    mode = c.i32(f.mode if f is not None else 0)
    if mode == 0:
        return None
    f = c.obj(f, Fade)
    f.mode = mode
    f.frames = c.f32(f.frames)
    f.params = c.f32s(f.params, 3)
    return f


def _l_uv(c, u, index):
    tag = c.tag(u, {0: _is_none, 1: UVFixed, 2: UVAnimation, 3: UVScroll, 4: UVFCurve}, "uv")
    if tag == 0:
        return None
    if tag == 1:
        u = c.obj(u, UVFixed)
        u.rect = c.f32s(u.rect, 4)
    elif tag == 2:
        u = c.obj(u, UVAnimation)
        u.rect = c.f32s(u.rect, 4)
        u.frame_length = c.i32(u.frame_length)
        u.frames_x = c.i32(u.frames_x)
        u.frames_y = c.i32(u.frames_y)
        u.loop = c.i32(u.loop)
        u.start_frame = c.ri(u.start_frame)
        if c.version >= 1600 and index == 0:
            u.interpolation = c.i32(u.interpolation)
    elif tag == 3:
        u = c.obj(u, UVScroll)
        u.position = c.rv(u.position, 2)
        u.size = c.rv(u.size, 2)
        u.speed = c.rv(u.speed, 2)
    else:
        u = c.obj(u, UVFCurve)
        u.position = _l_fcurve2(c, u.position)
        u.size = _l_fcurve2(c, u.size)
    return u


def _l_custom_data(c, d):
    t = c.i32(d.type if d is not None else 0)
    if t == 0:
        return None
    d = c.obj(d, CustomData)
    d.type = t
    if t == CUSTOM_FIXED2D:
        d.value = c.f32s(d.value, 2)
    elif t == CUSTOM_RANDOM2D:
        d.value = c.rv(d.value, 2)
    elif t == CUSTOM_EASING2D:
        v = d.value if not c.reading else (None, None, None)
        d.value = (c.rv(v[0], 2), c.rv(v[1], 2), c.f32s(v[2], 3))
    elif t == CUSTOM_FCURVE2D:
        d.value = _l_fcurve2(c, d.value)
    elif t == CUSTOM_FIXED4D:
        d.value = c.f32s(d.value, 4)
    elif t == CUSTOM_FCURVE_COLOR:
        d.value = _l_fcurve_rgba(c, d.value)
    elif t == CUSTOM_DYNAMIC_INPUT:
        d.value = None
    else:
        c.fail(f"unsupported custom data type {t}")
    return d


def _l_renderer_common(c, n):
    v = c.version
    n.material = c.i32(n.material)
    m = n.material
    if m in (MATERIAL_DEFAULT, MATERIAL_LIGHTING) and v >= 1600:
        n.emissive = c.f32(n.emissive)
    if m in (MATERIAL_DEFAULT, MATERIAL_DISTORTION, MATERIAL_LIGHTING):
        n.texture = c.i32(n.texture)
        n.normal_texture = c.i32(n.normal_texture)
        if v >= 1600:
            n.alpha_texture = c.i32(n.alpha_texture)
            n.uv_distortion_texture = c.i32(n.uv_distortion_texture)
            n.blend_texture = c.i32(n.blend_texture)
            n.blend_alpha_texture = c.i32(n.blend_alpha_texture)
            n.blend_uv_distortion_texture = c.i32(n.blend_uv_distortion_texture)
    else:
        mf = c.obj(_d(n.material_file, MaterialFile()), MaterialFile)
        mf.index = c.i32(mf.index)
        mf.textures = c.list(mf.textures, lambda t: c.i32s(t, 2))
        mf.uniforms = c.list(mf.uniforms, lambda u: c.f32s(u, 4))
        if v >= 1703:
            mf.gradients = c.list(mf.gradients, lambda g: _l_gradient(c, g))
        n.material_file = mf
    n.blend = c.i32(n.blend)
    n.filter = c.i32(n.filter)
    n.wrap = c.i32(n.wrap)
    n.filter2 = c.i32(n.filter2)
    n.wrap2 = c.i32(n.wrap2)
    if v >= 1600:
        n.filters_extra = c.tuple(n.filters_extra, 5, lambda fw: c.i32s(fw, 2))
    n.ztest = c.bool(n.ztest)
    n.zwrite = c.bool(n.zwrite)
    n.fade_in = _l_fade(c, n.fade_in)
    n.fade_out = _l_fade(c, n.fade_out)
    n.uv = _l_uv(c, n.uv, 0)
    if v >= 1600:
        n.alpha_uv = _l_uv(c, n.alpha_uv, 1)
        n.uv_distortion_uv = _l_uv(c, n.uv_distortion_uv, 2)
        n.uv_distortion_intensity = c.f32(n.uv_distortion_intensity)
        n.blend_uv = _l_uv(c, n.blend_uv, 3)
        n.texture_blend_type = c.i32(n.texture_blend_type)
        n.blend_alpha_uv = _l_uv(c, n.blend_alpha_uv, 4)
        n.blend_uv_distortion_uv = _l_uv(c, n.blend_uv_distortion_uv, 5)
        n.blend_uv_distortion_intensity = c.f32(n.blend_uv_distortion_intensity)
    n.color_bind = c.i32(n.color_bind)
    n.distortion_intensity = c.f32(n.distortion_intensity)
    n.custom_data1 = _l_custom_data(c, n.custom_data1)
    n.custom_data2 = _l_custom_data(c, n.custom_data2)


def _l_alpha_cutoff(c, a):
    a = c.obj(a, AlphaCutoff)
    tag = c.tag(a.threshold, {0: _isnum, 1: AlphaCutoffFourPoint, 2: FloatEasing, 3: FCurve1},
                "alpha cutoff")

    def body():
        if tag == 0:
            a.ref = c.i32(a.ref)
            a.threshold = c.f32(a.threshold)
        elif tag == 1:
            p = c.obj(a.threshold, AlphaCutoffFourPoint)
            p.begin = c.rf(p.begin)
            p.transition_frames = c.ri(p.transition_frames)
            p.no2 = c.rf(p.no2)
            p.no3 = c.rf(p.no3)
            p.transition_frames2 = c.ri(p.transition_frames2)
            p.end = c.rf(p.end)
            a.threshold = p
        elif tag == 2:
            e = c.obj(a.threshold, FloatEasing)
            a.threshold = _l_easing_body(c, e, 1, (0.0, 0.0), 1600, 1600)
        else:
            a.threshold = _l_fcurve1(c, a.threshold)
    c.sized(body, "alpha cutoff")
    a.edge_threshold = c.f32(a.edge_threshold)
    a.edge_color = c.rgba(a.edge_color)
    if c.version >= 1606:
        a.edge_color_scaling = c.f32(a.edge_color_scaling)
    else:
        a.edge_color_scaling = c.i32(int(a.edge_color_scaling) if not c.reading else 0)
    return a


def _l_falloff(c, f):
    f = c.obj(f, Falloff)
    f.blend = c.i32(f.blend)
    f.begin = c.rgba(f.begin)
    f.end = c.rgba(f.end)
    f.pow = c.f32(f.pow)
    return f


def _l_texture_uv(c, t):
    t = c.obj(t, TextureUV)
    t.type = c.i32(t.type)
    if t.type == UV_TILE_PER_PARTICLE:
        t.edge_head = c.i32(t.edge_head)
        t.edge_tail = c.i32(t.edge_tail)
        t.loop_area = c.f32s(t.loop_area, 2)
    elif t.type == UV_TILE:
        t.tile_length = c.f32(t.tile_length)
    return t


def _l_vertex_colors(c, n, count):
    t = c.i32(1 if n.vertex_colors is not None else 0)
    if t == 1:
        n.vertex_colors = c.tuple(n.vertex_colors, count, c.rgba)
    elif t == 0:
        n.vertex_colors = None
    else:
        c.fail(f"unsupported vertex color type {t}")


def _l_sprite(c, n):
    n.rendering_order = c.i32(n.rendering_order)
    n.billboard = c.i32(n.billboard)
    n.color = _l_color(c, n.color)
    _l_vertex_colors(c, n, 4)
    n.position_type = c.i32(n.position_type)
    if n.position_type not in (0, 1):
        c.fail(f"unsupported sprite position type {n.position_type}")
    n.vertex_positions = c.tuple(n.vertex_positions, 4, lambda p: c.f32s(p, 2))


def _l_ribbon(c, n):
    n.texture_uv = _l_texture_uv(c, n.texture_uv)
    if c.version >= 1700:
        n.time_type = c.i32(n.time_type)
    n.viewpoint_dependent = c.bool(n.viewpoint_dependent)
    n.color = _l_color(c, n.color)
    _l_vertex_colors(c, n, 2)
    n.position_type = c.i32(n.position_type)
    if n.position_type not in (0, 1):
        c.fail(f"unsupported ribbon position type {n.position_type}")
    n.vertex_positions = c.f32s(n.vertex_positions, 2)
    n.spline_division = c.i32(n.spline_division)


def _l_ring_single(c, s, default=0.0):
    tag = c.tag(s, {0: _isnum, 1: lambda o: isinstance(o, tuple), 2: FloatEasing}, "ring value")
    if tag == 0:
        return c.f32(s)
    if tag == 1:
        return c.rf(s)
    return _l_float_easing_compat(c, s, (default, default))


def _l_ring_location(c, loc):
    tag = c.tag(loc, {0: lambda o: isinstance(o, tuple), 1: RingPVA, 2: RingEasing}, "ring location")
    if tag == 0:
        return c.f32s(loc, 2)
    if tag == 1:
        p = c.obj(loc, RingPVA)
        p.location = c.rv(p.location, 2)
        p.velocity = c.rv(p.velocity, 2)
        p.acceleration = c.rv(p.acceleration, 2)
        return p
    e = c.obj(loc, RingEasing)
    e.start = c.rv(e.start, 2)
    e.end = c.rv(e.end, 2)
    e.params = c.f32s(e.params, 3)
    return e


def _l_ring(c, n):
    n.rendering_order = c.i32(n.rendering_order)
    n.billboard = c.i32(n.billboard)
    shape = c.i32(1 if n.shape is not None else 0)
    if shape == 1:
        s = c.obj(n.shape, Crescent)
        s.starting_fade = c.f32(s.starting_fade)
        s.ending_fade = c.f32(s.ending_fade)
        s.starting_angle = _l_ring_single(c, s.starting_angle)
        s.ending_angle = _l_ring_single(c, s.ending_angle, 360.0)
        n.shape = s
    elif shape == 0:
        n.shape = None
    else:
        c.fail(f"unsupported ring shape {shape}")
    n.vertex_count = c.i32(n.vertex_count)
    # the viewing angle is always loaded with the 1.5 layout
    n.viewing_angle = c.at_version(1500, lambda: _l_ring_single(c, n.viewing_angle, 360.0))
    n.outer = _l_ring_location(c, n.outer)
    n.inner = _l_ring_location(c, n.inner)
    n.center_ratio = _l_ring_single(c, n.center_ratio, 0.5)
    n.outer_color = _l_color(c, n.outer_color)
    n.center_color = _l_color(c, n.center_color)
    n.inner_color = _l_color(c, n.inner_color)


def _l_model(c, n):
    v = c.version
    if v >= 1602:
        n.model_mode = c.i32(n.model_mode)
    if n.model_mode == 0:
        n.model_magnification = c.f32(n.model_magnification)
        n.model = c.i32(n.model)
    elif n.model_mode == 1:
        n.model = c.i32(n.model)
    elif n.model_mode != 2:
        c.fail(f"unsupported model reference {n.model_mode}")
    n.billboard = c.i32(n.billboard)
    n.culling = c.i32(n.culling)
    n.color = _l_color(c, n.color)
    if 1600 <= v < 1602:
        flag = c.i32(1 if n.legacy_falloff is not None else 0)
        if flag == 1:
            n.legacy_falloff = _l_falloff(c, n.legacy_falloff)
        elif c.reading:
            n.legacy_falloff = None


def _l_track(c, n):
    n.texture_uv = _l_texture_uv(c, n.texture_uv)
    for name in ("size_front", "size_middle", "size_back"):
        if c.i32(0) != 0:
            c.fail("unsupported track size type")
        setattr(n, name, c.f32(getattr(n, name)))
    n.spline_division = c.i32(n.spline_division)
    if c.version >= 1700:
        n.smoothing = c.i32(n.smoothing)
        n.time_type = c.i32(n.time_type)
    for name in ("color_left", "color_left_middle", "color_center", "color_center_middle",
                 "color_right", "color_right_middle"):
        setattr(n, name, _l_color(c, getattr(n, name)))


_RENDERERS = {NODE_NONE: None, NODE_SPRITE: _l_sprite, NODE_RIBBON: _l_ribbon, NODE_RING: _l_ring,
              NODE_MODEL: _l_model, NODE_TRACK: _l_track}


def _l_sound(c, s):
    t = c.i32(1 if s is not None else 0)
    if t == 0:
        return None
    if t != 1:
        c.fail(f"unsupported sound type {t}")
    s = c.obj(s, Sound)
    s.wave = c.i32(s.wave)
    s.volume = c.rf(s.volume)
    s.pitch = c.rf(s.pitch)
    s.pan_type = c.i32(s.pan_type)
    s.pan = c.rf(s.pan)
    s.distance = c.f32(s.distance)
    s.delay = c.ri(s.delay)
    return s


def _l_common_values(c, n):
    def body():
        n.ref_max_generation = c.i32(n.ref_max_generation)
        n.ref_life = c.ref(n.ref_life)
        n.ref_generation_time = c.ref(n.ref_generation_time)
        n.ref_generation_offset = c.ref(n.ref_generation_offset)
        n.max_generation = c.i32(n.max_generation)
        n.bind_translation = c.i32(n.bind_translation)
        n.bind_rotation = c.i32(n.bind_rotation)
        n.bind_scale = c.i32(n.bind_scale)
        n.remove_when_life_ends = c.bool(n.remove_when_life_ends)
        n.remove_when_parent_removed = c.bool(n.remove_when_parent_removed)
        n.remove_when_children_removed = c.bool(n.remove_when_children_removed)
        n.life = c.ri(n.life)
        n.generation_time = c.rf(n.generation_time)
        n.generation_offset = c.rf(n.generation_offset)
    c.sized(body, "common values")


def _l_trigger(c, n):
    names = ("trigger_start", "trigger_stop", "trigger_remove")
    flags = c.u8(sum(1 << i for i, k in enumerate(names) if getattr(n, k) is not None))
    if flags & ~7:
        c.fail(f"unknown trigger flags {flags:#x}")
    for i, k in enumerate(names):
        if flags & (1 << i):
            setattr(n, k, c.u8s(getattr(n, k), 2))
        elif c.reading:
            setattr(n, k, None)


def _l_node(c, n, index):
    c.push(f"node{index}")
    t = c.i32(n.TYPE if not c.reading else 0)
    if c.reading:
        if t not in _NODE_CLASSES:
            c.fail(f"unsupported node type {t}")
        n = _NODE_CLASSES[t]()
    v = c.version
    n.visible = c.bool(n.visible)
    n.rendering_priority = c.i32(n.rendering_priority)
    _l_common_values(c, n)
    if v >= 1600 and n.bind_translation in (BIND_NOT_FOLLOW_PARENT, BIND_WHEN_CREATING_FOLLOW_PARENT):
        n.steering_max_follow_speed = c.rf(n.steering_max_follow_speed)
        n.steering_speed = c.rf(n.steering_speed)
    if v >= 1700:
        _l_trigger(c, n)
    if v >= 1702:
        n.lod_matching = c.i32(n.lod_matching)
        n.lod_behaviour = c.i32(n.lod_behaviour)
    n.translation = _l_translation(c, n.translation)
    n.force_fields = c.list(n.force_fields, lambda f: _l_force_field(c, f), limit=4)
    if v <= 1600:
        n.location_abs = _l_location_abs(c, n.location_abs)
    n.rotation = _l_rotation(c, n.rotation)
    n.scale = _l_scaling(c, n.scale)
    _l_spawn(c, n)
    # depth
    n.depth_offset = c.f32(n.depth_offset)
    n.depth_offset_scaled_with_camera = c.bool(n.depth_offset_scaled_with_camera)
    n.depth_offset_scaled_with_particle_scale = c.bool(n.depth_offset_scaled_with_particle_scale)
    n.depth_scale_suppression = c.f32(n.depth_scale_suppression)
    n.depth_clipping = c.f32(n.depth_clipping)
    n.zsort = c.i32(n.zsort)
    n.drawing_priority = c.i32(n.drawing_priority)
    n.soft_particle = c.f32(n.soft_particle)
    if v >= 1704:
        _l_kill_rules(c, n)
    _l_renderer_common(c, n)
    if v >= 1600:
        if v >= 1605:
            enabled = c.i32(1 if n.alpha_cutoff is not None else 0) == 1
        else:
            enabled = True
        if enabled:
            n.alpha_cutoff = _l_alpha_cutoff(c, _d(n.alpha_cutoff, AlphaCutoff()))
        elif c.reading:
            n.alpha_cutoff = None
    if v >= 1602:
        if c.i32(1 if n.falloff is not None else 0) == 1:
            n.falloff = _l_falloff(c, n.falloff)
        elif c.reading:
            n.falloff = None
    if v >= 1603:
        n.soft_particle_far = c.f32(n.soft_particle_far)
    if v >= 1604:
        n.soft_particle_near = c.f32(n.soft_particle_near)
        n.soft_particle_near_offset = c.f32(n.soft_particle_near_offset)
    if c.i32(t) != t:
        c.fail("renderer parameter type differs from the node type")
    if _RENDERERS[t]:
        _RENDERERS[t](c, n)
    n.sound = _l_sound(c, n.sound)
    counter = iter(range(_LIST_MAX))
    n.children = c.list(n.children, lambda ch: _l_node(c, ch, next(counter)))
    c.pop()
    return n


def _l_procedural_model(c, p):
    p = c.obj(p, ProceduralModel)
    v = c.version
    p.type = c.i32(p.type)
    s = p.shape if not c.reading else (None,) * 10
    if p.type == 0:
        shape = c.f32s(s[0:2], 2) + c.i32s(s[2:4], 2)
        if v >= 1608:
            shape += (c.f32(s[4]),)
    elif p.type == 1:
        shape = (c.i32(s[0]), c.f32(s[1]), c.i32(s[2])) + c.f32s(s[3:9], 6) + (c.i32(s[9]),)
    else:
        c.fail(f"unsupported procedural model type {p.type}")
    p.shape = shape
    p.primitive = c.i32(p.primitive)
    count = {0: 3, 1: 2, 2: 3, 3: 8}.get(p.primitive)
    if count is None:
        c.fail(f"unsupported procedural primitive {p.primitive}")
    p.primitive_params = c.f32s(p.primitive_params, count)
    p.axis = c.i32(p.axis)
    p.tilt_noise = c.tuple(p.tilt_noise, 3, lambda x: c.f32s(x, 2))
    p.wave_noise = c.tuple(p.wave_noise, 3, lambda x: c.f32s(x, 3))
    p.curl_noise = c.tuple(p.curl_noise, 3, lambda x: c.f32s(x, 3))
    colors = c.tuple(p.colors[:6] if not c.reading else None, 6, c.rgba)
    if v >= 1608:
        colors += c.tuple(p.colors[6:] if not c.reading else None, 3, c.rgba)
    else:
        colors += colors[0:3]
    p.colors = colors
    if v >= 1608:
        p.color_center_position = c.f32s(p.color_center_position, 2)
    p.color_center_area = c.f32s(p.color_center_area, 2)
    if v >= 1608:
        p.vertex_color_noise = c.tuple(p.vertex_color_noise, 3, lambda x: c.f32s(x, 3))
        p.uv_position = c.f32s(p.uv_position, 2)
        p.uv_size = c.f32s(p.uv_size, 2)
    return p


def _l_effect(c, e):
    if c.raw(b"SKFE", 4) != b"SKFE":
        c.fail("not an Effekseer binary (no SKFE header)")
    ver = c.i32(c.version)
    if c.reading:
        if not MIN_READ_VERSION <= ver <= MAX_READ_VERSION:
            raise NotImplementedError(
                f"SKFE version {ver} is not supported (reads {MIN_READ_VERSION}-{MAX_READ_VERSION})")
        c.version = e.version = ver
    v = c.version
    paths = lambda lst: c.list(lst, c.utf16, unsigned=True)  # noqa: E731
    e.textures = paths(e.textures)
    e.normal_textures = paths(e.normal_textures)
    e.distortion_textures = paths(e.distortion_textures)
    e.sounds = paths(e.sounds)
    e.models = paths(e.models)
    e.materials = paths(e.materials)

    def curves_and_procedural_models():
        e.curves = c.list(e.curves, c.utf16)
        e.procedural_models = c.list(e.procedural_models, lambda p: _l_procedural_model(c, p))
    if v >= 1607:
        curves_and_procedural_models()
    e.dynamic_inputs = c.list(e.dynamic_inputs, c.f32, unsigned=True)
    e.dynamic_equations = c.list(e.dynamic_equations, c.blob)
    if 1600 <= v < 1607:
        curves_and_procedural_models()
    e.rendering_node_count = c.i32(e.rendering_node_count)
    e.rendering_node_threshold = c.i32(e.rendering_node_threshold)
    e.magnification = c.f32(e.magnification)
    e.random_seed = c.i32(e.random_seed)
    shape = c.i32(1 if e.culling is not None else 0)
    if shape == 1:
        cs = c.obj(e.culling, CullingSphere)
        cs.radius = c.f32(cs.radius)
        cs.location = c.f32s(cs.location, 3)
        e.culling = cs
    elif shape == 0:
        e.culling = None
    else:
        c.fail(f"unsupported culling shape {shape}")
    if v >= 1702:
        e.lod_distances = c.f32s(e.lod_distances, 3)
    # root node
    if c.i32(NODE_ROOT) != NODE_ROOT:
        c.fail("the first node is not the root")
    counter = iter(range(_LIST_MAX))
    e.nodes = c.list(e.nodes, lambda ch: _l_node(c, ch, next(counter)))
    return e


# -------------------------------------------------------------- public API
def _skfe_from(data):
    data = bytes(data)
    if data[:4] == b"EFKE":
        for tag, chunk in read_efkefc_chunks(data):
            if tag == b"BIN_":
                return chunk
        raise FormatError("no BIN_ chunk in the .efkefc data")
    return data


def read_efkefc_chunks(data):
    """Split an .efkefc container ("EFKE", version, then tag/size/data chunks)."""
    data = bytes(data)
    if data[:4] != b"EFKE":
        raise FormatError("not an .efkefc container")
    pos, chunks = 8, []
    while pos < len(data):
        if pos + 8 > len(data):
            raise FormatError("truncated chunk header")
        tag = data[pos:pos + 4]
        size = struct.unpack_from("<i", data, pos + 4)[0]
        if size < 0 or pos + 8 + size > len(data):
            raise FormatError(f"bad size for chunk {tag!r}")
        chunks.append((tag, data[pos + 8:pos + 8 + size]))
        pos += 8 + size
    return chunks


def read_efk(data) -> Effect:
    """Parse an SKFE binary (or the first BIN_ chunk of an .efkefc)."""
    c = _Codec(_skfe_from(data))
    e = _l_effect(c, Effect())
    if c.pos != len(c.buf):
        raise FormatError(f"{len(c.buf) - c.pos} bytes left after the node tree")
    return e


def _walk(nodes):
    for n in nodes:
        yield n
        yield from _walk(n.children)


def _render_order(effect):
    """The editor's rendering order: nodes in tree order, sorted by drawing
    priority; returns ({id(node): priority}, count, threshold)."""
    nodes = list(_walk(effect.nodes))
    order = sorted(range(len(nodes)), key=lambda i: nodes[i].drawing_priority * 255 + i)
    prio = {id(nodes[i]): k for k, i in enumerate(order)}
    threshold = sum(1 for n in nodes if n.drawing_priority < 0)
    return prio, len(nodes), threshold


def _convert(effect, version=VERSION, warn=True):
    """A copy of ``effect`` as a file of ``version`` would hold it: settings
    of older versions are turned into their newer form (as the runtime loader
    does), settings newer than ``version`` go back to their defaults."""
    e = copy.deepcopy(effect)
    src = e.version
    dropped = set()
    if version < 1702 and e.lod_distances != (0.0, 0.0, 0.0):
        dropped.add("LOD distances")
    if version < 1702:
        e.lod_distances = (0.0, 0.0, 0.0)
    for n in _walk(e.nodes):
        if version < 1700:
            if (n.trigger_start, n.trigger_stop, n.trigger_remove) != (None, None, None):
                dropped.add("triggers")
            n.trigger_start = n.trigger_stop = n.trigger_remove = None
            if isinstance(n, (Ribbon, Track)):
                n.time_type = 0
            if isinstance(n, Track):
                n.smoothing = 0
        if version < 1702:
            if (n.lod_matching, n.lod_behaviour) != (0b1111, 0):
                dropped.add("LODs")
            n.lod_matching, n.lod_behaviour = 0b1111, 0
        if version < 1703 and n.material_file is not None and n.material_file.gradients:
            dropped.add("material gradients")
            n.material_file.gradients = []
        if version < 1704:
            if n.kill_rules is not None:
                dropped.add("kill rules")
            n.kill_rules = None
        if src < 1601 <= version:
            for f in n.force_fields:
                if f.type == FF_VORTEX:
                    f.power = _f32(f.power / 5.0)
                    f.subtype = 1           # constant speed
                elif f.type == FF_TURBULENCE:
                    f.power = _f32(f.strength * 10.0)
                    f.strength = 1.0
                    f.subtype = 1           # complicated
        if version > 1600 and n.location_abs is not None:
            a = n.location_abs
            while len(n.force_fields) < 4:
                n.force_fields.append(ForceField())
            if a.type == 1:
                n.force_fields[3] = ForceField(type=FF_GRAVITY, gravity=a.gravity)
            else:
                n.force_fields[3] = ForceField(type=FF_ATTRACTIVE, power=a.force, control=a.control,
                                               min_range=a.min_range, max_range=a.max_range)
            n.location_abs = None
        if version >= 1602 and isinstance(n, Model) and n.legacy_falloff is not None:
            if n.falloff is None:
                n.falloff = n.legacy_falloff
            n.legacy_falloff = None
    e.version = version
    if dropped and warn:
        warnings.warn(f"version {version} cannot hold: {', '.join(sorted(dropped))}", stacklevel=3)
    return e


def _encode(effect, version):
    c = _Codec(None, version)
    _l_effect(c, effect)
    return bytes(c.buf)


def write_efk(effect: Effect) -> bytes:
    """Serialize ``effect`` as an SKFE binary of version 1610."""
    e = _convert(effect, VERSION)
    nodes = list(_walk(e.nodes))
    if e.rendering_node_count is None or e.rendering_node_threshold is None or \
            any(n.rendering_priority is None for n in nodes):
        prio, e.rendering_node_count, e.rendering_node_threshold = _render_order(e)
        for n in nodes:
            n.rendering_priority = prio[id(n)]
    return _encode(e, VERSION)


# ------------------------------------------------------------------ helpers
def describe(obj, indent=0, out=None):
    """Print the fields of ``obj`` that differ from their defaults."""
    out = out if out is not None else sys.stdout
    pad = "  " * indent

    def fmt(v):
        if isinstance(v, float):
            return repr(v) if v != FLT_MAX else "FLT_MAX"
        if isinstance(v, tuple):
            return "(" + ", ".join(fmt(x) for x in v) + ("," if len(v) == 1 else "") + ")"
        return repr(v)

    if isinstance(obj, Effect):
        for f in dataclasses.fields(obj):
            if f.name != "nodes":
                v = getattr(obj, f.name)
                if v not in ([], None):
                    print(f"{pad}{f.name} = {fmt(v)}", file=out)
        for n in obj.nodes:
            describe(n, indent, out)
        return
    if not dataclasses.is_dataclass(obj):
        print(pad + fmt(obj), file=out)
        return
    default = type(obj)()
    print(f"{pad}{type(obj).__name__}", file=out)
    for f in dataclasses.fields(obj):
        if f.name == "children":
            continue
        v, d = getattr(obj, f.name), getattr(default, f.name)
        if v == d:
            continue
        if dataclasses.is_dataclass(v):
            print(f"{pad}  {f.name} =", file=out)
            describe(v, indent + 2, out)
        elif isinstance(v, list) and v and dataclasses.is_dataclass(v[0]):
            print(f"{pad}  {f.name} = [", file=out)
            for x in v:
                describe(x, indent + 2, out)
            print(f"{pad}  ]", file=out)
        else:
            print(f"{pad}  {f.name} = {fmt(v)}", file=out)
    for ch in getattr(obj, "children", []):
        describe(ch, indent + 1, out)


def _floats_of(obj, path=""):
    """Yield (path, value) for every float in a parsed effect."""
    if isinstance(obj, float):
        yield path, obj
    elif isinstance(obj, (tuple, list)):
        for i, x in enumerate(obj):
            yield from _floats_of(x, f"{path}[{i}]")
    elif dataclasses.is_dataclass(obj):
        for f in dataclasses.fields(obj):
            yield from _floats_of(getattr(obj, f.name), f"{path}.{f.name}")


def _suspicious_floats(effect):
    bad = []
    for path, v in _floats_of(effect):
        if math.isnan(v) or math.isinf(v):
            bad.append((path, v))
        elif v != 0.0 and v != FLT_MAX and -FLT_MAX != v and (abs(v) < 1e-20 or abs(v) > 1e9):
            bad.append((path, v))
    return bad


def _tree(nodes, depth=0):
    lines = []
    for n in nodes:
        what = type(n).__name__
        extra = []
        if getattr(n, "texture", -1) >= 0:
            extra.append(f"tex {n.texture}")
        if n.max_generation == INFINITE:
            extra.append("gen inf")
        else:
            extra.append(f"gen {n.max_generation}")
        extra.append(f"life {n.life[0]}-{n.life[1]}")
        lines.append("    " + "  " * depth + f"{what} ({', '.join(extra)})")
        lines += _tree(n.children, depth + 1)
    return lines


def _without(effect, names):
    e = copy.deepcopy(effect)
    for n in names:
        setattr(e, n, None)
    return e


def _first_difference(a, b, path="effect"):
    if type(a) is not type(b):
        return f"{path}: {type(a).__name__} != {type(b).__name__}"
    if dataclasses.is_dataclass(a):
        for f in dataclasses.fields(a):
            d = _first_difference(getattr(a, f.name), getattr(b, f.name), f"{path}.{f.name}")
            if d:
                return d
        return None
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = _first_difference(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if a == b else f"{path}: {a!r} != {b!r}"


def selftest(folder, verbose=False):
    """Check every BIN_ chunk of the .efkefc files in ``folder``."""
    files = sorted(f for f in os.listdir(folder) if f.endswith(".efkefc"))
    failures = 0
    checked = 0
    for name in files:
        data = open(os.path.join(folder, name), "rb").read()
        bins = [ch for tag, ch in read_efkefc_chunks(data) if tag == b"BIN_"]
        for k, chunk in enumerate(bins):
            label = f"{name} BIN_#{k + 1}"
            ver = struct.unpack_from("<i", chunk, 4)[0]
            results = []
            ok = True
            try:
                e = read_efk(chunk)
            except NotImplementedError as ex:
                print(f"{label}: v{ver} skipped ({ex})")
                continue
            except FormatError as ex:
                print(f"{label}: v{ver} READ FAILED: {ex}")
                failures += 1
                continue
            checked += 1
            nodes = list(_walk(e.nodes))
            results.append(f"read {len(chunk)} bytes, {len(nodes)} nodes")
            # 1. plausibility
            bad = _suspicious_floats(e)
            if bad:
                ok = False
                results.append(f"SUSPICIOUS floats: {bad[:4]}")
            prio, count, threshold = _render_order(e)
            if [prio[id(n)] for n in nodes] != [n.rendering_priority for n in nodes] or \
                    (count, threshold) != (e.rendering_node_count, e.rendering_node_threshold):
                results.append("note: rendering order differs from the editor's rule")
            # 2. byte-exact at the file's own version (1610 is required)
            same = _encode(e, ver) == chunk
            results.append(f"re-encode v{ver} {'identical' if same else 'DIFFERS'}")
            if not same:
                ok = False
            # 3. through the 1610 writer
            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    out = write_efk(e)
                    expect = _convert(e, VERSION, warn=False)
                back = read_efk(out)
                diff = _first_difference(back, expect)
                if diff:
                    ok = False
                    results.append(f"1610 round trip DIFFERS: {diff}")
                else:
                    note = f" (dropped: {caught[0].message})" if caught else ""
                    results.append(f"1610 round trip equal{note}")
                if ver == VERSION and out != chunk:
                    ok = False
                    results.append("write_efk output DIFFERS from the file")
            except Exception as ex:  # noqa: BLE001
                ok = False
                results.append(f"1610 round trip FAILED: {type(ex).__name__}: {ex}")
            failures += 0 if ok else 1
            print(f"{label}: v{ver} {'OK' if ok else 'FAIL'}: " + "; ".join(results))
            if verbose:
                print("\n".join(_tree(e.nodes)))
    print(f"{checked} binaries checked, {failures} failed")
    return failures == 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--selftest":
        sys.exit(0 if selftest(args[1], verbose="-v" in args[2:]) else 1)
    if len(args) == 1 and os.path.isfile(args[0]):
        describe(read_efk(open(args[0], "rb").read()))
        sys.exit(0)
    print("usage: efkformat.py --selftest <folder of .efkefc> [-v]\n"
          "       efkformat.py <file.efk|file.efkefc>   (print its non-default settings)")
    sys.exit(2)
