/* Chooses which data file the page loads and loads it, so the soccer and hockey builds can sit
   side by side. It replaces the old <script src="data.js"> tag.

   Order of choice: ?sport=hockey in the address, then the last choice, then soccer. If the chosen
   build is missing the other one loads and sport_ui.js says so. A soccer build from before the
   split (data.js) still works. */
(function () {
  "use strict";
  const FILES = { soccer: ["data_soccer.js", "data.js"], hockey: ["data_hockey.js"] };
  const KEY = "possnet.sport";
  let want = "soccer";
  try {
    const q = new URLSearchParams(location.search).get("sport");
    if (q && FILES[q]) localStorage.setItem(KEY, q);
    const saved = localStorage.getItem(KEY);
    if (saved && FILES[saved]) want = saved;
  } catch (e) { /* storage unavailable, keep the default */ }
  const asked = new URLSearchParams(location.search).get("sport");
  if (asked && FILES[asked]) want = asked;
  window.POSSNET_WANT = want;

  const other = want === "soccer" ? "hockey" : "soccer";
  const queue = [...FILES[want], ...FILES[other]];
  // Each file is written as its own script so they run in order; a missing file simply leaves
  // window.POSSNET unset and the next one is tried.
  window.__sportNext = function () {
    if (window.POSSNET || !queue.length) return;
    document.write('<script src="' + queue.shift() + '"></' + 'script><script>__sportNext()</' + 'script>');
  };
  window.__sportNext();
})();
