#!/usr/bin/env python3
"""Rebuilds the sample's character sprites and backgrounds at 1920x1080 from the original
800x600-era art in tools/assets/src, with Real-ESRGAN.

usage: python3 tools/assets/upscale.py [name ...]     (no names: all of them)

Real-ESRGAN (https://github.com/xinntao/Real-ESRGAN, BSD-3-Clause) runs here in NumPy, so
nothing beyond NumPy and Pillow is needed; it is slow (about half an hour for everything on
two cores). The weights are downloaded on first use into tools/assets/.weights (gitignored).
The network upscales 4x; the result is then scaled down to the sample's 1.8x (sprites) or
2.4x and cropped to 16:9 (backgrounds), so the line art comes out sharp instead of blurred.
"""
import hashlib, os, pickle, sys, time, urllib.request, zipfile
from collections import OrderedDict
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(HERE, "src")
WEIGHTS_DIR = os.path.join(HERE, ".weights")

MODELS = {
    # name: (url, sha256, residual blocks)
    "anime": ("https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
              "f872d837d3c90ed2e05227bed711af5671a6fd1c9f7d7e91c911a61f155e99da", 6),
    "photo": ("https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
              "4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1", 23),
}

# output (relative to the repo), source in src/, model, output size, crop (left, top) after scaling
JOBS = [
    ("data/fgimage/ch_0_0_1.png", "ch_0_0_1.png", "anime", (540, 1620), None),
    ("data/fgimage/ch_0_0_2.png", "ch_0_0_2.png", "anime", (540, 1620), None),
    ("data/fgimage/ch_0_0_3.png", "ch_0_0_3.png", "anime", (540, 1620), None),
    ("data/fgimage/ch_1_0_1.png", "ch_1_0_1.png", "anime", (324, 972), None),
    ("data/fgimage/ch_2_0_1.png", "ch_2_0_1.png", "anime", (810, 2430), None),
    # 800x600 -> 1920x1440, the middle 1080 lines
    ("data/bgimage/bg01_01.png", "bg01_01.png", "photo", (1920, 1440), (0, 180, 1920, 1080)),
    ("data/bgimage/event1.jpg", "event1.jpg", "photo", (1920, 1440), (0, 180, 1920, 1080)),
]
# CG/Replay thumbnails (setCGImage's picture area), made from a job's output
THUMBS = [("data/thum/thum_event1.png", "data/bgimage/event1.jpg", (208, 117))]


# --- a torch zip checkpoint, read without torch ----------------------------------------
_DT = {"FloatStorage": np.float32, "HalfStorage": np.float16, "DoubleStorage": np.float64,
       "LongStorage": np.int64, "IntStorage": np.int32}


def load_pth(path):
    z = zipfile.ZipFile(path)
    pkl = [n for n in z.namelist() if n.endswith("data.pkl")][0]
    prefix = pkl[: -len("data.pkl")]

    class StorageType:
        def __init__(self, name):
            self.dtype = _DT[name]

    def rebuild(storage, offset, size, stride, *a):
        if not size:
            return storage[offset].copy()
        item = storage.itemsize
        return np.lib.stride_tricks.as_strided(storage[offset:], shape=tuple(size),
                                               strides=tuple(s * item for s in stride)).copy()

    class Unpickler(pickle.Unpickler):
        def find_class(self, mod, name):
            if mod == "torch._utils" and name == "_rebuild_tensor_v2":
                return rebuild
            if mod == "torch._utils" and name == "_rebuild_parameter":
                return lambda data, requires_grad, hooks, *a: data
            if mod == "torch" and name.endswith("Storage"):
                return StorageType(name)
            if mod == "collections" and name == "OrderedDict":
                return OrderedDict
            raise pickle.UnpicklingError("unexpected %s.%s in the checkpoint" % (mod, name))

        def persistent_load(self, pid):
            _, stype, key, _, numel = pid
            return np.frombuffer(z.read(prefix + "data/" + key), dtype=stype.dtype)[:numel]

    sd = Unpickler(z.open(pkl)).load()
    for k in ("params_ema", "params"):
        if k in sd:
            return sd[k]
    return sd


