// The web build's page additions, loaded by index.html before webconfig.js and krkrz.js
// (.github/platforms/web-static-host.py puts it in the sample's site, kagex-release keeps it in a
// game's). index.html carries the build's id (<meta name=kagex-build>) and loads the scripts with
// it (?v=<id>), and kagex-build.json has the id of what the site serves now.
//
// - Updates: kagex-build.json is read past every cache before the engine starts. A page older
//   than the site is fetched again and reloaded (once). When the build differs from the one the
//   engine's file cache (OPFS, shared by every krkrz game on this origin) was filled for, that
//   cache is emptied, so the game's new files are fetched.
// - Same-origin fetches without ?v= revalidate with the server (cache: no-cache): the game's
//   files, krkrz.wasm and krkrz.data never come from a stale HTTP cache.
// - The engine's file cache (OPFS): a lookup of an entry the prefetch is still writing waits for
//   the write, which the engine would otherwise have read as an empty file.
// - Add to Home Screen: on phones and tablets, outside the home-screen app, a bar offers it: a
//   button where the browser can install the page (beforeinstallprompt: Chrome, Edge, Samsung
//   Internet, Opera), the steps elsewhere (iPhone and iPad browsers: Share, then Add to Home
//   Screen; Firefox and other Android browsers: their menu). Closing it hides it for 30 days.
(function () {
  "use strict";
  var meta = document.querySelector('meta[name="kagex-build"]');
  var build = meta ? meta.getAttribute("content") : "";
  var origFetch = window.fetch;

  // --- fetches revalidate --------------------------------------------------------------------
  if (origFetch) {
    window.fetch = function (input, init) {
      try {
        var raw = typeof input === "string" ? input : input && input.url ? input.url : String(input);
        var url = new URL(raw, location.href);
        var explicit = (init && init.cache) || (typeof Request !== "undefined" && input instanceof Request && input.cache !== "default");
        if (url.origin === location.origin && !/[?&]v=/.test(url.search) && !explicit)
          init = Object.assign({}, init || {}, { cache: "no-cache" });
      } catch (e) {}
      return origFetch.call(this, input, init);
    };
  }

  // --- the file cache: no reading an entry while it's being written --------------------------
  // krkrz.js's prefetch makes each OPFS entry (getFileHandle with create: an empty file) and then
  // writes it, and the engine takes any entry it finds as the file. One it read in between came
  // back empty: a compiled script then loaded as text (the engine opens a script as bytecode,
  // then as text), "Syntax error at line 1", and the page stopped. A lookup of an entry that is
  // being written waits until the write is done; an entry a failed write left is removed.
  (function () {
    var D = typeof FileSystemDirectoryHandle !== "undefined" ? FileSystemDirectoryHandle.prototype : null;
    var F = typeof FileSystemFileHandle !== "undefined" ? FileSystemFileHandle.prototype : null;
    if (!D || !F || !D.getFileHandle || !F.createWritable) return;
    var getFileHandle = D.getFileHandle, createWritable = F.createWritable;
    var writing = new Map();   // entry name -> { done, finish(ok) }
    function begin(dir, name) {
      if (writing.has(name)) return;
      var release;
      var entry = { done: new Promise(function (r) { release = r; }), settled: false };
      entry.finish = function (ok) {
        if (entry.settled) return;
        entry.settled = true;
        clearTimeout(entry.timer);
        if (writing.get(name) === entry) writing.delete(name);
        (ok ? Promise.resolve() : dir.removeEntry(name).catch(function () {})).then(function () { release(); });
      };
      // a create with no write after it doesn't hold the readers up for good
      entry.timer = setTimeout(function () { entry.finish(true); }, 30000);
      writing.set(name, entry);
    }
    D.getFileHandle = function (name, options) {
      var self = this, args = arguments;
      if (options && options.create) begin(self, name);
      else if (writing.has(name))
        return writing.get(name).done.then(function () { return getFileHandle.apply(self, args); });
      return getFileHandle.apply(self, args);
    };
    F.createWritable = function () {
      var name = this.name;
      return createWritable.apply(this, arguments).then(function (w) {
        var entry = writing.get(name);
        if (!entry) return w;
        var close = w.close, abort = w.abort;
        w.close = function () {
          return close.apply(w, arguments).then(function (r) { entry.finish(true); return r; },
                                                 function (e) { entry.finish(false); throw e; });
        };
        w.abort = function () {
          return abort.apply(w, arguments).then(function (r) { entry.finish(false); return r; },
                                                 function (e) { entry.finish(false); throw e; });
        };
        return w;
      }, function (e) {
        var entry = writing.get(name);
        if (entry) entry.finish(false);
        throw e;
      });
    };
  })();

  // --- updates -------------------------------------------------------------------------------
  function dependency(add, id) {
    var f = add ? (Module.addRunDependency || window.addRunDependency) : (Module.removeRunDependency || window.removeRunDependency);
    if (typeof f === "function") f(id);
  }

  async function checkBuild() {
    try {
      var r = await origFetch.call(window, "kagex-build.json", { cache: "no-store" });
      if (r.ok) {
        var latest = (await r.json()).build;
        if (latest && latest !== build) {
          var seen = null;
          try { seen = sessionStorage.getItem("kagex-reloaded"); } catch (e) {}
          if (seen !== latest) {
            try { sessionStorage.setItem("kagex-reloaded", latest); } catch (e) {}
            console.log("kagex: the site has build " + latest + ", this page " + build + ": reloading");
            await origFetch.call(window, location.href, { cache: "reload" });
            location.reload();
            return false;   // the engine doesn't start on the old page
          }
        }
      }
    } catch (e) {
      console.warn("kagex: update check failed", e);
    }
    try {
      var root = await navigator.storage.getDirectory();
      var mark = null;
      try { mark = await (await (await root.getFileHandle(".kagex-build")).getFile()).text(); } catch (e) {}
      if (mark !== build) {
        var names = [];
        for await (var name of root.keys()) if (/^[0-9a-f]{40}_/.test(name)) names.push(name);
        for (var i = 0; i < names.length; i++) {
          try { await root.removeEntry(names[i]); } catch (e) {}
        }
        var w = await (await root.getFileHandle(".kagex-build", { create: true })).createWritable();
        await w.write(build);
        await w.close();
        if (names.length) console.log("kagex: build " + build + ": the engine's file cache was emptied (" + names.length + " files)");
      }
    } catch (e) {
      console.warn("kagex: file cache check failed", e);
    }
    return true;
  }

  if (typeof Module !== "undefined" && build) {
    Module.preRun = Module.preRun ? [].concat(Module.preRun) : [];
    Module.preRun.unshift(function () {
      dependency(true, "kagex-update");
      checkBuild().then(function (go) { if (go) dependency(false, "kagex-update"); });
    });
  }

  // --- Add to Home Screen --------------------------------------------------------------------
  var ua = navigator.userAgent || "";
  var touch = navigator.maxTouchPoints || 0;
  var ios = /iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && touch > 1);
  var android = /Android/i.test(ua);
  var mobile = ios || android || (touch > 1 && window.matchMedia && matchMedia("(pointer: coarse)").matches);
  var installed = navigator.standalone === true || ["fullscreen", "standalone", "minimal-ui"].some(function (m) {
    return window.matchMedia && matchMedia("(display-mode: " + m + ")").matches;
  });
  var KEY = "kagex-home-screen-closed", DAYS = 30;
  var closedAt = 0;
  try { closedAt = +localStorage.getItem(KEY) || 0; } catch (e) {}
  if (!mobile || installed || Date.now() - closedAt < DAYS * 864e5) return;

  var ja = (typeof KRKRZ_LANG !== "undefined" ? KRKRZ_LANG : (navigator.language || "")).toLowerCase().indexOf("ja") === 0;
  var titleMeta = document.querySelector('meta[name="apple-mobile-web-app-title"]');
  var name = (titleMeta && titleMeta.getAttribute("content")) || document.title;
  var shareIcon = '<svg viewBox="0 0 16 20" width="14" height="17" aria-hidden="true" style="vertical-align:-3px">' +
    '<path d="M8 1.5v11M4.5 5 8 1.5 11.5 5" fill="none" stroke="currentColor" stroke-width="1.6"/>' +
    '<path d="M5.5 8H2.5v10.5h11V8h-3" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  var text = {
    prompt: ja ? esc(name) + "をホーム画面に追加すると、全画面で遊べます。" : "Add " + esc(name) + " to your home screen to play full screen.",
    add: ja ? "追加" : "Add",
    ios: ja ? "全画面で遊ぶには、共有ボタン " + shareIcon + " から「ホーム画面に追加」を選んでください。"
            : "To play full screen, tap Share " + shareIcon + ", then Add to Home Screen.",
    menu: ja ? "全画面で遊ぶには、ブラウザのメニュー（⋮）から「ホーム画面に追加」または「インストール」を選んでください。"
             : "To play full screen, open the browser menu (⋮) and choose Add to Home screen or Install.",
    close: ja ? "閉じる" : "Close"
  };

  var bar = null, deferred = null, started = false;
  function show(html, withButton) {
    if (!bar) {
      var style = document.createElement("style");
      style.textContent =
        "#kagex-home{position:fixed;left:50%;top:0;transform:translate(-50%,0);z-index:15;box-sizing:border-box;" +
        "width:min(100%,640px);display:flex;align-items:center;gap:10px;padding:10px 12px;" +
        "padding-top:calc(10px + env(safe-area-inset-top,0px));background:rgba(22,20,40,.94);color:#fff;" +
        "font:14px/1.4 system-ui,-apple-system,sans-serif;border-radius:0 0 12px 12px;" +
        "box-shadow:0 2px 12px rgba(0,0,0,.4);transition:transform .3s}" +
        "#kagex-home.away{transform:translate(-50%,-110%)}" +
        "#kagex-home .msg{flex:1}" +
        "#kagex-home button{font:inherit;border:0;border-radius:8px;cursor:pointer}" +
        "#kagex-home .add{padding:6px 14px;background:#5025ff;color:#fff;font-weight:600}" +
        "#kagex-home .close{padding:4px 8px;background:transparent;color:#bbb;font-size:20px;line-height:1}";
      document.head.appendChild(style);
      bar = document.createElement("div");
      bar.id = "kagex-home";
      bar.setAttribute("role", "dialog");
      ["pointerdown", "pointerup", "touchstart", "touchend", "mousedown", "mouseup", "click"].forEach(function (t) {
        bar.addEventListener(t, function (e) { e.stopPropagation(); });
      });
      document.body.appendChild(bar);
    }
    bar.innerHTML = '<div class="msg">' + html + "</div>" +
      (withButton ? '<button class="add" type="button">' + text.add + "</button>" : "") +
      '<button class="close" type="button" aria-label="' + text.close + '">×</button>';
    bar.className = "";
    bar.querySelector(".close").addEventListener("click", function () {
      try { localStorage.setItem(KEY, String(Date.now())); } catch (e) {}
      hide();
    });
    var add = bar.querySelector(".add");
    if (add) add.addEventListener("click", function () {
      if (!deferred) return;
      deferred.prompt();
      deferred.userChoice.then(function (c) { if (c && c.outcome === "accepted") hide(); });
      deferred = null;
    });
  }
  function hide() { if (bar) bar.className = "away"; }

  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();   // the bar offers it instead of the browser's own mini-infobar
    deferred = e;
    show(text.prompt, true);
  });
  window.addEventListener("appinstalled", hide);

  function start() {
    if (ios) show(text.ios, false);
    // Android: a button if the browser offers the install prompt soon, its menu otherwise
    else setTimeout(function () { if (!deferred) show(text.menu, false); }, 2500);
    // once the game runs, the bar goes after a while (it comes back next time)
    var t = setInterval(function () {
      if (typeof Module === "undefined" || !Module.krkrzLoadingDone || started) return;
      started = true;
      clearInterval(t);
      setTimeout(hide, 10000);
    }, 500);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
