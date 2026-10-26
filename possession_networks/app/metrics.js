/* Network measures for small weighted directed graphs, ported from the Python pipeline
 * (src/possnet/network/metrics.py, which uses networkx). tests/test_app_metrics.py checks
 * this file against networkx on random graphs.
 *
 * A graph is a square matrix W where W[i][j] is the number of completed passes i -> j.
 */
(function (root) {
  "use strict";

  function sum(a) { let s = 0; for (const v of a) s += v; return s; }

  function pagerank(W, alpha = 0.85, tol = 1e-12, maxIter = 1000) {
    const n = W.length;
    if (n === 0) return [];
    const out = W.map(sum);
    let x = new Array(n).fill(1 / n);
    for (let it = 0; it < maxIter; it++) {
      let dangling = 0;
      for (let i = 0; i < n; i++) if (out[i] === 0) dangling += x[i];
      const next = new Array(n).fill((alpha * dangling + (1 - alpha)) / n);
      for (let i = 0; i < n; i++) {
        if (out[i] === 0) continue;
        const share = alpha * x[i] / out[i];
        for (let j = 0; j < n; j++) if (W[i][j] > 0) next[j] += share * W[i][j];
      }
      let err = 0;
      for (let i = 0; i < n; i++) err += Math.abs(next[i] - x[i]);
      x = next;
      if (err < tol) break;
    }
    const s = sum(x);
    return x.map((v) => v / s);
  }

  /* Hubs and authorities by power iteration, each normalized to sum to one. */
  function hits(W, tol = 1e-12, maxIter = 2000) {
    const n = W.length;
    if (n === 0) return { hub: [], auth: [] };
    let h = new Array(n).fill(1 / n);
    let a = new Array(n).fill(0);
    for (let it = 0; it < maxIter; it++) {
      const prev = h;
      a = new Array(n).fill(0);
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) a[j] += W[i][j] * h[i];
      let m = Math.max(...a, 1e-300);
      a = a.map((v) => v / m);
      h = new Array(n).fill(0);
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) h[i] += W[i][j] * a[j];
      m = Math.max(...h, 1e-300);
      h = h.map((v) => v / m);
      let err = 0;
      for (let i = 0; i < n; i++) err += Math.abs(h[i] - prev[i]);
      if (err < tol) break;
    }
    const sh = sum(h) || 1, sa = sum(a) || 1;
    return { hub: h.map((v) => v / sh), auth: a.map((v) => v / sa) };
  }

  /* Brandes betweenness with edge length 1 / weight, normalized by (n-1)(n-2). */
  function betweenness(W) {
    const n = W.length;
    const bc = new Array(n).fill(0);
    const eps = 1e-9;
    for (let s = 0; s < n; s++) {
      const dist = new Array(n).fill(Infinity);
      const sigma = new Array(n).fill(0);
      const pred = Array.from({ length: n }, () => []);
      const done = new Array(n).fill(false);
      const order = [];
      dist[s] = 0; sigma[s] = 1;
      for (;;) {
        let v = -1, best = Infinity;
        for (let i = 0; i < n; i++) if (!done[i] && dist[i] < best) { best = dist[i]; v = i; }
        if (v < 0) break;
        done[v] = true; order.push(v);
        for (let w = 0; w < n; w++) {
          if (W[v][w] <= 0) continue;
          const d = dist[v] + 1 / W[v][w];
          if (d < dist[w] - eps) { dist[w] = d; sigma[w] = sigma[v]; pred[w] = [v]; }
          else if (Math.abs(d - dist[w]) <= eps && !done[w]) { sigma[w] += sigma[v]; pred[w].push(v); }
        }
      }
      const delta = new Array(n).fill(0);
      while (order.length) {
        const w = order.pop();
        for (const v of pred[w]) delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w]);
        if (w !== s) bc[w] += delta[w];
      }
    }
    const scale = n > 2 ? 1 / ((n - 1) * (n - 2)) : 0;
    return bc.map((v) => v * scale);
  }

  /* Fagiolo (2007) weighted directed clustering, as networkx.clustering does it. */
  function clustering(W) {
    const n = W.length;
    let maxW = 0;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) if (i !== j && W[i][j] > maxW) maxW = W[i][j];
    const wt = (u, v) => (u === v ? 0 : W[u][v] / (maxW || 1));
    const preds = (i) => { const s = []; for (let j = 0; j < n; j++) if (j !== i && W[j][i] > 0) s.push(j); return s; };
    const succs = (i) => { const s = []; for (let j = 0; j < n; j++) if (j !== i && W[i][j] > 0) s.push(j); return s; };
    const P = Array.from({ length: n }, (_, i) => new Set(preds(i)));
    const S = Array.from({ length: n }, (_, i) => new Set(succs(i)));
    const inter = (a, b) => [...a].filter((k) => b.has(k));
    const out = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
      let t = 0;
      for (const j of P[i]) {
        for (const k of inter(P[i], P[j])) t += Math.cbrt(wt(j, i) * wt(k, i) * wt(k, j));
        for (const k of inter(P[i], S[j])) t += Math.cbrt(wt(j, i) * wt(k, i) * wt(j, k));
        for (const k of inter(S[i], P[j])) t += Math.cbrt(wt(j, i) * wt(i, k) * wt(k, j));
        for (const k of inter(S[i], S[j])) t += Math.cbrt(wt(j, i) * wt(i, k) * wt(j, k));
      }
      for (const j of S[i]) {
        for (const k of inter(P[i], P[j])) t += Math.cbrt(wt(i, j) * wt(k, i) * wt(k, j));
        for (const k of inter(P[i], S[j])) t += Math.cbrt(wt(i, j) * wt(k, i) * wt(j, k));
        for (const k of inter(S[i], P[j])) t += Math.cbrt(wt(i, j) * wt(i, k) * wt(k, j));
        for (const k of inter(S[i], S[j])) t += Math.cbrt(wt(i, j) * wt(i, k) * wt(j, k));
      }
      const dt = P[i].size + S[i].size;
      const db = inter(P[i], S[i]).length;
      const denom = (dt * (dt - 1) - 2 * db) * 2;
      out[i] = t === 0 || denom <= 0 ? 0 : t / denom;
    }
    return out;
  }

  function gini(values) {
    const x = values.slice().sort((a, b) => a - b);
    const n = x.length, total = sum(x);
    if (n === 0 || total <= 0) return 0;
    let weighted = 0;
    x.forEach((v, i) => { weighted += (i + 1) * v; });
    return (2 * weighted) / (n * total) - (n + 1) / n;
  }

  /* Per node measures plus whole network summary for a pass count matrix. */
  function analyze(W) {
    const n = W.length;
    const inS = new Array(n).fill(0), outS = new Array(n).fill(0);
    let total = 0, edges = 0, reciprocated = 0;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      if (i === j || W[i][j] <= 0) continue;
      outS[i] += W[i][j]; inS[j] += W[i][j]; total += W[i][j]; edges++;
      if (W[j][i] > 0) reciprocated += Math.min(W[i][j], W[j][i]);
    }
    const strength = inS.map((v, i) => v + outS[i]);
    const pr = pagerank(W), { hub, auth } = hits(W), bt = betweenness(W), cl = clustering(W);
    let ent = 0;
    for (const p of pr) if (p > 0) ent -= p * Math.log(p);
    const team = {
      passes: total, density: n > 1 ? edges / (n * (n - 1)) : 0,
      reciprocity: total ? reciprocated / total : NaN, strengthGini: gini(strength),
      pagerankEntropy: n > 1 ? ent / Math.log(n) : NaN,
      top3Pagerank: sum(pr.slice().sort((a, b) => a - b).slice(-3)),
      betweennessMax: bt.length ? Math.max(...bt) : 0, clusteringMean: n ? sum(cl) / n : 0,
    };
    return { inStrength: inS, outStrength: outS, strength, pagerank: pr, hub, authority: auth,
             betweenness: bt, clustering: cl, team };
  }

  const api = { pagerank, hits, betweenness, clustering, gini, analyze };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Metrics = api;
})(typeof window !== "undefined" ? window : globalThis);
