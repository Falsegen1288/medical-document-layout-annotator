const pptxgen = require("pptxgenjs");
const path = require("path");

// ---------- GLOBAL GRID MATH ----------
const PAGE_W = 13.333, PAGE_H = 7.5;
const MARGIN = 0.5;
const CONTENT_W = PAGE_W - MARGIN * 2; // 12.333
const CONTENT_TOP = 1.62;   // below eyebrow+title+subtitle block
const CONTENT_BOTTOM = 7.05; // above page number

// ---------- PALETTE ----------
const NAVY = "18233F";
const NAVY2 = "1C2F50";
const TEAL = "237A98";
const RUST = "DF6438";
const GOLD = "F1A641";
const BG_LIGHT = "F7F8FC";
const GRAY = "4B5563";
const GRAY_SOFT = "8A93A6";
const WHITE = "FFFFFF";
const LAV_TEXT = "C7D0E8"; // light text on navy bg

const SERIF = "Cambria";
const SANS = "Calibri";

function fresh(o) { return JSON.parse(JSON.stringify(o)); }
const CARD_SHADOW = () => ({ type: "outer", color: "1C2F50", opacity: 0.18, blur: 8, offset: 3, angle: 90 });

const pres = new pptxgen();
pres.defineLayout({ name: "WIDE", width: PAGE_W, height: PAGE_H });
pres.layout = "WIDE";

// ---------- SHARED HELPERS ----------
function pageBg(slide, color) {
  slide.addShape("rect", { x: 0, y: 0, w: PAGE_W, h: PAGE_H, fill: { color }, line: { type: "none" } });
}

function pageNumber(slide, n, dark) {
  slide.addText(String(n), {
    x: PAGE_W - 0.9, y: PAGE_H - 0.42, w: 0.5, h: 0.3,
    fontFace: SANS, fontSize: 10, color: dark ? LAV_TEXT : GRAY_SOFT, align: "right",
  });
}

// header block: eyebrow (small caps teal), serif title, sans subtitle
function header(slide, eyebrow, title, subtitle, opts) {
  opts = opts || {};
  const titleColor = opts.titleColor || NAVY;
  const eyebrowColor = opts.eyebrowColor || TEAL;
  const subColor = opts.subColor || GRAY;
  slide.addText(eyebrow.toUpperCase(), {
    x: MARGIN, y: 0.42, w: CONTENT_W, h: 0.3,
    fontFace: SANS, fontSize: 12, bold: true, color: eyebrowColor, charSpacing: 2, margin: 0,
  });
  slide.addText(title, {
    x: MARGIN, y: 0.72, w: CONTENT_W, h: 0.55,
    fontFace: SERIF, fontSize: 30, bold: true, color: titleColor, margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: MARGIN, y: 1.28, w: CONTENT_W, h: 0.32,
      fontFace: SANS, fontSize: 13.5, color: subColor, margin: 0, italic: opts.subItalic || false,
    });
  }
}

// circular badge with letter/number
function badge(slide, x, y, d, color, label, fontSize) {
  slide.addShape("ellipse", { x, y, w: d, h: d, fill: { color }, line: { type: "none" } });
  slide.addText(label, {
    x, y, w: d, h: d, align: "center", valign: "middle",
    fontFace: SERIF, fontSize: fontSize || 15, bold: true, color: WHITE, margin: 0,
  });
}

function card(slide, x, y, w, h, opts) {
  opts = opts || {};
  slide.addShape("roundRect", {
    x, y, w, h, rectRadius: 0.08,
    fill: { color: opts.fill || WHITE },
    line: { type: "none" },
    shadow: opts.shadow === false ? undefined : CARD_SHADOW(),
  });
}

// ==================================================================
// SLIDE 1 — TITLE
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, NAVY);

  s.addText("BIWEEKLY INTERN PROGRESS REPORT", {
    x: MARGIN, y: 2.5, w: CONTENT_W, h: 0.35,
    fontFace: SANS, fontSize: 13, bold: true, color: GOLD, charSpacing: 3, margin: 0,
  });
  s.addText("Document Intelligence &\nRetrieval Pipeline", {
    x: MARGIN, y: 2.92, w: 10.5, h: 1.55,
    fontFace: SERIF, fontSize: 42, bold: true, color: WHITE, margin: 0, lineSpacingMultiple: 1.05,
  });
  s.addText("Embedding model benchmarks  →  hybrid retrieval leaderboard  →  parsing re-evaluation with GLM-OCR", {
    x: MARGIN, y: 4.58, w: 11.6, h: 0.4,
    fontFace: SANS, fontSize: 15, color: LAV_TEXT, margin: 0,
  });
  s.addShape("line", { x: MARGIN, y: 6.55, w: 0.55, h: 0, line: { color: TEAL, width: 2 } });
  s.addText("Weeks 5–6 • Document Understanding Track", {
    x: MARGIN, y: 6.68, w: 8, h: 0.32,
    fontFace: SANS, fontSize: 12.5, color: TEAL, bold: true, margin: 0,
  });
}

