/* Glossary: term buttons with a tooltip (hover or keyboard focus) and a drawer that holds every
   definition. A term button can sit in any text. Selecting it opens the drawer at that entry. */
(function () {
  "use strict";
  const App = window.App, T = window.EvidenceText, $ = App.$;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  App.esc = esc;

  /* A term button for the given glossary key. Unknown keys fall back to plain text. */
  App.term = (key, label, cls = "") => T.GLOSSARY[key]
    ? `<button type="button" class="term ${cls}" data-term="${key}" aria-haspopup="dialog">${esc(label)}</button>`
    : esc(label);

  /* Escape a string, then turn {{key|label}} tokens into term buttons. */
  App.rich = (s) => esc(s).replace(/\{\{([a-z0-9]+)\|([^}]+)\}\}/g, (_, k, label) => App.term(k, label));

  /* ---------- tooltip ---------- */
  const tip = App.el("div", { id: "termTip", class: "termtip", role: "tooltip", hidden: "" });
  document.body.append(tip);
  let current = null;

  function place(btn) {
    const r = btn.getBoundingClientRect();
    tip.style.left = "0px"; tip.style.top = "0px";
    const w = tip.offsetWidth, h = tip.offsetHeight;
    const x = Math.max(8, Math.min(window.innerWidth - w - 8, r.left + r.width / 2 - w / 2));
    let y = r.bottom + 8;
    if (y + h > window.innerHeight - 8) y = r.top - h - 8;
    tip.style.left = x + "px"; tip.style.top = Math.max(8, y) + "px";
  }
  function show(btn) {
    const g = T.GLOSSARY[btn.dataset.term];
    if (!g) return;
    if (current && current !== btn) current.removeAttribute("aria-describedby");
    current = btn;
    tip.innerHTML = `<b>${esc(g.name)}</b>${esc(g.short)}<span class="more">Select for the full entry</span>`;
    tip.hidden = false;
    btn.setAttribute("aria-describedby", "termTip");
    place(btn);
  }
  function hide() {
    if (current) current.removeAttribute("aria-describedby");
    current = null; tip.hidden = true;
  }
  const termOf = (ev) => (ev.target.closest ? ev.target.closest(".term") : null);
  document.addEventListener("mouseover", (ev) => { const b = termOf(ev); if (b) show(b); });
  document.addEventListener("mouseout", (ev) => { if (termOf(ev) && document.activeElement !== termOf(ev)) hide(); });
  document.addEventListener("focusin", (ev) => { const b = termOf(ev); if (b) show(b); });
  document.addEventListener("focusout", (ev) => { if (termOf(ev)) hide(); });
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !tip.hidden) hide(); });
  /* Focusing a term can scroll it into view, so follow it instead of hiding the tooltip. */
  window.addEventListener("scroll", () => {
    if (!current) return;
    const r = current.getBoundingClientRect();
    if (r.bottom < 0 || r.top > window.innerHeight) hide(); else place(current);
  }, true);
  window.addEventListener("resize", hide);

  /* ---------- drawer ---------- */
  const dlg = $("#glossary"), list = $("#glossaryList");
  list.innerHTML = T.GLOSSARY_ORDER.map((k) => {
    const g = T.GLOSSARY[k];
    return `<div class="gl" id="g-${k}"><dt tabindex="-1">${esc(g.name)}</dt><dd><p class="short">${esc(g.short)}</p><p>${esc(g.long)}</p></dd></div>`;
  }).join("");

  function open(key) {
    hide();
    if (typeof dlg.showModal === "function") { if (!dlg.open) dlg.showModal(); } else dlg.setAttribute("open", "");
    for (const el of list.querySelectorAll(".gl.hit")) el.classList.remove("hit");
    const target = key ? $("#g-" + key, list) : null;
    if (target) {
      target.classList.add("hit");
      target.scrollIntoView({ block: "start" });
      target.querySelector("dt").focus({ preventScroll: true });
    } else {
      $("#glossaryClose").focus();
    }
  }
  App.openGlossary = open;
  document.addEventListener("click", (ev) => { const b = termOf(ev); if (b) open(b.dataset.term); });
  $("#openGlossary").addEventListener("click", () => open());
  $("#glossaryClose").addEventListener("click", () => (dlg.close ? dlg.close() : dlg.removeAttribute("open")));
  dlg.addEventListener("click", (ev) => { if (ev.target === dlg) dlg.close(); });
})();
