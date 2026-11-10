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
// - A game file whose name has %, # or ? is fetched by its escaped name (the engine sends it as
//   it is).
// - The engine's file cache (OPFS): a lookup of an entry the prefetch is still writing waits for
//   the write, which the engine would otherwise have read as an empty file.
// - Add to Home Screen: on phones and tablets, outside the home-screen app, a bar offers it: a
//   button where the browser can install the page (beforeinstallprompt: Chrome, Edge, Samsung
//   Internet, Opera), the steps elsewhere (iPhone and iPad browsers: Share, then Add to Home
//   Screen; Firefox and other Android browsers: their menu). Closing it hides it for 30 days.
// - Typing on phones and tablets: a phone's browser opens its keyboard only for a text field the
//   page focuses while it handles a tap, and the game has none, so as a tap ends this asks the
//   game (through the engine's krkrz_repl_eval) whether the tap went down on an [edit] field
//   (KAGTextEntryWebTap in TextEntry.tjs), focuses a hidden field of its own with the text, and
//   hands each change to the game; Enter runs the field's enter=, closing the keyboard keeps the
//   text; a field of several lines types into a hidden textarea, where Enter makes a new line.
//   A game whose framework predates it answers nothing, and nothing happens.
(function () {
  "use strict";
  var meta = document.querySelector('meta[name="kagex-build"]');
  var build = meta ? meta.getAttribute("content") : "";
  var origFetch = window.fetch;

  // --- the game's files with %, # or ? in their names ----------------------------------------
  // The engine (tTVPHttpStorageMedia::ToUrl) and krkrz.js's prefetch put a file's name into its
  // URL as it is, so window@base%base.png asked for "%ba" and # or ? cut the name short
  // (UPSTREAM.md). Their URLs under the web base (KRKRZ_WEB_DEFAULT_WEBBASE, webconfig.js) never
  // carry a query or an escape of their own, so those three are escaped here, on the way out:
  // the file cache's keys, made from the URL before the fetch, stay the engine's.
  function gameFileURL(raw) {
    var base = window.KRKRZ_WEB_DEFAULT_WEBBASE;
    if (typeof base !== "string" || base === "" || !/[%#?]/.test(raw)) return raw;
    var at = raw.indexOf(base);
    if (at < 0) return raw;
    var head = raw.substring(0, at + base.length);
    if (at > 0 && head.indexOf(location.origin) !== 0) return raw;
    return head + raw.substring(at + base.length).replace(/%/g, "%25").replace(/#/g, "%23").replace(/\?/g, "%3F");
  }

  // --- fetches revalidate --------------------------------------------------------------------
  if (origFetch) {
    window.fetch = function (input, init) {
      try {
        if (typeof input === "string") input = gameFileURL(input);
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

  // English, Japanese or Chinese (Traditional for zh-tw, zh-hk, zh-hant...), by KRKRZ_LANG or the browser's
  var langCode = (typeof KRKRZ_LANG !== "undefined" ? KRKRZ_LANG : (navigator.language || "")).toLowerCase();
  var lang = langCode.indexOf("ja") === 0 ? "ja" : langCode.indexOf("zh") !== 0 ? "en" :
    /^zh[-_](tw|hk|mo|hant)/.test(langCode) ? "zh-tw" : "zh-cn";
  var titleMeta = document.querySelector('meta[name="apple-mobile-web-app-title"]');
  var name = (titleMeta && titleMeta.getAttribute("content")) || document.title;
  var shareIcon = '<svg viewBox="0 0 16 20" width="14" height="17" aria-hidden="true" style="vertical-align:-3px">' +
    '<path d="M8 1.5v11M4.5 5 8 1.5 11.5 5" fill="none" stroke="currentColor" stroke-width="1.6"/>' +
    '<path d="M5.5 8H2.5v10.5h11V8h-3" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>';
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  var texts = {
    en: {
      prompt: "Add " + esc(name) + " to your home screen to play full screen.",
      add: "Add",
      ios: "To play full screen, tap Share " + shareIcon + ", then Add to Home Screen.",
      menu: "To play full screen, open the browser menu (⋮) and choose Add to Home screen or Install.",
      close: "Close"
    },
    ja: {
      prompt: esc(name) + "をホーム画面に追加すると、全画面で遊べます。",
      add: "追加",
      ios: "全画面で遊ぶには、共有ボタン " + shareIcon + " から「ホーム画面に追加」を選んでください。",
      menu: "全画面で遊ぶには、ブラウザのメニュー（⋮）から「ホーム画面に追加」または「インストール」を選んでください。",
      close: "閉じる"
    },
    "zh-cn": {
      prompt: "将" + esc(name) + "添加到主屏幕，即可全屏游玩。",
      add: "添加",
      ios: "要全屏游玩，请点按分享按钮 " + shareIcon + "，然后选择“添加到主屏幕”。",
      menu: "要全屏游玩，请打开浏览器菜单（⋮），选择“添加到主屏幕”或“安装”。",
      close: "关闭"
    },
    "zh-tw": {
      prompt: "將" + esc(name) + "加入主畫面，即可全螢幕遊玩。",
      add: "加入",
      ios: "要全螢幕遊玩，請點一下分享按鈕 " + shareIcon + "，然後選擇「加入主畫面」。",
      menu: "要全螢幕遊玩，請開啟瀏覽器選單（⋮），選擇「加到主畫面」或「安裝」。",
      close: "關閉"
    }
  };
  var text = texts[lang];

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

// --- Typing on phones and tablets -------------------------------------------------------------
(function () {
  "use strict";
  var coarse = (navigator.maxTouchPoints || 0) > 0 && !!window.matchMedia && matchMedia("(pointer: coarse)").matches;
  if (!coarse) return;

  // Full screen for the whole page, not the canvas the engine asks for: a browser lets nothing
  // outside the full-screen element take the focus, so the field below couldn't have the
  // keyboard (Android's full screen; iPhones have none). The page's style fits the canvas to
  // the screen either way.
  var canvasProto = window.HTMLCanvasElement && HTMLCanvasElement.prototype, root = document.documentElement;
  if (canvasProto) ["requestFullscreen", "webkitRequestFullscreen"].forEach(function (name) {
    if (typeof root[name] === "function") canvasProto[name] = function () { return root[name].apply(root, arguments); };
  });

  // TJS in the game, through the engine's bridge: its result as text, or null. Only calls that
  // note things: the game does the rest from its own loop
  function tjs(code) {
    if (typeof Module === "undefined" || !Module.krkrzLoadingDone || typeof Module.ccall !== "function") return null;
    try {
      var r = JSON.parse(Module.ccall("krkrz_repl_eval", "string", ["string"], [code]));
      return r && r.ok ? String(r.result).trim() : null;
    } catch (e) { return null; }
  }
  function hex(s) {
    var h = "";
    for (var i = 0; i < s.length; i++) h += ("000" + s.charCodeAt(i).toString(16)).slice(-4);
    return h;
  }
  function unhex(h) {
    var s = "";
    for (var i = 0; i + 4 <= h.length; i += 4) s += String.fromCharCode(parseInt(h.substr(i, 4), 16));
    return s;
  }

  // the hidden field: an <input>, or a <textarea> for a field of several lines ([edit
  // multiline=true]: Enter makes a new line there, and the field ends as it loses the focus)
  var inputs = {}, input = null, typing = false;
  function field(multi) {
    var kind = multi ? "textarea" : "input";
    if (inputs[kind]) return inputs[kind];
    var f = document.createElement(kind);
    if (!multi) f.type = "text";
    f.id = "kagex-text" + (multi ? "-lines" : "");
    f.setAttribute("autocomplete", "off");
    f.setAttribute("autocapitalize", multi ? "sentences" : "words");
    f.setAttribute("enterkeyhint", multi ? "enter" : "done");
    f.setAttribute("aria-hidden", "true");
    // 16px: iPhones zoom the page into a field with smaller text
    f.style.cssText = "position:fixed;left:0;top:0;width:1px;height:1px;opacity:0;border:0;padding:0;" +
      "margin:0;font-size:16px;background:transparent;color:transparent;z-index:-1;resize:none";
    // the keys go to the field, not to the game (SDL listens on the window)
    ["keydown", "keypress", "keyup"].forEach(function (t) {
      f.addEventListener(t, function (e) {
        e.stopPropagation();
        if (t === "keydown" && (e.key === "Enter" || e.keyCode === 13) && (!multi || e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          end(1);
        }
      });
    });
    f.addEventListener("input", function () { if (typing && input === f) tjs('KAGTextEntryWebInput("' + hex(f.value) + '")'); });
    f.addEventListener("blur", function () { if (input === f) end(0); });
    document.body.appendChild(f);
    inputs[kind] = f;
    return f;
  }
  function end(ok) {
    if (!typing) return;
    typing = false;
    tjs('KAGTextEntryWebInput("' + hex(input.value) + '")');
    tjs("KAGTextEntryWebDone(" + ok + ")");
    input.blur();
  }

  // inside the tap, so the browser lets the field have the keyboard
  window.addEventListener("touchend", function (e) {
    if (typing) return;
    var r = tjs("KAGTextEntryWebTap()");
    if (!r) return;
    var m = /^"?(m?)(\d+):([0-9a-f]*)"?$/.exec(r);   // a string comes back as a TJS literal
    if (!m) return;
    // no mouse events made from the tap: their click would focus the canvas (tabindex) and
    // take the keyboard away again (the game has the tap from SDL's touch events already)
    e.preventDefault();
    var f = field(m[1] === "m");
    f.maxLength = +m[2] > 0 ? +m[2] : 524288;
    f.value = unhex(m[3]);
    input = f;
    typing = true;
    f.focus();
    try { f.select(); } catch (e) {}
  }, true);
})();

// --- Back on phones and tablets ---------------------------------------------------------------
// The browser's Back (Android's back button or gesture, an installed web app's) goes to the game
// as Esc while Esc has something to do there, as in the Android app: it closes the history, a
// panel, a prompt or a screen (KAGWebBack in the game's Actions.tjs). With nothing for it (the
// title) the page goes back as it always did. The page keeps one history entry of its own for
// Back to land on, made again at the next touch after each Back the game took: browsers skip an
// entry a page made without the player's touch.
(function () {
  "use strict";
  var coarse = (navigator.maxTouchPoints || 0) > 0 && !!window.matchMedia && matchMedia("(pointer: coarse)").matches;
  if (!coarse || !window.history || typeof history.pushState !== "function") return;
  var armed = false, leaving = false;
  function ready() { return typeof Module !== "undefined" && Module.krkrzLoadingDone && typeof Module.ccall === "function"; }
  function arm() {
    if (armed || leaving || !ready()) return;
    armed = true;
    history.pushState({ kagexBack: 1 }, "");
  }
  ["pointerdown", "touchstart"].forEach(function (t) { window.addEventListener(t, arm, true); });
  window.addEventListener("popstate", function () {
    if (!armed) return;
    armed = false;
    var took = false;
    try {
      var r = JSON.parse(Module.ccall("krkrz_repl_eval", "string", ["string"], ["KAGWebBack()"]));
      took = !!(r && r.ok && /^"?1"?$/.test(String(r.result).trim()));
    } catch (e) { took = false; }
    if (!took) { leaving = true; history.back(); }
  });
})();
