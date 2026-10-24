#!/usr/bin/env python3
"""Makes kagex-release's iOS engine package (kagex_engine_ios.zip) from krkrz_ios builds: the app
for devices (Release, unsigned) and for the Simulator, without the game.

  ios-engine.py --device <.ipa, or a zip of the .app> --simulator <zip of the .app> <out.zip>
                --version 0.3.0 [--licenses-from <a package with licenses/>]

  engine.json
  license.txt, licenses/
  device/<name>.app        no data/, data.xp3, signature or provisioning profile
  simulator/<name>.app     the same

kagex-release copies one, gives it the game's data, names, version and icon, and signs it: ad
hoc for the Simulator, with the developer's certificate and profile for devices.
"""
import argparse
import json
import stat
import sys
import zipfile


def app_files(path):
    """{path inside the .app: (bytes, mode)} and the .app's name, from an .ipa or a zip"""
    files, name = {}, None
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            parts = i.filename.split("/")
            # Payload/<name>.app/... in an .ipa, <name>.app/... in a zip of the app
            at = next((k for k, p in enumerate(parts) if p.endswith(".app")), None)
            if at is None or i.is_dir():
                continue
            name = parts[at]
            rel = "/".join(parts[at + 1:])
            if not rel:
                continue
            mode = (i.external_attr >> 16) & 0o7777 if i.create_system == 3 else 0o644
            if stat.S_ISLNK(i.external_attr >> 16):
                sys.exit("%s: symbolic links aren't expected in the app (%s)" % (path, i.filename))
            files[rel] = (z.read(i), mode or 0o644)
    if not name:
        sys.exit("%s has no .app" % path)
    return name, files


def keep(rel):
    top = rel.split("/")[0]
    return top not in ("data", "_CodeSignature") and rel not in ("data.xp3", "embedded.mobileprovision") \
        and not rel.split("/")[-1].startswith("._")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", required=True)
    ap.add_argument("--simulator", required=True)
    ap.add_argument("out")
    ap.add_argument("--version", required=True)
    ap.add_argument("--licenses-from")
    a = ap.parse_args()
    out = {}
    for kind, path in (("device", a.device), ("simulator", a.simulator)):
        name, files = app_files(path)
        if "Info.plist" not in files:
            sys.exit("%s: the app has no Info.plist" % path)
        for rel, v in files.items():
            if keep(rel):
                out["%s/%s/%s" % (kind, name, rel)] = v
    if a.licenses_from:
        with zipfile.ZipFile(a.licenses_from) as z:
            for n in z.namelist():
                if (n == "license.txt" or n.startswith("licenses/")) and not n.endswith("/"):
                    out[n] = (z.read(n), 0o644)
    manifest = {"format": 1, "platform": "ios", "version": a.version, "debug": False}
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data, mode in [("engine.json", (json.dumps(manifest, indent=2) + "\n").encode(), 0o644)] + \
                [(n, d, m) for n, (d, m) in sorted(out.items())]:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    print("%s: %d files" % (a.out, len(out) + 1))


if __name__ == "__main__":
    main()
