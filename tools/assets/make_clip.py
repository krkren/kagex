#!/usr/bin/env python3
"""Packs the layer demo's emblem into a CLIP STUDIO PAINT file, data/fgimage/emblem.clip, with
two layers, badge and star (drawn by make_vector.py), which layer.ks loads one by one through
the clipfile plugin's clip:// storage.

A .clip can't be written from nothing: it carries a database that the clipfile plugin's
CLIPWriter edits but doesn't create. So this starts from the empty canvas in clipparse, the
library clipfile is built on (samples/emptyimage.clip, MIT, at the commit krkrz_dev's clipfile
uses; downloaded once into tools/assets/.cache, or given with --template), and drives the
engine through its REPL as tools/smoketest.py does (so it needs the engine, with the clipfile
plugin, next to data/): it sizes the canvas, puts the badge on the template's layer, adds the
star above it, removes the paper layer and checks the file with CLIPWriter.validate.

usage: python3 tools/assets/make_clip.py [--engine ./krkrz] [--template emptyimage.clip]
"""
import argparse, os, shutil, sys, tempfile, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import make_vector  # noqa: E402

CLIPPARSE = "322a273c0e059d1dee9132af78289efa12a59522"  # krkrz_dev 21d20e9's clipfile -> clipparse
TEMPLATE_URL = "https://raw.githubusercontent.com/wamsoft/clipparse/%s/samples/emptyimage.clip" % CLIPPARSE
OUT = os.path.join(ROOT, "data", "fgimage", "emblem.clip")
SEED = 20261025  # CLIPWriter's external ids, so the same art gives the same file

BUILD = r"""(function() {
	if (typeof global.CLIPWriter == "undefined") Plugins.link("plugin/clipfile.dll");
	var w = new CLIPWriter(), size = %(size)d;
	w.setSeed(%(seed)d);
	if (!w.load("%(template)s")) return "load: " + w.error;
	if (!w.resizeCanvas(size, size)) return "resizeCanvas: " + w.error;
	var badge = new global.Layer(kag, kag.primaryLayer), star = new global.Layer(kag, kag.primaryLayer);
	var whole = new global.Layer(kag, kag.primaryLayer);
	badge.loadImages("%(badge)s");
	star.loadImages("%(star)s");
	whole.loadImages("%(whole)s");
	// the template's raster layer (LayerId 3, above the paper, 4) becomes the badge
	if (!w.setPixels(3, badge)) return "setPixels: " + w.error;
	if (!w.setLayerAttr(3, %%[ name: "badge" ])) return "setLayerAttr: " + w.error;
	if (!w.addLayer("star", 3, star, 3, 0)) return "addLayer: " + w.error;
	if (!w.deleteLayer(4)) return "deleteLayer: " + w.error;
	if (!w.setCanvasPreview(whole)) return "setCanvasPreview: " + w.error;
	var n = w.save("%(out)s");
	invalidate badge; invalidate star; invalidate whole; invalidate w;
	if (!n) return "save failed";
	var problems = CLIPWriter.validate("%(out)s");
	if (problems.count) return "validate: " + problems.join("; ");
	var c = new CLIP(), names = [];
	if (!c.load("%(out)s")) return "reading it back failed";
	for (var i = 0; i < c.layer_count; i++) names.add(c.getLayerName(i));
	return "ok " + n + " bytes, layers " + names.join(", ");
})()"""


def storage(path):
    """a local path as a storage name"""
    return "file://." + os.path.abspath(path).replace("\\", "/")


def template(path):
    if path:
        return path
    cache = os.path.join(HERE, ".cache", "emptyimage-%s.clip" % CLIPPARSE[:12])
    if not os.path.exists(cache):
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        print("downloading", TEMPLATE_URL, flush=True)
        with urllib.request.urlopen(TEMPLATE_URL) as r, open(cache + ".part", "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(cache + ".part", cache)
    return cache


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--engine", default="krkrz.exe" if os.name == "nt" else "./krkrz")
    ap.add_argument("--template", help="clipparse's samples/emptyimage.clip, instead of downloading it")
    opts = ap.parse_args()
    tpl = template(opts.template)

    import smoketest
    work = tempfile.mkdtemp(prefix="make-clip-")
    try:
        parts = {"badge": make_vector.badge(), "star": make_vector.star(), "whole": make_vector.emblem()}
        files = {}
        for name, shapes in parts.items():
            files[name] = os.path.join(work, name + ".png")
            make_vector.bitmap(shapes).save(files[name])
        local_tpl = os.path.join(work, "template.clip")  # CLIPWriter edits a local copy
        shutil.copyfile(tpl, local_tpl)
        out = os.path.join(work, "emblem.clip")

        os.chdir(ROOT)
        eng = smoketest.DesktopEngine(opts.engine, "data", os.path.join(work, "engine"), False)
        try:
            eng.wait("the engine", 'typeof global.kag != "undefined"', timeout=60)
            r = eng._eval(BUILD % dict(size=make_vector.SIZE, seed=SEED, template=storage(local_tpl),
                                       badge=storage(files["badge"]), star=storage(files["star"]),
                                       whole=storage(files["whole"]), out=storage(out)), 120)
        finally:
            eng.stop()
        result = r.get("result", "") if r.get("ok") else "TJS: " + r.get("error", "")
        result = result.strip('"')
        if not result.startswith("ok "):
            sys.exit("make_clip: " + result)
        shutil.copyfile(out, OUT)
        print("wrote data/fgimage/emblem.clip:", result[3:])
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