// ==================================================================
// SLIDE 2 — OVERVIEW (stacked full-width cards)
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Overview", "What this report covers", null);

  const items = [
    { n: "01", color: TEAL, t: "Week 5 Recap: Embedding Models", d: "9 dense, sparse, multi-vector, and vision-language embedding models registered and benchmarked" },
    { n: "02", color: NAVY2, t: "Week 5: Hybrid Evaluation Harness", d: "Built a 4-stage retrieval pipeline (BM25 + dense + SPLADE → RRF fusion → LLM judge) and ran it on a 54-pair QA bank" },
    { n: "03", color: RUST, t: "Week 6: Revisiting Parsing with GLM-OCR", d: "Benchmarked a new single-model 0.9B VLM against our locked-in multi-stage parsing pipeline" },
    { n: "04", color: GOLD, t: "Week 7 Plan", d: "Formal CER/TEDS for GLM-OCR, hallucination mitigation, and the remaining embedding-model candidates" },
  ];
  const top = CONTENT_TOP + 0.05, bottom = CONTENT_BOTTOM;
  const gap = 0.2;
  const h = (bottom - top - gap * (items.length - 1)) / items.length;
  const d = 0.62;
  items.forEach((it, i) => {
    const y = top + i * (h + gap);
    card(s, MARGIN, y, CONTENT_W, h);
    badge(s, MARGIN + 0.32, y + (h - d) / 2, d, it.color, it.n, 15);
    const tx = MARGIN + 0.32 + d + 0.32;
    const tw = CONTENT_W - (0.32 + d + 0.32) - 0.4;
    s.addText(it.t, { x: tx, y: y + 0.12, w: tw, h: 0.32, fontFace: SERIF, fontSize: 16, bold: true, color: NAVY, margin: 0 });
    s.addText(it.d, { x: tx, y: y + 0.46, w: tw, h: h - 0.55, fontFace: SANS, fontSize: 12, color: GRAY, margin: 0, valign: "top" });
  });
  pageNumber(s, 2, false);
}

