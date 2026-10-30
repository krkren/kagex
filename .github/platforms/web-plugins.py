#!/usr/bin/env python3
"""Edits krkrz_web's built-in plugin list (CMakeLists.txt) for kagex, in the CI checkout only:
drops the plugins that come from Wamsoft repositories which aren't public (krkrtemplate,
wamsoft_work; kagex uses none of them), and adds the krkrz_dev plugins kagex uses that
krkrz_web doesn't list: krkreffekseer (Effekseer effects, the efk flip type, with
krkreffekseer-kit.cmake at the end), minizip (zip patches) and clipfile (clip:// images); and
kagex's own xp3crypt (encrypted data.xp3) and scnfile (compiled scenarios), from
$KRKRZ_BASE/xp3crypt and $KRKRZ_BASE/scnfile, with monocypher-kit.cmake at the end (both carry
Monocypher).

krkr_richtext stays out: it doesn't compile for wasm32 at engine 2.6.5. Its main.cpp casts
a tTJSVariant to tjs_intptr_t, and tp_stub only converts to that type on Apple (elsewhere it
is int64_t, which on wasm32 it isn't), so the web build draws text with the engine's own
drawText, the fallback kagex uses wherever the plugin is missing.
krkrlive2d joins too (krkrlive2d-web): the Live2D plugin, from the checkout tools/live2d
build.py --web fetches (build/src), with kagex's Cubism Core for the web underneath — the SDK
for Web itself is private too, and its live2dcubismcore.min.js is loaded as a sidecar script
by web-static-host.py; live2d-web-kit.cmake at the top points the build at the environment.

usage: web-plugins.py <krkrz_web/CMakeLists.txt>"""
import os, re, sys
path = sys.argv[1]
s = open(path, encoding="utf-8").read()
drop = ["getLangName", "textrender", "tjsDataPack", "tlgSliceLoader", "psbfile"]
for name in drop:
    s, n = re.subn(r"^[ \t]*%s[ \t]*\n" % name, "", s, flags=re.M)
    if n > 1:
        sys.exit("expected one %s line in the plugin list, found %d" % (name, n))
    if n == 0:
        # a rerun on a list that was already edited, or upstream moved it — nothing to drop
        print("%s: nothing to drop (already edited upstream?)" % name, file=sys.stderr)
add = ["krkreffekseer", "minizip", "clipfile", "xp3crypt", "scnfile", "krkrlive2d"]
start = s.index("LIST(APPEND TVP_PLUGINS_STATIC")
close = re.compile(r"^[ \t]*\)", re.M).search(s, start)
s = s[:close.start()] + "".join("  %s\n" % name for name in add if not re.search(r"^[ \t]*%s[ \t]*$" % name, s[start:close.start()], re.M)) + s[close.start():]
# the plugin folders: after krkrz_dev's, whose tp_stub and ncbind they use
folders = "LIST(APPEND TVP_PLUGIN_FOLDERS"
fstart = s.index(folders)
fclose = re.compile(r"^[ \t]*\)", re.M).search(s, fstart)
for name, entry in (("krkrlive2d", "${KRKRZ_BASE}/kagex/tools/live2d/build/src"),
                    ("xp3crypt", "${KRKRZ_BASE}/xp3crypt/plugins"),
                    ("scnfile", "${KRKRZ_BASE}/scnfile/plugins")):
    if entry not in s[fstart:fclose.start()]:
        # Live2D's copy goes first: the engine's own tree holds a submodule of the plugin, at
        # its unpatched state (krkrz_dev's plugin folders come first below), and build.py's
        # checkout, patched with EMSCRIPTEN branches, is the one to pick up
        if name == "krkrlive2d":
            s = s.replace(folders, folders + "\n   " + entry, 1)
        else:
            s = s[:fclose.start()] + "   %s\n" % entry + s[fclose.start():]
        fclose = re.compile(r"^[ \t]*\)", re.M).search(s, fstart)
here = os.path.dirname(os.path.abspath(__file__))
# the Live2D kit reads the environment, and goes before the plugin lists are read below
marker = "LIST(APPEND TVP_PLUGIN_FOLDERS"
inc = 'include("%s")\n' % os.path.join(here, "live2d-web-kit.cmake").replace("\\", "/")
if inc not in s:
    s = s.replace(marker, inc + marker, 1)
for kit in ("krkreffekseer-kit.cmake", "monocypher-kit.cmake"):
    line = 'include("%s")\n' % os.path.join(here, kit).replace("\\", "/")
    if line not in s:
        s = s.rstrip("\n") + "\n\n" + line
open(path, "w", encoding="utf-8").write(s)
end = re.compile(r"^[ \t]*\)", re.M).search(s, start).end()
print(s[start:end])
