(function () {
  "use strict";

  /* header: sfondo dopo lo scroll */
  var bar = document.querySelector(".bar");
  function onScroll() { bar.classList.toggle("on", window.scrollY > 24); }
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  /* filtri galleria */
  var shots = Array.prototype.slice.call(document.querySelectorAll(".shot"));
  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip"));
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var f = chip.getAttribute("data-f");
      chips.forEach(function (c) { c.setAttribute("aria-pressed", c === chip ? "true" : "false"); });
      shots.forEach(function (s) { s.hidden = !(f === "all" || s.getAttribute("data-cat") === f); });
    });
  });

  /* lightbox */
  var dlg = document.getElementById("lb");
  if (!dlg || typeof dlg.showModal !== "function") return; /* senza <dialog> le foto si aprono come link */
  var img = document.getElementById("lbImg");
  var count = document.getElementById("lbCount");
  var num = document.getElementById("lbNum");
  var title = document.getElementById("lbTitle");
  var text = document.getElementById("lbText");
  var stage = document.getElementById("lbStage");
  var list = [], idx = 0, opener = null;

  function visible() { return shots.filter(function (s) { return !s.hidden; }); }
  function pad(n) { return (n < 10 ? "0" : "") + n; }

  function show(i) {
    idx = (i + list.length) % list.length;
    var s = list[idx];
    img.src = s.getAttribute("href");
    img.alt = s.querySelector("img").alt;
    num.textContent = s.getAttribute("data-n");
    title.textContent = s.getAttribute("data-title");
    text.textContent = s.getAttribute("data-cap");
    count.textContent = pad(idx + 1) + " / " + pad(list.length);
    var nxt = new Image(); nxt.src = list[(idx + 1) % list.length].getAttribute("href");
  }

  shots.forEach(function (s) {
    s.addEventListener("click", function (e) {
      e.preventDefault();
      opener = s; list = visible(); idx = list.indexOf(s);
      show(idx); dlg.showModal();
    });
  });

  document.getElementById("lbClose").addEventListener("click", function () { dlg.close(); });
  document.getElementById("lbPrev").addEventListener("click", function () { show(idx - 1); });
  document.getElementById("lbNext").addEventListener("click", function () { show(idx + 1); });
  dlg.addEventListener("click", function (e) { if (e.target === dlg) dlg.close(); });
  dlg.addEventListener("close", function () { if (opener) opener.focus(); });
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