// ==================================================================
// SLIDE 3 — WEEK 5 RECAP: EMBEDDING MODELS EVALUATED
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 5 Recap — Embedding Model Registry", "Nine models, four representation types",
    "All backends pinned to commit SHAs in models.yaml and benchmarked on the same 54-pair ground-truth QA bank.");

  // banner
  const bannerY = CONTENT_TOP + 0.05, bannerH = 0.62;
  s.addShape("roundRect", { x: MARGIN, y: bannerY, w: CONTENT_W, h: bannerH, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" } });
  s.addShape("ellipse", { x: MARGIN + 0.25, y: bannerY + (bannerH - 0.34) / 2, w: 0.34, h: 0.34, fill: { color: GOLD }, line: { type: "none" } });
  s.addText("\u2713", { x: MARGIN + 0.25, y: bannerY + (bannerH - 0.34) / 2, w: 0.34, h: 0.34, align: "center", valign: "middle", fontFace: SANS, fontSize: 14, bold: true, color: NAVY, margin: 0 });
  s.addText("Registry locked — 9 models spanning dense, sparse, multi-vector, and vision-language embeddings, evaluated under one harness", {
    x: MARGIN + 0.75, y: bannerY, w: CONTENT_W - 1.1, h: bannerH, valign: "middle",
    fontFace: SANS, fontSize: 13.5, bold: true, color: WHITE, margin: 0,
  });

  const cols = [
    { label: "DENSE", pillColor: TEAL, model: "qwen3-embedding-8b (4-bit)", note: "Best overall — top Spec Hit Rate (1.00) and top Faithfulness (0.454) when hybridized with BM25." },
    { label: "SPARSE / LEXICAL", pillColor: RUST, model: "BM25 (custom tokenizer)", note: "Custom regex tokenizer preserves full alphanumeric part numbers (e.g. 352952) — the backbone of every hybrid win." },
    { label: "MULTI-VECTOR", pillColor: NAVY2, model: "bge-m3", note: "Only model producing dense + sparse + ColBERT vectors simultaneously — broadest single-model coverage." },
  ];
  const rowY = bannerY + bannerH + 0.3;
  const rowH = CONTENT_BOTTOM - rowY;
  const gap = 0.35;
  const w = (CONTENT_W - gap * 2) / 3;
  cols.forEach((c, i) => {
    const x = MARGIN + i * (w + gap);
    card(s, x, rowY, w, rowH);
    const pad = 0.28;
    s.addText(c.label, { x: x + pad, y: rowY + 0.24, w: w - pad * 2, h: 0.26, fontFace: SANS, fontSize: 11, bold: true, color: GRAY_SOFT, charSpacing: 1.5, margin: 0 });
    s.addShape("roundRect", { x: x + pad, y: rowY + 0.56, w: w - pad * 2, h: 0.56, rectRadius: 0.28, fill: { color: c.pillColor }, line: { type: "none" } });
    s.addText(c.model, { x: x + pad, y: rowY + 0.56, w: w - pad * 2, h: 0.56, align: "center", valign: "middle", fontFace: SERIF, fontSize: 14, bold: true, color: WHITE, margin: 0 });
    s.addText("GO-TO BACKEND", { x: x + pad, y: rowY + 1.28, w: w - pad * 2, h: 0.24, fontFace: SANS, fontSize: 10, bold: true, color: GOLD, charSpacing: 1.5, margin: 0 });
    s.addText(c.note, { x: x + pad, y: rowY + 1.56, w: w - pad * 2, h: rowH - 1.56 - 0.2, fontFace: SANS, fontSize: 11.5, color: GRAY, margin: 0, valign: "top" });
  });
  pageNumber(s, 3, false);
}

// ==================================================================
// SLIDE 4 — EVALUATION HARNESS ARCHITECTURE (flow)
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 5 — Evaluation Harness", "From documents to a leaderboard", "run_leaderboard.py — four stages, fused with Reciprocal Rank Fusion (k=60)");

  const stages = [
    { k: "D", color: TEAL, t: "Doc Prep & Chunking", d: "PDFs parsed into linked_chunks.jsonl, preserving text\u2013figure/table associations" },
    { k: "H", color: NAVY2, t: "Hybrid Indexing", d: "BM25 lexical + dense (SentenceTransformers) + SPLADE neural-sparse indexers, built in parallel" },
    { k: "F", color: RUST, t: "RRF Fusion & Eval", d: "Rank lists fused via RRF (k=60); scored with HitRate@K and MRR@K against the QA bank" },
    { k: "J", color: GOLD, t: "LLM Judge & Leaderboard", d: "qwen3-32b scores Ragas + DeepEval faithfulness, independent of the answer generator" },
  ];
  const top = CONTENT_TOP + 0.35;
  const boxH = 2.55;
  const gap = 0.5; // includes arrow space
  const w = (CONTENT_W - gap * (stages.length - 1)) / stages.length;
  stages.forEach((st, i) => {
    const x = MARGIN + i * (w + gap);
    card(s, x, top, w, boxH);
    const d = 0.72;
    badge(s, x + (w - d) / 2, top + 0.3, d, st.color, st.k, 20);
    s.addText(st.t, { x: x + 0.2, y: top + 1.18, w: w - 0.4, h: 0.55, align: "center", fontFace: SERIF, fontSize: 14.5, bold: true, color: NAVY, margin: 0 });
    s.addText(st.d, { x: x + 0.24, y: top + 1.72, w: w - 0.48, h: boxH - 1.9, align: "center", valign: "top", fontFace: SANS, fontSize: 10.8, color: GRAY, margin: 0 });
    if (i < stages.length - 1) {
      s.addText("\u2192", { x: x + w, y: top + 0.15, w: gap, h: 0.5, align: "center", valign: "middle", fontFace: SANS, fontSize: 22, bold: true, color: GRAY_SOFT, margin: 0 });
    }
  });

  // engineering notes row
  const noteY = top + boxH + 0.35;
  const notes = [
    "Embedding cache: 7 min \u2192 20 ms on repeat lookups",
    "tiktoken truncation capped at 4,800 tokens/context",
    "Completion DB avoids re-running Groq generations",
  ];
  const ngap = 0.3;
  const nw = (CONTENT_W - ngap * 2) / 3;
  notes.forEach((n, i) => {
    const x = MARGIN + i * (nw + ngap);
    s.addShape("roundRect", { x, y: noteY, w: nw, h: 0.5, rectRadius: 0.06, fill: { color: WHITE }, line: { color: "E3E7F0", width: 1 } });
    s.addText(n, { x: x + 0.18, y: noteY, w: nw - 0.36, h: 0.5, valign: "middle", fontFace: SANS, fontSize: 10.5, color: GRAY, margin: 0 });
  });
  pageNumber(s, 4, false);
}

