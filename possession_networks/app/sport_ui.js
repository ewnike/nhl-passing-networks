/* Per sport behavior that does not belong in the shared views.

   Everything sport specific the Networks view needs is read from the payload (meta and
   meta.text), so the wording for each sport lives with its data builder. This file adds the
   sport switch to the header and, for hockey, the rink, jersey labels and the removal of the
   soccer only tabs. It loads after every view and before main.js. */
(function () {
  "use strict";
  const App = window.App, $ = App.$, meta = App.data.meta, TXT = meta.text || {};
  const sport = meta.sport || "soccer";
  const want = window.POSSNET_WANT || sport;

  /* ---------- sport switch ---------- */
  const seg = App.el("div", { class: "seg", id: "sportSeg", role: "group", "aria-label": "Sport" });
  for (const [v, label] of [["soccer", "Soccer"], ["hockey", "Hockey"]]) {
    const b = App.el("button", { "data-v": v, "aria-pressed": String(v === sport), text: label });
    b.style.cssText = "flex:none;overflow:visible;text-overflow:clip;padding:0 12px";
    seg.append(b);
  }
  $(".top").insertBefore(seg, $("#theme"));
  App.seg(seg, (v) => {
    if (v === sport) return;
    App.store.set("sport", v);
    const url = new URL(location.href);
    url.searchParams.set("sport", v);
    location.href = url.toString();
  });
  if (want !== sport) {
    const note = App.el("p", { class: "hint", role: "status",
      text: `No ${want} build found, showing ${sport}. Run scripts/${want === "hockey" ? "11b_build_app_data_hockey" : "11_build_app_data"}.py to create it.` });
    note.style.cssText = "margin:8px 16px 0";
    $("main").prepend(note);
  }
  if (sport !== "hockey") return;

  /* ---------- hockey ---------- */
  document.title = TXT.title || document.title;
  if (meta.credit) $(".foot").firstChild.textContent = meta.credit + " ";
  for (const b of document.querySelectorAll(".tabs button")) b.hidden = b.dataset.view !== "networks";
  // Zones and Evidence need soccer only inputs, so they are inert here.
  const idle = { init() {}, show() {}, draw() {} };
  App.views.zones = idle; App.views.evidence = idle;
  const home = () => { if (location.hash && location.hash !== "#networks") history.replaceState(null, "", "#networks"); };
  home();
  window.addEventListener("hashchange", home);

  // Players are jersey numbers and one goalie per team.
  const baseName = App.shortName;
  App.shortName = (full) => {
    const j = /#(\S+)$/.exec(String(full));
    if (j) return "#" + j[1];
    if (/ goalie$/i.test(String(full))) return "Goalie";
    return baseName(full);
  };

  // Rink in meters from centre ice, NHL markings (200 by 85 feet, 28 foot corners).
  App.drawPitch = (ctx, w, h) => {
    const v = App.pitchView(w, h), { X, Y, s, L, W } = v;
    const ft = 0.3048, R = 28 * ft, line = App.css("--pitch-line");
    const red = (a) => App.rgba("#d05b5b", a), blue = (a) => App.rgba("#4f86d6", a);
    ctx.fillStyle = App.css("--pitch");
    ctx.fillRect(0, 0, w, h);
    const outline = () => {
      ctx.beginPath();
      ctx.moveTo(X(-L / 2 + R), Y(W / 2)); ctx.lineTo(X(L / 2 - R), Y(W / 2));
      ctx.arcTo(X(L / 2), Y(W / 2), X(L / 2), Y(W / 2 - R), R * s);
      ctx.lineTo(X(L / 2), Y(-W / 2 + R));
      ctx.arcTo(X(L / 2), Y(-W / 2), X(L / 2 - R), Y(-W / 2), R * s);
      ctx.lineTo(X(-L / 2 + R), Y(-W / 2));
      ctx.arcTo(X(-L / 2), Y(-W / 2), X(-L / 2), Y(-W / 2 + R), R * s);
      ctx.lineTo(X(-L / 2), Y(W / 2 - R));
      ctx.arcTo(X(-L / 2), Y(W / 2), X(-L / 2 + R), Y(W / 2), R * s);
      ctx.closePath();
    };
    const vline = (x, col, wd) => {
      ctx.strokeStyle = col; ctx.lineWidth = wd;
      ctx.beginPath(); ctx.moveTo(X(x), Y(-W / 2)); ctx.lineTo(X(x), Y(W / 2)); ctx.stroke();
    };
    ctx.save(); outline(); ctx.clip();
    vline(0, red(0.75), 2.2);
    for (const sg of [-1, 1]) { vline(sg * 25 * ft, blue(0.75), 2.2); vline(sg * 89 * ft, red(0.6), 1.2); }
    ctx.restore();
    ctx.strokeStyle = line; ctx.lineWidth = 1.4; outline(); ctx.stroke();
    ctx.lineWidth = 1.1; ctx.strokeStyle = red(0.55); ctx.fillStyle = red(0.55);
    ctx.beginPath(); ctx.arc(X(0), Y(0), 15 * ft * s, 0, Math.PI * 2); ctx.stroke();
    for (const sg of [-1, 1]) {
      for (const sy of [-1, 1]) {
        const cx = sg * 69 * ft, cy = sy * 22 * ft;
        ctx.beginPath(); ctx.arc(X(cx), Y(cy), 15 * ft * s, 0, Math.PI * 2); ctx.stroke();
        ctx.beginPath(); ctx.arc(X(cx), Y(cy), 2.2, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(X(sg * 20 * ft), Y(sy * 22 * ft), 2.2, 0, Math.PI * 2); ctx.fill();
      }
      const gx = sg * 89 * ft, depth = 3.5 * ft;           // goal line, crease opens toward centre ice
      ctx.strokeStyle = blue(0.5); ctx.fillStyle = blue(0.12);
      ctx.beginPath();
      ctx.arc(X(gx), Y(0), 6 * ft * s, sg === 1 ? Math.PI / 2 : -Math.PI / 2, sg === 1 ? 1.5 * Math.PI : Math.PI / 2, false);
      ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.strokeStyle = line; ctx.lineWidth = 1.6;
      ctx.strokeRect(X(sg === 1 ? gx : gx - depth), Y(3 * ft), depth * s, 6 * ft * s);
      ctx.lineWidth = 1.1; ctx.fillStyle = red(0.55);
    }
    ctx.fillStyle = blue(0.8);
    ctx.beginPath(); ctx.arc(X(0), Y(0), 2.4, 0, Math.PI * 2); ctx.fill();
    return v;
  };

  // The release has no positions, so the layout choice has nothing to offer: use average touches.
  const net = App.views.networks, init = net.init;
  net.init = () => {
    init();
    $("#layoutSeg").querySelector('[data-v="actual"]').click();
    $("#layoutSeg").style.display = "none";
    $("#layoutSeg").previousElementSibling.style.display = "none";
    const label = (v, text) => { if (text) $("#modeSeg").querySelector(`[data-v="${v}"]`).textContent = text; };
    label("cum", meta.start_label); label("win", meta.window_label);
    if (TXT.tl_hint) $("#tlHint").textContent = TXT.tl_hint;
    if (TXT.minw_hint) $("#minW").closest(".group").querySelector(".hint").textContent = TXT.minw_hint;
  };
})();