# --- RRDBNet ---------------------------------------------------------------------------
class Net:
    def __init__(self, sd, blocks):
        self.w = {}  # 3x3 convolutions as (9*Cin, Cout) matrices for a channels-last im2col
        for k, v in sd.items():
            if k.endswith(".weight"):
                cout, cin, kh, kw = v.shape
                self.w[k[:-7]] = (np.ascontiguousarray(v.transpose(2, 3, 1, 0).reshape(kh * kw * cin, cout)).astype(np.float32),
                                  sd[k[:-7] + ".bias"].astype(np.float32))
        self.blocks = blocks

    def conv(self, x, name, act=False):
        w, b = self.w[name]
        h, wd, c = x.shape
        p = np.pad(x, ((1, 1), (1, 1), (0, 0)))
        s = p.strides
        win = np.lib.stride_tricks.as_strided(p, shape=(h, wd, 3, 3, c), strides=(s[0], s[1], s[0], s[1], s[2]))
        out = (win.reshape(h * wd, 9 * c) @ w + b).reshape(h, wd, -1)
        if act:
            np.maximum(out, out * 0.2, out=out)  # leaky ReLU
        return out

    def rdb(self, x, p):
        x1 = self.conv(x, p + ".conv1", True)
        x2 = self.conv(np.concatenate([x, x1], 2), p + ".conv2", True)
        x3 = self.conv(np.concatenate([x, x1, x2], 2), p + ".conv3", True)
        x4 = self.conv(np.concatenate([x, x1, x2, x3], 2), p + ".conv4", True)
        return self.conv(np.concatenate([x, x1, x2, x3, x4], 2), p + ".conv5") * 0.2 + x

    def __call__(self, img):
        f = self.conv(img, "conv_first")
        b = f
        for i in range(self.blocks):
            p = "body.%d" % i
            b = self.rdb(self.rdb(self.rdb(b, p + ".rdb1"), p + ".rdb2"), p + ".rdb3") * 0.2 + b
        f = f + self.conv(b, "conv_body")
        f = self.conv(f.repeat(2, 0).repeat(2, 1), "conv_up1", True)
        f = self.conv(f.repeat(2, 0).repeat(2, 1), "conv_up2", True)
        return self.conv(self.conv(f, "conv_hr", True), "conv_last")