// ==================================================================
// SLIDE 5 — BENCHMARK LEADERBOARD TABLE
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 5 — Benchmark Results", "Top model / strategy combinations",
    "Scored across all 54 Q&A pairs — Spec Hit Rate, Overall Hit Rate, and downstream generator Faithfulness");

  const headRow = ["Rank", "Model", "Strategy", "Spec Hit@5", "Overall Hit@5", "Faithfulness"].map(t => ({
    text: t, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontFace: SANS, fontSize: 12, align: t === "Rank" || t === "Model" || t === "Strategy" ? "left" : "center", valign: "middle" },
  }));
  const data = [
    [1, "qwen3-embedding-8b-4bit", "bm25_hybrid", "1.00", "0.518", "0.454"],
    [2, "baseline", "bm25_only", "1.00", "0.722", "0.272"],
    [3, "bge-m3", "bm25_hybrid", "1.00", "0.444", "0.181"],
    [4, "nv-embed-v2-fp16", "bm25_hybrid", "1.00", "0.500", "0.181"],
    [5, "bge-m3", "dense_only", "1.00", "0.240", "0.090"],
    [6, "nomic-embed-text", "bm25_hybrid", "1.00", "0.462", "0.000"],
    [7, "bge-m3", "dense_sparse_colbert_hybrid", "0.50", "0.166", "0.090"],
    [8, "granite-vision-embedding", "text_only", "0.50", "0.363", "0.000"],
  ];
  const rows = [headRow];
  data.forEach((r, i) => {
    const isWinner = i === 0;
    rows.push(r.map((cell, ci) => ({
      text: String(cell),
      options: {
        fontFace: SANS, fontSize: 11.5,
        bold: isWinner || ci === 3 || ci === 5 ? isWinner : false,
        color: isWinner ? NAVY : GRAY,
        fill: { color: isWinner ? "FDECE2" : (i % 2 === 0 ? WHITE : "F2F4FA") },
        align: ci <= 2 ? "left" : "center", valign: "middle",
      },
    })));
  });

  s.addTable(rows, {
    x: MARGIN, y: CONTENT_TOP + 0.05, w: CONTENT_W, h: 4.55,
    colW: [0.75, 3.55, 3.55, 1.6, 1.6, 1.5],
    border: { type: "solid", color: "E3E7F0", pt: 0.75 },
    autoPage: false,
    rowH: 0.5,
  });

  s.addText("qwen3-embedding-8b-4bit + bm25_hybrid ranks #1 on Faithfulness (0.454) — exact-match lexical context prevents the generator from hallucinating spec values.", {
    x: MARGIN, y: CONTENT_TOP + 0.05 + 4.55 + 0.18, w: CONTENT_W, h: 0.4,
    fontFace: SANS, fontSize: 11.5, italic: true, color: RUST, margin: 0,
  });
  pageNumber(s, 5, false);
}

// ==================================================================
// SLIDE 6 — CHART: FAITHFULNESS BY MODEL
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 5 — Benchmark Results", "Faithfulness by model / strategy", "Downstream RAG-generator faithfulness (Ragas), for the six models with a perfect Spec Hit Rate@5");

  const chartW = 8.05, chartH = 4.65;
  const chartX = MARGIN, chartY = CONTENT_TOP + 0.05;
  const labels = ["qwen3-8b-4bit\nbm25_hybrid", "baseline\nbm25_only", "bge-m3\nbm25_hybrid", "nv-embed-v2\nbm25_hybrid", "bge-m3\ndense_only", "nomic-embed\nbm25_hybrid"];
  const vals = [0.454, 0.272, 0.181, 0.181, 0.090, 0.000];
  s.addChart("bar", [{ name: "Faithfulness", labels, values: vals }], {
    x: chartX, y: chartY, w: chartW, h: chartH,
    chartColors: [TEAL],
    showTitle: false,
    showLegend: false,
    showValue: true,
    dataLabelPosition: "outEnd",
    dataLabelColor: NAVY,
    dataLabelFontSize: 10,
    dataLabelFormatCode: "0.000",
    catAxisLabelColor: GRAY,
    catAxisLabelFontSize: 9,
    valAxisLabelColor: GRAY,
    valAxisLabelFontSize: 9,
    valAxisLabelFormatCode: "0.0",
    valGridLine: { color: "E3E7F0", size: 0.75 },
    catGridLine: { style: "none" },
    barGapWidthPct: 40,
    plotArea: { fill: { color: "FFFFFF" } },
  });

  const sideX = chartX + chartW + 0.35;
  const sideW = PAGE_W - MARGIN - sideX;
  card(s, sideX, chartY, sideW, chartH);
  s.addText("READING THE CHART", { x: sideX + 0.25, y: chartY + 0.25, w: sideW - 0.5, h: 0.28, fontFace: SANS, fontSize: 11, bold: true, color: GRAY_SOFT, charSpacing: 1.5, margin: 0 });
  const bullets = [
    "All six arms hit a perfect 1.00 Spec Hit Rate@5",
    "Faithfulness is where they separate — hybrid BM25 arms dominate",
    "nomic-embed-text scores 0.000 despite perfect retrieval — a generation-side gap, not a retrieval one",
    "Exact-match lexical context is the strongest predictor of faithful answers",
  ];
  s.addText(bullets.map((b, i) => ({ text: b, options: { bullet: { code: "25CF" }, breakLine: i < bullets.length - 1, color: GRAY, fontSize: 11.5, paraSpaceAfter: 10 } })), {
    x: sideX + 0.25, y: chartY + 0.62, w: sideW - 0.5, h: chartH - 0.85, fontFace: SANS, valign: "top", margin: 0,
  });
  pageNumber(s, 6, false);
}

