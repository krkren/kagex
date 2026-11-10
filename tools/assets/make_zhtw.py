#!/usr/bin/env python3
"""Makes the sample's Traditional Chinese (zh-tw) from its Simplified Chinese (zh-cn).

Every text file in data/lang/zh-cn/ (scenario translations, lang.json, the manual's pages,
credits, terms, subtitles) and template/system/*_zh-cn.* (the framework's strings and manual)
is converted with OpenCC's s2twp (Simplified to Traditional with Taiwan's phrases), then with
the terms below that OpenCC leaves in their mainland form for software (全屏, 視頻, 菜單...),
and written as the same file under zh-tw. A JSON table's values are converted, not its keys
(English), and its "name" is 繁體中文. A file keeps its BOM, or its lack of one. Images aren't
touched: make_ui.py --lang zh-tw draws them.

Needs OpenCC in Python: pip install opencc-python-reimplemented (no native library).

  python3 tools/assets/make_zhtw.py          # from the repository's root, or give its path
"""
import argparse
import glob
import json
import os
import sys

# after s2twp: the words a Taiwanese player expects in a game's menus
FIX = [("簡體中文", "繁體中文"), ("全屏", "全螢幕"), ("快進", "快轉"), ("預設設定", "預設值"), ("質量", "品質"),
       ("歷史記錄", "歷史紀錄"), ("手柄", "控制器"), ("幫助", "說明"), ("屏幕", "螢幕"), ("視頻", "影片"),
       ("文本", "文字"), ("鼠標", "滑鼠"), ("菜單", "選單"), ("默認", "預設"), ("字體", "字型"), ("軟件", "軟體"),
       ("程序", "程式"), ("鏈接", "連結"), ("網絡", "網路"), ("音頻", "音訊"), ("數據", "資料"), ("存檔位", "存檔欄位")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repo", nargs="?", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."),
                    help="the repository's root (default: this script's)")
    args = ap.parse_args()
    try:
        from opencc import OpenCC
    except ImportError:
        sys.exit("needs OpenCC: pip install opencc-python-reimplemented")
    cc = OpenCC("s2twp")

    def conv(text):
        text = cc.convert(text)
        for a, b in FIX:
            text = text.replace(a, b)
        return text

    repo = os.path.abspath(args.repo)
    pairs = []
    for p in sorted(glob.glob(os.path.join(repo, "data/lang/zh-cn/**/*"), recursive=True)):
        if os.path.isfile(p) and not p.endswith(".png"):
            pairs.append((p, p.replace("/zh-cn/", "/zh-tw/")))
    for p in sorted(glob.glob(os.path.join(repo, "template/system/*_zh-cn.*"))):
        pairs.append((p, p.replace("_zh-cn.", "_zh-tw.")))
    for src, dst in pairs:
        raw = open(src, "rb").read()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        if src.endswith(".json"):
            table = json.loads(text)
            table["name"] = "繁體中文"
            table["strings"] = {k: conv(v) for k, v in table["strings"].items()}
            out = json.dumps(table, ensure_ascii=False, indent=2) + ("\n" if text.endswith("\n") else "")
        else:
            out = conv(text)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write((b"\xef\xbb\xbf" if bom else b"") + out.encode("utf-8"))
        print(os.path.relpath(dst, repo))


if __name__ == "__main__":
    main()
