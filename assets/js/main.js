(function () {
  "use strict";

  /* header: sfondo dopo lo scroll */
  var bar = document.querySelector(".bar");
  function onScroll() { bar.classList.toggle("on", window.scrollY > 24); }
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  /* menu mobile (Popover API): si chiude quando scegli una voce */
  var menu = document.getElementById("menu");
  if (menu) {
    menu.addEventListener("click", function (e) {
      if (e.target.closest("a") && typeof menu.hidePopover === "function") menu.hidePopover();
    });
  }

  /* galleria: elementi, filtri, disposizione in colonne nell'ordine di lettura */
  var wall = document.getElementById("wall");
  var status = document.getElementById("status");
  var shots = Array.prototype.slice.call(document.querySelectorAll(".shot"));
  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip"));
  var ROW = 8; /* px: deve coincidere con grid-auto-rows in style.css */

  function visible() { return shots.filter(function (s) { return !s.hidden; }); }

  /* ogni foto va nella colonna piu bassa: l'ordine visivo resta quello del DOM (Tab incluso) */
  function layout() {
    if (!wall || !wall.classList.contains("is-grid")) return;
    var cs = window.getComputedStyle(wall);
    var cols = cs.gridTemplateColumns.split(" ").length;
    var gap = parseFloat(cs.columnGap) || 0;
    var colW = (wall.clientWidth - gap * (cols - 1)) / cols;
    var rows = [], i;
    for (i = 0; i < cols; i++) rows.push(0);
    visible().forEach(function (s) {
      var img = s.querySelector("img");
      var h = colW * (img.getAttribute("height") / img.getAttribute("width"));
      var span = Math.ceil((h + gap) / ROW);
      var c = 0;
      for (i = 1; i < cols; i++) if (rows[i] < rows[c]) c = i;
      s.style.gridColumn = String(c + 1);
      s.style.gridRow = (rows[c] + 1) + " / span " + span;
      rows[c] += span;
    });
  }

  if (wall) {
    wall.classList.add("is-grid");
    layout();
    if (typeof ResizeObserver === "function") {
      var raf = 0, lastW = wall.clientWidth;
      new ResizeObserver(function () {
        if (wall.clientWidth === lastW) return;
        lastW = wall.clientWidth;
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(layout);
      }).observe(wall);
    } else {
      window.addEventListener("resize", layout);
    }
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var f = chip.getAttribute("data-f");
      chips.forEach(function (c) { c.setAttribute("aria-pressed", c === chip ? "true" : "false"); });
      shots.forEach(function (s) { s.hidden = !(f === "all" || s.getAttribute("data-cat") === f); });
      layout();
      var n = visible().length;
      if (status) status.textContent = n + (n === 1 ? " foto mostrata" : " foto mostrate");
    });
  });

  /* lightbox */
  var dlg = document.getElementById("lb");
  if (!dlg || typeof dlg.showModal !== "function") return; /* senza <dialog> le foto si aprono come link */
  var img = document.getElementById("lbImg");
  var srcEl = document.getElementById("lbSrc");
  var count = document.getElementById("lbCount");
  var num = document.getElementById("lbNum");
  var title = document.getElementById("lbTitle");
  var text = document.getElementById("lbText");
  var exif = document.getElementById("lbExif");
  var stage = document.getElementById("lbStage");
  var list = [], idx = 0, opener = null;
  var motion = window.PortfolioMotion || null;

  /* AVIF supportato? (serve solo per precaricare il formato giusto) */
  var avif = false;
  (function () {
    var t = new Image();
    t.onload = function () { avif = t.width > 0; };
    t.src = "data:image/avif;base64,AAAAIGZ0eXBhdmlmAAAAAGF2aWZtaWYxbWlhZk1BMUIAAADrbWV0YQAAAAAAAAAhaGRscgAAAAAAAAAAcGljdAAAAAAAAAAAAAAAAAAAAAAOcGl0bQAAAAAAAQAAAB5pbG9jAAAAAEQAAAEAAQAAAAEAAAETAAAAJwAAAChpaW5mAAAAAAABAAAAGmluZmUCAAAAAAEAAGF2MDFDb2xvcgAAAABqaXBycAAAAEtpcGNvAAAAFGlzcGUAAAAAAAAAAgAAAAIAAAAQcGl4aQAAAAADCAgIAAAADGF2MUOBAAwAAAAAE2NvbHJuY2x4AAEADQAGgAAAABdpcG1hAAAAAAAAAAEAAQQBAoMEAAAAL21kYXQSAAoIGAA2iAhoNCAyGRlHh4Yhh5555oAAAJBAyRxhSgnBjgTNEYw=";
  })();

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function fullOf(s) { return avif && s.getAttribute("data-avif") ? s.getAttribute("data-avif") : s.getAttribute("href"); }
  function preload(i) { var n = new Image(); n.src = fullOf(list[(i + list.length) % list.length]); }

  function show(i) {
    idx = (i + list.length) % list.length;
    var s = list[idx];
    opener = s;
    var thumb = s.querySelector("img");
    /* subito la miniatura (gia in cache), poi la foto grande appena e pronta: nessun vuoto */
    srcEl.removeAttribute("srcset");
    img.src = thumb.currentSrc || thumb.src;
    var big = new Image();
    big.onload = function () {
      if (list[idx] !== s) return;
      srcEl.srcset = s.getAttribute("data-avif") || "";
      img.src = s.getAttribute("href");
    };
    big.src = fullOf(s);
    img.alt = thumb.alt;
    num.textContent = s.getAttribute("data-n");
    title.textContent = s.getAttribute("data-title");
    text.textContent = s.getAttribute("data-cap");
    exif.textContent = s.getAttribute("data-exif") || "";
    count.textContent = pad(idx + 1) + " / " + pad(list.length);
    preload(idx + 1);
    preload(idx - 1);
  }

  function run(fn, from, to) {
    if (motion && motion.transition) motion.transition(fn, from, to); else fn();
  }

  function openLb(s) {
    list = visible(); opener = s;
    var thumb = s.querySelector("img");
    run(function () { show(list.indexOf(s)); dlg.showModal(); }, thumb, img);
  }

  function closeLb() {
    if (!dlg.open) return;
    var thumb = list[idx] && !list[idx].hidden ? list[idx].querySelector("img") : null;
    run(function () { dlg.close(); }, img, thumb);
  }

  shots.forEach(function (s) {
    s.addEventListener("click", function (e) { e.preventDefault(); openLb(s); });
  });

  document.getElementById("lbClose").addEventListener("click", closeLb);
  document.getElementById("lbPrev").addEventListener("click", function () { show(idx - 1); });
  document.getElementById("lbNext").addEventListener("click", function () { show(idx + 1); });
  dlg.addEventListener("click", function (e) { if (e.target === dlg) closeLb(); });
  dlg.addEventListener("cancel", function (e) { e.preventDefault(); closeLb(); });
  dlg.addEventListener("close", function () { if (opener) opener.focus({ preventScroll: false }); });
  dlg.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight") show(idx + 1);
    else if (e.key === "ArrowLeft") show(idx - 1);
  });

  /* swipe */
  var x0 = null;
  stage.addEventListener("pointerdown", function (e) { x0 = e.clientX; });
  stage.addEventListener("pointerup", function (e) {
    if (x0 === null) return;
    var dx = e.clientX - x0; x0 = null;
    if (Math.abs(dx) > 50) show(idx + (dx < 0 ? 1 : -1));
  });
  stage.addEventListener("pointercancel", function () { x0 = null; });
})();
