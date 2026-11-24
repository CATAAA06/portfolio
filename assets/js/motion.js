/* Movimento come extra: tutto si spegne con prefers-reduced-motion e senza supporto del browser. */
(function () {
  "use strict";

  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* la foto "diventa" la foto grande (e viceversa) con le View Transitions */
  function transition(fn, from, to) {
    if (reduced || typeof document.startViewTransition !== "function" || !from) { fn(); return; }
    var NAME = "photo";
    from.style.viewTransitionName = NAME;
    var t;
    try {
      t = document.startViewTransition(function () {
        from.style.viewTransitionName = "";
        if (to) to.style.viewTransitionName = NAME;
        fn();
      });
    } catch (err) {
      from.style.viewTransitionName = "";
      fn();
      return;
    }
    var clean = function () { if (to) to.style.viewTransitionName = ""; from.style.viewTransitionName = ""; };
    t.finished.then(clean, clean);
  }

  window.PortfolioMotion = { reduced: reduced, transition: transition };

  /* le foto compaiono mentre scorri; senza JS o senza IntersectionObserver restano sempre visibili */
  if (reduced || typeof IntersectionObserver !== "function") return;
  var shots = document.querySelectorAll(".shot");
  if (!shots.length) return;
  document.documentElement.classList.add("motion");
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (!e.isIntersecting) return;
      e.target.classList.add("is-in");
      io.unobserve(e.target);
    });
  }, { rootMargin: "0px 0px -6% 0px", threshold: 0.05 });
  Array.prototype.forEach.call(shots, function (s, i) {
    s.style.setProperty("--d", (i % 3) * 70 + "ms");
    io.observe(s);
  });
})();
