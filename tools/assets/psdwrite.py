#!/usr/bin/env python3
"""Writes Photoshop (.psd) files with layers and folders, with nothing but the standard library.

psdlayer.tjs (characters drawn from layers) reads a layer structure either from its text format,
<name>.txt with a picture per layer (<name>_<layer id>.png), or from a .psd through the psdfile
plugin; kagex-release turns a .psd into the text format. psdfile can write PSDs but not folders,
which a character's eyes and mouths are, so this makes them: from a layer structure in the text
format (the other way round from kagex-release), or from layers given in Python.

    python3 tools/assets/psdwrite.py data/fgimage/pip/pip_0.txt /tmp/pip_0.psd

The layers keep their names, places, opacity, visibility and layer IDs (Photoshop's 'lyid'),
the folders theirs, so the PSD reads back as the same structure. The pictures are 8-bit RGBA
PNGs; the PSD is 8-bit RGB with transparency, its channels RLE-compressed. Its merged image
(what a viewer that doesn't read layers shows) is left transparent: Photoshop makes it again
when it saves the file.

Used by tools/smoketest.py and tools/release/test/smoke.py to make test PSDs.
"""
import os
import struct
import sys
import zlib

# ---------------------------------------------------------------- PNG (8-bit, not interlaced)


def read_png(path):
    """(width, height, RGBA bytes) of an 8-bit PNG: grey, grey+alpha, RGB, RGBA or a palette"""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("%s: not a PNG" % path)
    pos, idat, plte, trns = 8, [], b"", b""
    width = height = depth = ctype = interlace = None
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            plte = body
        elif kind == b"tRNS":
            trns = body
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if depth != 8 or interlace:
        raise ValueError("%s: only 8-bit PNGs that aren't interlaced" % path)
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(b"".join(idat))
    stride = width * bpp
    out = bytearray(width * height * 4)
    prev = bytearray(stride)
    for y in range(height):
        at = y * (stride + 1)
        filt, line = raw[at], bytearray(raw[at + 1:at + 1 + stride])
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if filt == 1:
                line[x] = (line[x] + a) & 255
            elif filt == 2:
                line[x] = (line[x] + b) & 255
            elif filt == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif filt == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        o = y * width * 4
        for x in range(width):
            s = x * bpp
            if ctype == 6:
                out[o:o + 4] = line[s:s + 4]
            elif ctype == 2:
                out[o:o + 4] = line[s:s + 3] + b"\xff"
            elif ctype == 4:
                out[o:o + 4] = bytes((line[s], line[s], line[s], line[s + 1]))
            elif ctype == 0:
                out[o:o + 4] = bytes((line[s], line[s], line[s], 255))
            else:
                i = line[s]
                out[o:o + 3] = plte[i * 3:i * 3 + 3]
                out[o + 3] = trns[i] if i < len(trns) else 255
            o += 4
        prev = line
    return width, height, bytes(out)


# ---------------------------------------------------------------- PSD


def packbits(row):
    """PackBits (RLE) of one row"""
    out = bytearray()
    i, n = 0, len(row)
    while i < n:
        run = 1
        while i + run < n and run < 128 and row[i + run] == row[i]:
            run += 1
        if run >= 2:   # a byte repeated: 257 - run, then the byte
            out += bytes((257 - run, row[i]))
            i += run
            continue
        start = i      # bytes as they are, up to the next repeat: their count - 1, then them
        i += 1
        while i < n and i - start < 128 and not (i + 1 < n and row[i] == row[i + 1]):
            i += 1
        out.append(i - start - 1)
        out += row[start:i]
    return bytes(out)


def channel_rle(plane, width, height):
    """a channel's data, compressed: 1, each row's length, then the rows"""
    if width <= 0 or height <= 0:
        return struct.pack(">H", 0)
    rows = [packbits(plane[y * width:(y + 1) * width]) for y in range(height)]
    return struct.pack(">H", 1) + b"".join(struct.pack(">H", len(r)) for r in rows) + b"".join(rows)


def pascal_name(name):
    raw = name.encode("ascii", "replace")[:255]
    s = bytes((len(raw),)) + raw
    return s + b"\0" * (-len(s) % 4)


def block(key, body):
    """an additional layer information block"""
    body += b"\0" * (len(body) % 2)
    return b"8BIM" + key + struct.pack(">I", len(body)) + body