def upscale4(net, img, label, tile=96, pad=10):
    """HxWx3 float32 in [0, 1] -> 4x, in overlapping tiles"""
    h, w, _ = img.shape
    out = np.zeros((h * 4, w * 4, 3), np.float32)
    total = ((h + tile - 1) // tile) * ((w + tile - 1) // tile)
    n = 0
    t0 = time.time()
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            y0, x0 = max(0, y - pad), max(0, x - pad)
            y1, x1 = min(h, y + tile + pad), min(w, x + tile + pad)
            r = net(img[y0:y1, x0:x1])
            ty, tx = (y - y0) * 4, (x - x0) * 4
            th, tw = min(tile, h - y) * 4, min(tile, w - x) * 4
            out[y * 4:y * 4 + th, x * 4:x * 4 + tw] = r[ty:ty + th, tx:tx + tw]
            n += 1
            print("\r  %s: tile %d/%d, %ds" % (label, n, total, time.time() - t0), end="", flush=True)
    print()
    return np.clip(out, 0, 1)


def bleed(rgb, alpha):
    """Spreads the colours of opaque pixels into the transparent ones, so the upscaler and the
    downscale don't pull whatever colour the transparent pixels happen to have into the edges"""
    a = (alpha > 0).astype(np.float32)[:, :, None]
    acc_c, acc_a = rgb * a, a.copy()
    im_c, im_a = acc_c, acc_a
    for _ in range(64):
        if (acc_a > 0).all():
            break
        # one step of a 3x3 box spread
        pc = np.pad(im_c, ((1, 1), (1, 1), (0, 0)), mode="edge")
        pa = np.pad(im_a, ((1, 1), (1, 1), (0, 0)), mode="edge")
        im_c = sum(pc[dy:dy + rgb.shape[0], dx:dx + rgb.shape[1]] for dy in range(3) for dx in range(3))
        im_a = sum(pa[dy:dy + rgb.shape[0], dx:dx + rgb.shape[1]] for dy in range(3) for dx in range(3))
        fill = (acc_a == 0) & (im_a > 0)
        acc_c = np.where(fill, im_c / np.maximum(im_a, 1e-6), acc_c)
        acc_a = np.where(fill, 1.0, acc_a)
        im_c, im_a = acc_c * acc_a, acc_a
    return np.where(a > 0, rgb, acc_c / np.maximum(acc_a, 1e-6))


def weights(model):
    url, sha, blocks = MODELS[model]
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    path = os.path.join(WEIGHTS_DIR, os.path.basename(url))
    if not os.path.exists(path):
        print("downloading", url, flush=True)
        urllib.request.urlretrieve(url, path + ".part")
        os.replace(path + ".part", path)
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != sha:
        raise SystemExit("%s: unexpected sha256 %s" % (path, digest))
    return Net(load_pth(path), blocks)


def resize_premultiplied(rgba, size):
    """Lanczos resize of an RGBA float image without dark fringes at the alpha edges"""
    a = rgba[:, :, 3:4]
    pre = np.concatenate([rgba[:, :, :3] * a, a], 2)
    chans = [np.asarray(Image.fromarray(pre[:, :, i]).resize(size, Image.LANCZOS)) for i in range(4)]
    out = np.clip(np.stack(chans, 2), 0, 1)
    al = out[:, :, 3:4]
    rgb = np.where(al > 1e-4, out[:, :, :3] / np.maximum(al, 1e-4), 0)
    return np.concatenate([np.clip(rgb, 0, 1), al], 2)


def run(job, nets):
    dst, src, model, size, crop = job
    if model not in nets:
        nets[model] = weights(model)
    net = nets[model]
    im = Image.open(os.path.join(SRC, src))
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    a = np.asarray(im.convert("RGBA" if has_alpha else "RGB")).astype(np.float32) / 255
    rgb = a[:, :, :3]
    if has_alpha:
        rgb = bleed(rgb, a[:, :, 3])
    big = upscale4(net, np.ascontiguousarray(rgb, dtype=np.float32), src + " colour")
    if has_alpha:
        al = upscale4(net, np.repeat(a[:, :, 3:4], 3, 2), src + " alpha").mean(2, keepdims=True)
        out = resize_premultiplied(np.concatenate([big, al], 2), size)
    else:
        chans = [np.asarray(Image.fromarray(big[:, :, i]).resize(size, Image.LANCZOS)) for i in range(3)]
        out = np.clip(np.stack(chans, 2), 0, 1)
    img = Image.fromarray((out * 255 + 0.5).astype(np.uint8))
    if crop:
        l, t, w, h = crop
        img = img.crop((l, t, l + w, t + h))
    path = os.path.join(REPO, dst)
    if path.endswith(".jpg"):
        img.convert("RGB").save(path, quality=92, subsampling=0)
    else:
        img.save(path, optimize=True)
    print("wrote", dst, img.size, flush=True)


def thumbs():
    for dst, src, size in THUMBS:
        im = Image.open(os.path.join(REPO, src)).convert("RGB")
        im.resize(size, Image.LANCZOS, reducing_gap=3.0).save(os.path.join(REPO, dst), optimize=True)
        print("wrote", dst, size, flush=True)


def main():
    names = sys.argv[1:]
    jobs = [j for j in JOBS if not names or os.path.basename(j[0]) in names or j[1] in names]
    if names and not jobs:
        raise SystemExit("nothing matches %s; jobs: %s" % (names, [os.path.basename(j[0]) for j in JOBS]))
    nets = {}
    for job in sorted(jobs, key=lambda j: j[2]):
        run(job, nets)
    thumbs()


if __name__ == "__main__":
    main()
