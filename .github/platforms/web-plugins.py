#!/usr/bin/env python3
"""Edits krkrz_web's built-in plugin list (CMakeLists.txt) for kagex, in the CI checkout only:
drops the plugins that come from Wamsoft repositories which aren't public (krkrtemplate,
wamsoft_work; kagex uses none of them), and adds krkreffekseer (Effekseer effects, the efk
flip type), which krkrz_web doesn't list, with krkreffekseer-kit.cmake at the end.

krkr_richtext stays out: it doesn't compile for wasm32 at engine 2.6.5. Its main.cpp casts
a tTJSVariant to tjs_intptr_t, and tp_stub only converts to that type on Apple (elsewhere it
is int64_t, which on wasm32 it isn't), so the web build draws text with the engine's own
drawText, the fallback kagex uses wherever the plugin is missing.
usage: web-plugins.py <krkrz_web/CMakeLists.txt>"""
import os, re, sys
path = sys.argv[1]
s = open(path, encoding="utf-8").read()
drop = ["getLangName", "textrender", "tjsDataPack", "tlgSliceLoader", "psbfile"]
for name in drop:
    s, n = re.subn(r"^[ \t]*%s[ \t]*\n" % name, "", s, flags=re.M)
    if n != 1:
        sys.exit("expected one %s line in the plugin list, found %d" % (name, n))
add = ["krkreffekseer"]
start = s.index("LIST(APPEND TVP_PLUGINS_STATIC")
close = re.compile(r"^[ \t]*\)", re.M).search(s, start)
s = s[:close.start()] + "".join("  %s\n" % name for name in add if not re.search(r"^[ \t]*%s[ \t]*$" % name, s[start:close.start()], re.M)) + s[close.start():]
egl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "krkreffekseer-kit.cmake").replace("\\", "/")
line = 'include("%s")\n' % egl
if line not in s:
    s = s.rstrip("\n") + "\n\n" + line
open(path, "w", encoding="utf-8").write(s)
end = re.compile(r"^[ \t]*\)", re.M).search(s, start).end()
print(s[start:end])
