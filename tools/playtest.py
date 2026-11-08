#!/usr/bin/env python3
"""Plays a game's routes on its own and reports what went wrong (since 0.26.0).

Each route is a run of the game here (headless on Linux with SDL's offscreen driver), driven
through the engine's REPL file channel as tools/smoketest.py drives it, with a save folder and a
log of its own. The game plays from a script (and label) by itself through the framework's route
runner (KAGPlaytest, template/system/DebugTools.tjs): it skips (read and unread text alike),
clicks on at every wait, takes the given choice at each menu (the first beyond the list) and
stops when it gets to --until, or reports "stuck" when nothing has moved for --stuck seconds.
A script error (the log's "Script exception raised" and its trace) or a native dialog the
engine opens fails the route, with where it happened.

  python3 tools/playtest.py --start char.ks --until s0001.ks
  python3 tools/playtest.py --start s0001.ks --until s0001.ks --choices 1,0
  python3 tools/playtest.py --start char.ks --until s0001.ks --all --jobs 2

--all plays every route: the first with no choices given, then for each choice a route took, one
route for each other option there, and so on (--max-routes stops it). --jobs runs that many games
at once (each with -instance=<n>, its own single-instance lock). The exit code is the number of
routes that failed (0: every one got to --until).

The engine is the one next to data/ (./krkrz, ./krkrz.exe) unless --engine names another; the
game is data/ unless --data names another project folder.
"""
import argparse, os, queue, shutil, subprocess, sys, tempfile, threading, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smoketest  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# a script error: the engine's own (an exception no script caught) and KAG's (Conductor.tjs: the
# script, line and tag where a tag's handler threw)
ERRORS = ("Script exception raised", "スクリプトで例外が発生しました", "A fatal error has occurred")


class PlayEngine(smoketest.FileChannel):
    """smoketest's DesktopEngine with arguments of its own (-instance=)"""

    def __init__(self, exe, data, workdir, extra):
        self.workdir = workdir
        self.chan = os.path.join(workdir, "repl")
        self.savedir = os.path.join(workdir, "savedata")
        os.makedirs(self.chan)
        os.makedirs(self.savedir, exist_ok=True)
        self.log_path = os.path.join(workdir, "engine.log")
        self.verbose = False
        self.modals = []
        env = dict(os.environ)
        env.setdefault("SDL_VIDEO_DRIVER", "offscreen")
        env.setdefault("SDL_AUDIO_DRIVER", "dummy")
        args = [exe, os.path.abspath(data), "-datapath=" + self.savedir + "/", "-replfile=" + self.chan,
                "-replmodaltimeout=0"] + extra
        self.log = open(self.log_path, "wb")
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT, env=env)

    alive = smoketest.DesktopEngine.alive
    output = smoketest.DesktopEngine.output
    stop = smoketest.DesktopEngine.stop


def first_error(text):
    """The first script error in a log and the lines after it (its trace), or None"""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if any(e in line for e in ERRORS):
            start = i - 1 if i > 0 and "trace :" in lines[i - 1] else i
            return "\n".join(l.rstrip() for l in lines[start:i + 5])
    return None


def tjs_list(values):
    return "[" + ", ".join(str(int(v)) for v in values) + "]"


def play(args, choices, number, out):
    """One route: %(status, where, taken: [(picked, options)], ms, message, error, log)"""
    work = os.path.join(out, "route-%03d" % number)
    if os.path.exists(work):
        shutil.rmtree(work)
    os.makedirs(work)
    eng = PlayEngine(args.engine, args.data, work, ["-instance=playtest%d" % number] + (["-allseen=yes"] if args.allseen else []))
    r = {"choices": choices, "status": "failed", "where": "", "taken": [], "ms": 0, "message": "", "error": None, "log": work}
    try:
        eng.wait("the REPL", "1", timeout=90)
        # the game started (its first script on, nothing in the way)
        eng.wait("the game", 'typeof global.kag == "Object" && kag.inStable && kag.conductor.curStorage != "" && '
                 'kag.conductor.curStorage != "first.ks" && typeof global.KAGPlaytest == "Object"', timeout=120)
        spec = "%%[ storage:\"%s\", label:\"%s\", choices:%s, skip:%s, until:\"%s\", stuck:%d, timeout:%d ]" % (
            args.start, args.label, tjs_list(choices), "true" if args.skip else "false", args.until,
            args.stuck * 1000, args.timeout * 1000)
        eng.tjs("KAGPlaytest.start(%s); return 1;" % spec)
        end = time.time() + args.timeout + 30
        while time.time() < end:
            err = first_error(eng.output())
            if err:
                r["status"], r["error"] = "error", err
                break
            if eng.modals:
                r["status"], r["error"] = "error", "a native dialog: " + eng.modals[0].strip()
                break
            rep = str(eng.tjs("return KAGPlaytest.report();", timeout=60))
            status = rep.split("|", 1)[0]
            if status != "running":
                break
            time.sleep(0.5)
        try:
            rep = str(eng.tjs("return KAGPlaytest.report();", timeout=20))
            p = rep.split("|")
            if r["status"] != "error":
                r["status"] = p[0]
            r["where"], r["ms"], r["message"] = p[1], int(p[3]), "|".join(p[4:])
            r["taken"] = [tuple(int(n) for n in t.split("/")) for t in p[2].split(",") if t]
        except Exception as e:  # an error dialog may hold the game
            r["message"] = r["message"] or str(e)
    except smoketest.SmokeError as e:
        r["status"], r["message"] = "failed", str(e)
        r["error"] = r["error"] or first_error(eng.output())
    finally:
        eng.stop()
    return r