// ==================================================================
// SLIDE 7 — KEY INFERENCES (2x2 grid)
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 5 — Engineering Inferences", "What the benchmark tells us", null);

  const items = [
    { pill: "1.00 hit rate", color: GOLD, t: "Lexical BM25 wins on spec codes", d: "Subword tokenizers fragment part/model numbers (e.g. 352952). A regex tokenizer preserving full alphanumeric strings hits 100% Hit Rate@5 on spec lookups." },
    { pill: "RRF k=60", color: TEAL, t: "Hybrid fusion is essential", d: "Neither pure dense nor pure sparse retrieval covers every query type. RRF-fused hybrid retrieval gives the best accuracy and resilience across mixed workloads." },
    { pill: "0.454 best", color: RUST, t: "Exact context \u2192 higher faithfulness", d: "Downstream LLM faithfulness rises when exact-match lexical snippets sit in the context window, preventing the generator from hallucinating spec values." },
    { pill: "3-way coverage", color: NAVY2, t: "Dense, sparse & ColBERT are complementary", d: "Dense models excel at abstract synthesis; sparse/multi-vector excel at token-level precision. bge-m3 combines all three for full coverage." },
  ];
  const top = CONTENT_TOP + 0.05;
  const bottom = CONTENT_BOTTOM;
  const colGap = 0.4, rowGap = 0.35;
  const w = (CONTENT_W - colGap) / 2;
  const h = (bottom - top - rowGap) / 2;
  items.forEach((it, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = MARGIN + col * (w + colGap);
    const y = top + row * (h + rowGap);
    card(s, x, y, w, h);
    const pad = 0.3;
    s.addShape("roundRect", { x: x + pad, y: y + 0.24, w: 1.7, h: 0.4, rectRadius: 0.2, fill: { color: it.color }, line: { type: "none" } });
    s.addText(it.pill, { x: x + pad, y: y + 0.24, w: 1.7, h: 0.4, align: "center", valign: "middle", fontFace: SANS, fontSize: 11, bold: true, color: WHITE, margin: 0 });
    s.addText(it.t, { x: x + pad, y: y + 0.82, w: w - pad * 2, h: 0.5, fontFace: SERIF, fontSize: 15.5, bold: true, color: NAVY, margin: 0 });
    s.addText(it.d, { x: x + pad, y: y + 1.32, w: w - pad * 2, h: h - 1.32 - 0.2, fontFace: SANS, fontSize: 11.5, color: GRAY, valign: "top", margin: 0 });
  });
  pageNumber(s, 7, false);
}

// ==================================================================
// SLIDE 8 — WEEK 6: GLM-OCR INTRO (stat callouts)
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 6 — Revisiting Parsing", "GLM-OCR: a single-model contender",
    "zai-org/GLM-OCR (Zhipu AI) — a compact vision-language model that reads pixels and writes structured Markdown directly, no separate stages.");

  const stats = [
    { big: "0.9B", label: "parameters", sub: "vs. an 885M-param layout model alone in the old pipeline", color: TEAL },
    { big: "94.62", label: "OmniDocBench V1.5", sub: "#1 on the public leaderboard at release", color: RUST },
    { big: "1 model", label: "replaces 4\u20135", sub: "layout + OCR + table + caption + cleanup stages, unified", color: GOLD },
  ];
  const top = CONTENT_TOP + 0.15;
  const h = 2.5;
  const gap = 0.35;
  const w = (CONTENT_W - gap * 2) / 3;
  stats.forEach((st, i) => {
    const x = MARGIN + i * (w + gap);
    card(s, x, top, w, h);
    s.addText(st.big, { x: x + 0.2, y: top + 0.28, w: w - 0.4, h: 0.85, align: "center", fontFace: SERIF, fontSize: 40, bold: true, color: st.color, margin: 0 });
    s.addText(st.label.toUpperCase(), { x: x + 0.2, y: top + 1.12, w: w - 0.4, h: 0.3, align: "center", fontFace: SANS, fontSize: 11.5, bold: true, color: NAVY, charSpacing: 1, margin: 0 });
    s.addText(st.sub, { x: x + 0.3, y: top + 1.5, w: w - 0.6, h: h - 1.7, align: "center", valign: "top", fontFace: SANS, fontSize: 10.5, color: GRAY, margin: 0 });
  });

  // architecture comparison strip
  const stripY = top + h + 0.35;
  const stripH = CONTENT_BOTTOM - stripY;
  card(s, MARGIN, stripY, CONTENT_W, stripH);
  const half = (CONTENT_W - 0.6) / 2;
  s.addText("INITIAL PIPELINE — 4\u20135 CHAINED MODELS", { x: MARGIN + 0.3, y: stripY + 0.2, w: half, h: 0.26, fontFace: SANS, fontSize: 10.5, bold: true, color: GRAY_SOFT, charSpacing: 1, margin: 0 });
  s.addText("DocLayoutYOLO  \u2192  EasyOCR / Tesseract  \u2192  Docling + TableFormer/TATR  \u2192  Qwen2.5VL-3B captioning  \u2192  LLM cleanup pass", {
    x: MARGIN + 0.3, y: stripY + 0.52, w: half, h: stripH - 0.75, fontFace: SANS, fontSize: 11.5, color: NAVY, valign: "top", margin: 0,
  });
  s.addShape("line", { x: MARGIN + half + 0.3, y: stripY + 0.18, w: 0, h: stripH - 0.36, line: { color: "E3E7F0", width: 1.25 } });
  s.addText("GLM-OCR — ONE UNIFIED VLM", { x: MARGIN + half + 0.6, y: stripY + 0.2, w: half, h: 0.26, fontFace: SANS, fontSize: 10.5, bold: true, color: TEAL, charSpacing: 1, margin: 0 });
  s.addText("Vision encoder + causal LM with Multi-Token Prediction \u2014 outputs structured Markdown (tables, headers, layout) directly from page pixels.", {
    x: MARGIN + half + 0.6, y: stripY + 0.52, w: half, h: stripH - 0.75, fontFace: SANS, fontSize: 11.5, color: NAVY, valign: "top", margin: 0,
  });
  pageNumber(s, 8, false);
}

