#!/usr/bin/env python3
# 生成物 (stage_web.py): 案件 web サイトの実行用サーバ。
# site/ 一式 (index.html / krkrz.* / webconfig.js / resource/ / gamedata/) を
# COOP/COEP 付きで配信する。gamedata/krkrz_files.json は生成マニフェストを返す。
# <video> ストリーミング (VideoOverlay) 用に HTTP Range (単一レンジ) と
# マルチスレッド配信に対応。
# サイトは自己完結 (絶対パス参照なし) — このフォルダごとコピーすれば動く。
import os, re, sys, posixpath
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(SITE_DIR, "gamedata.krkrz_files.json")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8100

def ci_resolve(path):
    """path が存在しなければ、各パス成分を大文字小文字無視で実在名に置換して返す。
    web:// の URL はマニフェスト由来で小文字なので、case-sensitive な FS (Linux 等)
    でも実ファイル名を変えずに解決できるようにする (見つからなければ通常の 404)。"""
    if os.path.exists(path):
        return path
    drive, rest = os.path.splitdrive(path)
    parts = [p for p in rest.replace('\\', '/').split('/') if p]
    cur = (drive + os.sep) if drive else os.sep
    if not os.path.isabs(path):
        cur = '.'
    for comp in parts:
        nxt = os.path.join(cur, comp)
        if not os.path.exists(nxt):
            low = comp.lower()
            try:
                match = next((e for e in os.listdir(cur) if e.lower() == low), None)
            except OSError:
                return path
            if match is None:
                return path
            nxt = os.path.join(cur, match)
        cur = nxt
    return cur

class H(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                       '.wasm': 'application/wasm', '.mjs': 'text/javascript',
                       '.js': 'text/javascript'}
    def __init__(self, *a, **k):
        super().__init__(*a, directory=SITE_DIR, **k)
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()
    def translate_path(self, path):
        p = posixpath.normpath(unquote(path.split('?', 1)[0].split('#', 1)[0]))
        if p == '/gamedata/krkrz_files.json':
            return MANIFEST   # マニフェストは配信データを汚さず site 直下から返す
        return ci_resolve(super().translate_path(path))
    def do_GET(self):
        rh = self.headers.get('Range')
        path = self.translate_path(self.path)
        if rh and os.path.isfile(path):
            self.send_range(path, rh)
        else:
            super().do_GET()
    def send_range(self, path, rh):
        size = os.path.getsize(path)
        m = re.match(r'bytes=(\d*)-(\d*)$', rh.strip())
        if not m or (not m.group(1) and not m.group(2)):
            self.send_error(416)
            return
        if m.group(1):
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else size - 1
        else:  # suffix 形式 bytes=-N (末尾 N バイト)
            start = max(0, size - int(m.group(2)))
            end = size - 1
        end = min(end, size - 1)
        if start >= size or start > end:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        try:
            with open(path, 'rb') as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # ブラウザ側の中断 (シーク等) は正常系

print(f"serving {SITE_DIR}\n  http://localhost:{PORT}/")
ThreadingHTTPServer(('localhost', PORT), H).serve_forever()