def describe(r):
    taken = ",".join("%d/%d" % t for t in r["taken"]) or "none"
    s = "%-7s choices %-12s %6.1f s  at %s" % (r["status"], taken, r["ms"] / 1000.0, r["where"])
    if r["message"]:
        s += "\n         " + r["message"]
    if r["error"]:
        s += "\n         " + r["error"].replace("\n", "\n         ")
    if r["status"] != "done":
        s += "\n         log: " + os.path.join(r["log"], "engine.log")
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", help="the engine (default: krkrz or krkrz.exe next to data/)")
    ap.add_argument("--data", default=os.path.join(ROOT, "data"), help="the game's project folder (data/)")
    ap.add_argument("--start", default="first.ks", help="the script each route plays from")
    ap.add_argument("--label", default="", help="its label (*name), or its top")
    ap.add_argument("--until", default="title.ks", help="a route is done at this script, once it has left the first")
    ap.add_argument("--choices", default="", help="the choices to take, by number from 0, separated by commas")
    ap.add_argument("--all", action="store_true", help="every route, branch by branch")
    ap.add_argument("--max-routes", type=int, default=64, help="--all stops after this many")
    ap.add_argument("--jobs", type=int, default=1, help="games at once")
    ap.add_argument("--stuck", type=int, default=20, help="seconds without moving that make a route stuck")
    ap.add_argument("--timeout", type=int, default=600, help="seconds a route may take")
    ap.add_argument("--no-skip", dest="skip", action="store_false", help="click through instead of skipping")
    ap.add_argument("--allseen", action="store_true", help="run with -allseen=yes")
    ap.add_argument("--out", help="the routes' save folders and logs (default: a new temporary folder)")
    args = ap.parse_args()
    if not args.engine:
        for name in ("krkrz", "krkrz.exe"):
            p = os.path.join(os.path.dirname(os.path.abspath(args.data)), name)
            if os.path.exists(p):
                args.engine = p
                break
    if not args.engine or not os.path.exists(args.engine):
        sys.exit("no engine: give --engine")
    out = args.out or tempfile.mkdtemp(prefix="playtest-")
    os.makedirs(out, exist_ok=True)
    print("playtest: %s from %s%s to %s, routes in %s" % (args.data, args.start, " " + args.label if args.label else "",
                                                         args.until, out), flush=True)

    first = [int(c) for c in args.choices.split(",") if c.strip() != ""]
    todo = queue.Queue()
    todo.put(first)
    results, lock, counter = [], threading.Lock(), [0]
    pending = [1]

    def worker():
        while True:
            try:
                choices = todo.get(timeout=1)
            except queue.Empty:
                with lock:
                    if pending[0] == 0:
                        return
                continue
            with lock:
                counter[0] += 1
                number = counter[0]
            r = play(args, choices, number, out)
            with lock:
                results.append(r)
                print("route %d: %s" % (number, describe(r)), flush=True)
                if args.all:
                    # the other options of each choice this route made past those it was given
                    for i in range(len(choices), len(r["taken"])):
                        picked, options = r["taken"][i]
                        for alt in range(1, options):
                            if counter[0] + todo.qsize() + pending[0] - 1 >= args.max_routes:
                                break
                            todo.put([t[0] for t in r["taken"][:i]] + [alt])
                            pending[0] += 1
                pending[0] -= 1

    threads = [threading.Thread(target=worker) for _ in range(max(1, args.jobs))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    failed = [r for r in results if r["status"] != "done"]
    print("playtest: %d routes, %d done, %d failed" % (len(results), len(results) - len(failed), len(failed)), flush=True)
    sys.exit(min(len(failed), 100))


if __name__ == "__main__":
    main()