// ==================================================================
// SLIDE 9 — TEXT OCR RESULTS (GLM-OCR page-level CER/WER)
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 6 — GLM-OCR Benchmark", "Text OCR: page-level results",
    "Real GPU inference, cuda:0, GTX 1650, 4-bit quantized \u2014 scored end-to-end on full, un-cropped 300 DPI pages");

  const headRow = ["Page", "GT Chars", "Pred Chars", "CER", "WER", "Latency"].map(t => ({
    text: t, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontFace: SANS, fontSize: 12, align: t === "Page" ? "left" : "center", valign: "middle" },
  }));
  const data = [
    ["1 (Cover)", "416", "478", "0.8341", "0.8667", "105.6s"],
    ["2 (Diagnostics Catalog)", "1,734", "1,541", "0.4683", "0.5882", "148.9s"],
    ["4 (Ordering & Contact)", "1,563", "1,442", "0.4210", "0.6468", "134.3s"],
    ["Filtered Average (1, 2, 4)", "3,713", "3,461", "0.4894", "0.6441", "129.6s / page"],
  ];
  const rows = [headRow];
  data.forEach((r, i) => {
    const isAvg = i === data.length - 1;
    rows.push(r.map((cell, ci) => ({
      text: cell,
      options: {
        fontFace: SANS, fontSize: 12, bold: isAvg,
        color: isAvg ? NAVY : GRAY,
        fill: { color: isAvg ? "FDECE2" : (i % 2 === 0 ? WHITE : "F2F4FA") },
        align: ci === 0 ? "left" : "center", valign: "middle",
      },
    })));
  });

  const tableY = CONTENT_TOP + 0.05, tableH = 2.75;
  s.addTable(rows, {
    x: MARGIN, y: tableY, w: CONTENT_W, h: tableH,
    colW: [3.2, 1.9, 1.9, 1.83, 1.83, 1.673],
    border: { type: "solid", color: "E3E7F0", pt: 0.75 },
    autoPage: false,
    rowH: 0.55,
  });

  s.addText("Excluded: Page 3 \u2014 GLM-OCR entered a repetition loop, generating 3,831 chars of table content vs. 1,076 GT chars (\u2248 3.5\u00d7 repeat). See Slide 11.", {
    x: MARGIN, y: tableY + tableH + 0.18, w: CONTENT_W, h: 0.32,
    fontFace: SANS, fontSize: 11.5, italic: true, color: RUST, margin: 0,
  });

  const bY = tableY + tableH + 0.62;
  const bH = 0.9;
  s.addShape("roundRect", { x: MARGIN, y: bY, w: CONTENT_W, h: bH, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" } });
  s.addText("Not apples-to-apples yet: baseline EasyOCR CER (0.1078) was scored on 64 pre-cropped element bounding boxes. GLM-OCR CER (0.4894) is end-to-end on full uncropped pages \u2014 it also absorbs line-ordering, header/footer, and Markdown-formatting differences the cropped baseline never sees.", {
    x: MARGIN + 0.3, y: bY + 0.12, w: CONTENT_W - 0.6, h: bH - 0.24, valign: "middle",
    fontFace: SANS, fontSize: 12, color: WHITE, margin: 0,
  });
  pageNumber(s, 9, false);
}

// ==================================================================
// SLIDE 10 — TABLE EXTRACTION RESULTS (TEDS comparison)
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 6 — GLM-OCR Benchmark", "Table extraction: GLM-OCR takes the lead",
    "Evaluated with GLM-OCR's official \u201cTable Recognition:\u201d task prompt, which activates its structured HTML decoder head");

  const headRow = ["Model", "TEDS", "TEDS (Structure)", "Cell F1"].map(t => ({
    text: t, options: { bold: true, color: WHITE, fill: { color: NAVY }, fontFace: SANS, fontSize: 12.5, align: t === "Model" ? "left" : "center", valign: "middle" },
  }));
  const data = [
    ["Docling (TableFormer)", "0.7295", "0.7295", "0.9828"],
    ["TATR (Table Transformer)", "0.7444", "0.8684", "0.4213"],
    ["EasyOCR + Structure", "0.9816", "1.0000", "0.8720"],
    ["GLM-OCR (official prompt)", "0.9996", "1.0000", "1.0000"],
  ];
  const rows = [headRow];
  data.forEach((r, i) => {
    const isWinner = i === data.length - 1;
    rows.push(r.map((cell, ci) => ({
      text: cell,
      options: {
        fontFace: SANS, fontSize: 12.5, bold: isWinner,
        color: isWinner ? NAVY : GRAY,
        fill: { color: isWinner ? "FDECE2" : (i % 2 === 0 ? WHITE : "F2F4FA") },
        align: ci === 0 ? "left" : "center", valign: "middle",
      },
    })));
  });

  const tableY = CONTENT_TOP + 0.05, tableH = 2.75;
  s.addTable(rows, {
    x: MARGIN, y: tableY, w: CONTENT_W, h: tableH,
    colW: [4.93, 2.467, 2.467, 2.469],
    border: { type: "solid", color: "E3E7F0", pt: 0.75 },
    autoPage: false,
    rowH: 0.55,
  });

  const chipY = tableY + tableH + 0.28, chipH = 0.9;
  const chipGap = 0.35;
  const chipW = (CONTENT_W - chipGap) / 2;
  const chips = [
    { id: "e0043", page: "Page 3", desc: "Patient Monitor Feature Comparison (14\u00d74)", teds: "0.9993" },
    { id: "e0074", page: "Page 4", desc: "ServicePlus Plans (4\u00d73)", teds: "1.0000" },
  ];
  chips.forEach((c, i) => {
    const x = MARGIN + i * (chipW + chipGap);
    card(s, x, chipY, chipW, chipH);
    s.addText(c.teds, { x: x + 0.28, y: chipY + 0.14, w: 1.6, h: chipH - 0.28, valign: "middle", fontFace: SERIF, fontSize: 26, bold: true, color: TEAL, margin: 0 });
    s.addText(`${c.id}  \u2014  ${c.page}`, { x: x + 2.0, y: chipY + 0.16, w: chipW - 2.3, h: 0.32, fontFace: SANS, fontSize: 12, bold: true, color: NAVY, margin: 0 });
    s.addText(c.desc, { x: x + 2.0, y: chipY + 0.48, w: chipW - 2.3, h: 0.36, fontFace: SANS, fontSize: 11, color: GRAY, margin: 0 });
  });

  const bY = chipY + chipH + 0.28, bH = 0.62;
  s.addShape("roundRect", { x: MARGIN, y: bY, w: CONTENT_W, h: bH, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" } });
  s.addText("GLM-OCR beats every baseline table specialist \u2014 0.9996 TEDS vs. 0.9816 (EasyOCR+Structure), 0.7444 (TATR), 0.7295 (Docling).", {
    x: MARGIN + 0.3, y: bY, w: CONTENT_W - 0.6, h: bH, valign: "middle", fontFace: SANS, fontSize: 12.5, bold: true, color: WHITE, margin: 0,
  });
  pageNumber(s, 10, false);
}

// ==================================================================
// SLIDE 11 — FINDINGS & RECOMMENDATION (3-card row)
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 6 — GLM-OCR Benchmark", "Findings & recommendation", "What the page-level CER and prompted-TEDS results change about our read on GLM-OCR");

  const cols = [
    { n: "1", color: TEAL, t: "Prompting Unlocks Structure", d: "Full-page parsing with no task prompt yields plain, unformatted text. The official \u201cTable Recognition:\u201d prompt activates a specialized decoder head that emits clean <table> HTML with 100% cell accuracy." },
    { n: "2", color: RUST, t: "Repetition Loop on Dense Pages", d: "Page 3\u2019s dense table triggered a token-repetition loop \u2014 3\u00d7 the ground-truth length. Needs standard generation stop-criteria / max-new-tokens limits before it\u2019s production-safe." },
    { n: "3", color: NAVY2, t: "Eval Methodology Still Diverges", d: "Baseline CER is scored on 64 cropped element boxes; GLM-OCR CER is scored end-to-end on full pages. The two numbers aren\u2019t directly comparable until we run both under one protocol." },
  ];
  const rowY = CONTENT_TOP + 0.05;
  const rowH = CONTENT_BOTTOM - rowY - 0.78;
  const gap = 0.35;
  const w = (CONTENT_W - gap * 2) / 3;
  cols.forEach((c, i) => {
    const x = MARGIN + i * (w + gap);
    card(s, x, rowY, w, rowH);
    const d = 0.5;
    badge(s, x + 0.28, rowY + 0.26, d, c.color, c.n, 15);
    s.addText(c.t, { x: x + 0.28, y: rowY + 0.94, w: w - 0.56, h: 0.55, fontFace: SERIF, fontSize: 15, bold: true, color: NAVY, margin: 0 });
    s.addText(c.d, { x: x + 0.28, y: rowY + 1.52, w: w - 0.56, h: rowH - 1.52 - 0.2, fontFace: SANS, fontSize: 11, color: GRAY, valign: "top", margin: 0 });
  });

  const bY = rowY + rowH + 0.25;
  const bH = 0.78;
  s.addShape("roundRect", { x: MARGIN, y: bY, w: CONTENT_W, h: bH, rectRadius: 0.08, fill: { color: NAVY }, line: { type: "none" } });
  s.addText("Recommendation: GLM-OCR\u2019s single 0.9B model already beats every specialized table extractor (0.9996 TEDS) and stays #1 on OmniDocBench (94.62). Next, hold Unlimited OCR to the same protocol before picking a production parser.", {
    x: MARGIN + 0.3, y: bY + 0.1, w: CONTENT_W - 0.6, h: bH - 0.2, valign: "middle", fontFace: SANS, fontSize: 12, bold: true, color: WHITE, margin: 0,
  });
  pageNumber(s, 11, false);
}

