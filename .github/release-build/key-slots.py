#!/usr/bin/env python3
"""Checks that a package's engine has xp3crypt's key slot (the plugin built into the engine) and
that its scnfile plugin has its own: kagex-release writes a game's archive and scenario keys into
them, so without either an encrypted game built with these engines can't be read.
usage: key-slots.py <engine> <scnfile plugin>"""
import sys

# the markers, as kagex-release (Encrypt.cpp, Scenes.cpp) and the plugins keep them: inverted,
# so no file but the plugins holds them plainly
XP3CRYPT = bytes(~b & 0xFF for b in (0xA7, 0xAF, 0xCC, 0xBC, 0xAD, 0xA6, 0xAF, 0xAB, 0xD2, 0xB4, 0xBA, 0xA6, 0xAC, 0xB3, 0xB0, 0xAB))
SCNFILE = bytes(~b & 0xFF for b in (0xB4, 0xAC, 0xBC, 0xB1, 0xD2, 0xB4, 0xBA, 0xA6, 0xD2, 0xAC, 0xB3, 0xB0, 0xAB, 0xD2, 0x89, 0xCE))

engine, scnfile = sys.argv[1], sys.argv[2]
bad = []
for path, marker, what in ((engine, XP3CRYPT, "xp3crypt built into the engine"), (scnfile, SCNFILE, "the scnfile plugin")):
    data = open(path, "rb").read()
    n = data.count(marker)
    print("%s: %d %s key slot(s) (%s)" % (path, n, marker.decode(), what))
    if n != 1:
        bad.append("%s: expected one %s key slot, found %d" % (path, marker.decode(), n))
if bad:
    sys.exit("\n".join(bad))
