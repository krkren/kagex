#!/usr/bin/env python3
"""Draws the rule images for the sample's transitions into data/rule.

  rule_shatter.png  3duniversal (extNagano): the screen breaks into glass-like shards that
                    fly outward from the centre, the middle ones first. Each pixel's red is
                    when its shard starts moving (0-255 over the transition), green how fast,
                    blue which way (0 right, 64 down, 128 left, 192 up).
  wipe_brush.png    imagewipe (extNagano): a violet brush stroke that leads the wipe. Each
                    row's switching edge is the rightmost pixel more than 94% opaque; the
                    stroke is drawn over the incoming picture just behind that edge.

usage: python3 tools/assets/make_rules.py
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "rule")
W, H = 1920, 1080

LAVENDER = np.array([166, 144, 255], float)  # the theme's panel colour (make_ui.py)
VIOLET = np.array([80, 37, 255], float)      # its borders and shadows


def shatter(cells=150, seed=7):
    """Voronoi shards: the start time grows with the shard's distance from the centre (with a
    little jitter), the speed varies a little from shard to shard, and each shard moves
    straight out from the centre."""
    rng = np.random.default_rng(seed)
    # jittered grid seeds, so the shards come out evenly sized
    nx = int(round(np.sqrt(cells * W / H)))
    ny = max(1, cells // nx)
    gx, gy = np.meshgrid((np.arange(nx) + 0.5) * W / nx, (np.arange(ny) + 0.5) * H / ny)
    px = (gx + rng.uniform(-0.4, 0.4, gx.shape) * W / nx).ravel()
    py = (gy + rng.uniform(-0.4, 0.4, gy.shape) * H / ny).ravel()
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    owner = np.zeros((H, W), np.int32)
    best = np.full((H, W), np.inf, np.float32)
    for i, (sx, sy) in enumerate(zip(px, py)):
        d = (x - sx) ** 2 + (y - sy) ** 2
        closer = d < best
        best[closer] = d[closer]
        owner[closer] = i
    cx, cy = W / 2, H / 2
    dist = np.hypot(px - cx, py - cy) / np.hypot(cx, cy)
    start = np.clip(dist * 190 + rng.uniform(-12, 12, dist.shape), 0, 210)
    speed = rng.uniform(150, 230, dist.shape)
    angle = np.degrees(np.arctan2(py - cy, px - cx)) % 360  # screen y points down: clockwise
    direction = angle / 360 * 256
    r = start[owner].astype(np.uint8)
    g = speed[owner].astype(np.uint8)
    b = (np.round(direction[owner]) % 256).astype(np.uint8)
    return Image.fromarray(np.dstack([r, g, b]), "RGB")


def brush(width=360, seed=3):
    """A stroke whose right edge is ragged like a dry brush, opaque near the edge and fading
    out to the left, lavender to violet, with faint bristle streaks."""
    rng = np.random.default_rng(seed)
    rows = np.arange(H, dtype=float)
    edge = (width * 0.72
            + 34 * np.sin(rows / 97.0 + 0.6) + 18 * np.sin(rows / 31.0 + 2.1)
            + 5 * np.sin(rows / 9.3) + rng.normal(0, 2.0, H))
    edge = np.convolve(edge, np.ones(7) / 7, mode="same")
    edge[:4], edge[-4:] = edge[4], edge[-5]
    cols = np.arange(width, dtype=float)
    t = cols[None, :] / edge[:, None]                 # 0 at the left, 1 at the edge
    alpha = np.clip((t - 0.15) / 0.6, 0, 1) ** 1.4 * 255
    alpha[t >= 1] = 0
    alpha[(t >= 0.75) & (t < 1)] = 255                # solid behind the edge (> 0xf0)
    mix = np.clip(t, 0, 1)[..., None] ** 1.5
    rgb = LAVENDER * (1 - mix) + VIOLET * mix
    streaks = np.convolve(rng.normal(0, 1, H), np.ones(9) / 9, mode="same")
    rgb = rgb + (streaks[:, None, None] * 18) * (1 - mix)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), "RGBA")


def main():
    os.makedirs(OUT, exist_ok=True)
    shatter().save(os.path.join(OUT, "rule_shatter.png"), optimize=True)
    brush().save(os.path.join(OUT, "wipe_brush.png"), optimize=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