// ==================================================================
// SLIDE 12 — WEEK 7 PLAN
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, BG_LIGHT);
  header(s, "Week 7 Plan", "Bring Unlimited OCR into the comparison, then re-run the harness",
    "Same protocol, one more model \u2014 then the winning parser feeds directly into the Week 5 retrieval pipeline");

  const items = [
    { color: TEAL, t: "Benchmark Unlimited OCR", d: "Run the same page-level CER/WER + official-prompt TEDS protocol on Unlimited OCR for a fair three-way comparison" },
    { color: RUST, t: "Fix the repetition loop", d: "Add generation stop-criteria / max-new-tokens limits to GLM-OCR before it touches dense, table-heavy pages" },
    { color: NAVY2, t: "Swap the baseline in the harness", d: "Re-run the Week 5 retrieval pipeline with GLM-OCR and Unlimited OCR replacing DocLayoutYOLO + EasyOCR + Docling" },
    { color: GOLD, t: "Compare end-to-end faithfulness", d: "Measure whether better parsing accuracy actually lifts RAG faithfulness downstream, not just parsing-stage metrics" },
  ];
  const top = CONTENT_TOP + 0.1;
  const bottom = CONTENT_BOTTOM;
  const gap = 0.35;
  const w = (CONTENT_W - gap * 3) / 4;
  const h = bottom - top;
  items.forEach((it, i) => {
    const x = MARGIN + i * (w + gap);
    card(s, x, top, w, h);
    const d = 0.55;
    badge(s, x + (w - d) / 2, top + 0.3, d, it.color, String(i + 1), 16);
    s.addText(it.t, { x: x + 0.22, y: top + 1.05, w: w - 0.44, h: 0.7, align: "center", fontFace: SERIF, fontSize: 13.5, bold: true, color: NAVY, margin: 0 });
    s.addText(it.d, { x: x + 0.22, y: top + 1.75, w: w - 0.44, h: h - 1.75 - 0.2, align: "center", valign: "top", fontFace: SANS, fontSize: 10.5, color: GRAY, margin: 0 });
  });
  pageNumber(s, 12, false);
}

// ==================================================================
// SLIDE 13 — THANK YOU / CLOSING
// ==================================================================
{
  const s = pres.addSlide();
  pageBg(s, NAVY);
  s.addText("THANK YOU", {
    x: MARGIN, y: 2.85, w: CONTENT_W, h: 0.4,
    fontFace: SANS, fontSize: 14, bold: true, color: GOLD, charSpacing: 3, margin: 0,
  });
  s.addText("Questions & Discussion", {
    x: MARGIN, y: 3.25, w: CONTENT_W, h: 0.9,
    fontFace: SERIF, fontSize: 38, bold: true, color: WHITE, margin: 0,
  });
  s.addText("Next check-in: Week 7 \u2014 Unlimited OCR benchmark, and a full harness re-run with GLM-OCR + Unlimited OCR replacing the baseline parser", {
    x: MARGIN, y: 4.15, w: 11.3, h: 0.6,
    fontFace: SANS, fontSize: 14, color: LAV_TEXT, margin: 0,
  });
  pageNumber(s, 13, true);
}

const outPath = path.resolve(__dirname, "results_review_Week6.pptx");
pres.writeFile({ fileName: outPath }).then(() => console.log("PPTX written to " + outPath));
