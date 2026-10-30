/* Router, theme toggle and start up. */
(function () {
  "use strict";
  const App = window.App, $ = App.$;
  const names = ["networks", "zones", "evidence"];
  $("#season").textContent = App.data.meta.season + "  |  " + App.data.meta.source;
  $("#buildInfo").textContent = App.data.matches.length + " " + (App.data.meta.unit || "matches");

  function show(name) {
    if (!names.includes(name)) name = "networks";
    App.current = name;
    for (const n of names) $("#view-" + n).hidden = n !== name;
    for (const b of document.querySelectorAll(".tabs button")) b.setAttribute("aria-selected", String(b.dataset.view === name));
    requestAnimationFrame(() => App.views[name].show());
  }
  for (const b of document.querySelectorAll(".tabs button")) {
    b.addEventListener("click", () => { location.hash = b.dataset.view; });
  }
  window.addEventListener("hashchange", () => show(location.hash.slice(1)));
  window.addEventListener("resize", () => App.redraw());

  const root = document.documentElement;
  const saved = App.store.get("theme", "");
  if (saved) root.setAttribute("data-theme", saved);
  $("#theme").addEventListener("click", () => {
    const dark = root.getAttribute("data-theme") === "dark" ||
      (!root.hasAttribute("data-theme") && matchMedia("(prefers-color-scheme: dark)").matches);
    const next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next); App.store.set("theme", next); App.redraw();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => App.redraw());

  for (const n of names) App.views[n].init();
  show(location.hash.slice(1) || "networks");
})();
