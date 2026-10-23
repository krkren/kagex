#!/usr/bin/env python3
"""Edits krkrz_web's built-in plugin list (CMakeLists.txt) for kagex, in the CI checkout only:
drops the plugins that come from Wamsoft repositories which aren't public (krkrtemplate,
wamsoft_work; kagex uses none of them) and adds krkr_richtext, which kagex draws its text with.
usage: web-plugins.py <krkrz_web/CMakeLists.txt>"""
import re, sys
path = sys.argv[1]
s = open(path, encoding="utf-8").read()
drop = ["getLangName", "textrender", "tjsDataPack", "tlgSliceLoader", "psbfile"]
for name in drop:
    s, n = re.subn(r"^[ \t]*%s[ \t]*\n" % name, "", s, flags=re.M)
    if n != 1:
        sys.exit("expected one %s line in the plugin list, found %d" % (name, n))
s, n = re.subn(r"^([ \t]*)shrinkCopy[ \t]*\n", r"\g<0>\1krkr_richtext\n", s, count=1, flags=re.M)
if n != 1:
    sys.exit("no shrinkCopy line to add krkr_richtext after")
open(path, "w", encoding="utf-8").write(s)
start = s.index("LIST(APPEND TVP_PLUGINS_STATIC")
end = re.compile(r"^[ \t]*\)", re.M).search(s, start).end()
print(s[start:end])