def unicode_name(name):
    u = name.encode("utf-16-be")
    return struct.pack(">I", len(u) // 2) + u


def layer_record(r):
    """one layer record and its channels' data. r: name, left, top, width, height, rgba (or
    None), opacity, visible, layer_id, blend (4 bytes), section (None, or 1 folder, 3 its end)"""
    w, h = (r["width"], r["height"]) if r.get("rgba") else (0, 0)
    planes = []
    for ch, k in ((-1, 3), (0, 0), (1, 1), (2, 2)):
        plane = r["rgba"][k::4] if w and h else b""
        planes.append((ch, channel_rle(plane, w, h)))
    rec = struct.pack(">iiiiH", r["top"], r["left"], r["top"] + h, r["left"] + w, len(planes))
    for ch, data in planes:
        rec += struct.pack(">hI", ch, len(data))
    flags = 0x08 | (0 if r.get("visible", True) else 0x02)
    rec += b"8BIM" + r.get("blend", b"norm") + struct.pack(">BBBB", r.get("opacity", 255), 0, flags, 0)
    extra = struct.pack(">I", 0) + struct.pack(">I", 0) + pascal_name(r["name"])
    extra += block(b"luni", unicode_name(r["name"]))
    if r.get("layer_id") is not None:
        extra += block(b"lyid", struct.pack(">I", r["layer_id"]))
    if r.get("section"):
        extra += block(b"lsct", struct.pack(">I", r["section"]) + (b"8BIMpass" if r["section"] == 1 else b""))
    rec += struct.pack(">I", len(extra)) + extra
    return rec, b"".join(d for ch, d in planes)


def write_psd(path, width, height, layers, groups=None):
    """Writes path. layers: top first, each a dict with name, left, top, width, height, rgba
    (width*height*4 bytes), and optional blend (Photoshop's 4-byte key, b"norm"), opacity (255),
    visible (True), layer_id, group (the ID of its folder). groups: folder ID -> dict with name, and optional opacity, visible,
    layer_id (its ID, the key by default) and group (the folder it's in)."""
    groups = groups or {}

    # the tree, top first: a folder where its topmost layer is
    def chain(gid):
        out = []
        while gid is not None and gid in groups and gid not in out:
            out.insert(0, gid)
            gid = groups[gid].get("group")
        return out
    root, nodes = [], {}
    for l in layers:
        where = root
        for gid in chain(l.get("group")):
            if gid not in nodes:
                nodes[gid] = []
                where.append(("group", gid))
            where = nodes[gid]
        where.append(("layer", l))
    for gid in groups:   # folders with no layers, at the bottom
        if gid not in nodes:
            nodes[gid] = []
            root.append(("group", gid))

    ids = [l["layer_id"] for l in layers if l.get("layer_id") is not None]
    ids += [g.get("layer_id", k) for k, g in groups.items() if isinstance(g.get("layer_id", k), int)]
    next_id = [max(ids + [0]) + 1]

    def records(items):
        """PSD's order: bottom first, a folder's end below what it holds, the folder above"""
        out = []
        for kind, x in reversed(items):
            if kind == "layer":
                out.append(dict(x, blend=x.get("blend", b"norm")))
                continue
            g = groups[x]
            out.append(dict(name="</Layer group>", left=0, top=0, width=0, height=0, rgba=None,
                            layer_id=next_id[0], section=3, blend=b"norm"))
            next_id[0] += 1
            out += records(nodes[x])
            out.append(dict(name=g["name"], left=0, top=0, width=0, height=0, rgba=None,
                            opacity=g.get("opacity", 255), visible=g.get("visible", True),
                            layer_id=g.get("layer_id", x), section=1, blend=b"pass"))
        return out
    recs = records(root)

    info = struct.pack(">h", -len(recs))   # negative: the merged image has transparency
    data = b""
    for r in recs:
        rec, chans = layer_record(r)
        info += rec
        data += chans
    info += data
    info += b"\0" * (len(info) % 2)
    layer_info = struct.pack(">I", len(info)) + info
    mask_section = layer_info + struct.pack(">I", 0)   # no global layer mask

    # the merged image: transparent (RLE: every row a run of zeros)
    row = packbits(bytes(width))
    merged = struct.pack(">H", 1) + struct.pack(">H", len(row)) * (height * 4) + row * (height * 4)

    with open(path, "wb") as f:
        f.write(b"8BPS" + struct.pack(">H6xHIIHH", 1, 4, height, width, 8, 3))
        f.write(struct.pack(">I", 0))   # no colour mode data
        f.write(struct.pack(">I", 0))   # no image resources
        f.write(struct.pack(">I", len(mask_section)) + mask_section)
        f.write(merged)


# the engine's layer types (as psdfile reports a PSD's blend modes) back to Photoshop's keys
BLEND_KEYS = {13: b"norm", 14: b"lddg", 15: b"lbrn", 16: b"mul ", 17: b"scrn", 18: b"over", 19: b"hLit",
              20: b"sLit", 21: b"div ", 23: b"idiv", 24: b"lite", 25: b"dark", 26: b"diff", 28: b"smud"}


def read_structure(txt):
    """psdlayer.tjs's text format: (width, height, layers, groups) as write_psd takes them, with
    each layer's picture read from <name>_<layer id>.png beside it"""
    base = txt[:-4] if txt.lower().endswith(".txt") else txt
    width = height = 0
    layers, groups = [], {}
    with open(txt, encoding="utf-8-sig") as f:
        for line in f.read().splitlines():
            if not line or line.startswith("#"):
                continue
            c = line.split("\t") + [""] * 13
            if c[0] == "":
                width, height = int(c[4]), int(c[5])
                continue
            num = lambda v, d=None: int(v) if v.strip() != "" else d
            entry = dict(name=c[1], left=num(c[2], 0), top=num(c[3], 0), width=num(c[4], 0), height=num(c[5], 0),
                         blend=BLEND_KEYS.get(num(c[6], 13), b"norm"), opacity=num(c[7], 255), visible=num(c[8], 1) != 0,
                         layer_id=num(c[9]), group=num(c[10]))
            if c[0] == "2":
                groups[entry["layer_id"]] = entry
            elif c[0] == "0" and entry["width"] > 0 and entry["height"] > 0:
                w, h, rgba = read_png("%s_%d.png" % (base, entry["layer_id"]))
                if (w, h) != (entry["width"], entry["height"]):
                    raise ValueError("%s_%d.png is %dx%d, not %dx%d" % (base, entry["layer_id"], w, h, entry["width"], entry["height"]))
                entry["rgba"] = rgba
                layers.append(entry)
    return width, height, layers, groups


def structure_to_psd(txt, psd):
    width, height, layers, groups = read_structure(txt)
    write_psd(psd, width, height, layers, groups)
    return len(layers), len(groups)


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    txt = sys.argv[1]
    psd = sys.argv[2] if len(sys.argv) == 3 else os.path.splitext(txt)[0] + ".psd"
    n, g = structure_to_psd(txt, psd)
    print("%s: %d layers, %d folders" % (psd, n, g))


if __name__ == "__main__":
    main()
