// Q-Sentinel Mesh — Business Slides (3 pages)
// Run: node create_business_slides.js

const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Q-Sentinel Mesh — Business Case";

const C = {
  bgDark:  "0f0a14",
  bgCard:  "1e1128",
  card:    "271535",
  cardAlt: "1a0e24",
  pink:    "c25b86",
  cyan:    "5bc4c2",
  green:   "4ec98a",
  yellow:  "f0c060",
  white:   "ffffff",
  muted:   "9b85ac",
  dim:     "5a4a6a",
};

// ── helpers ─────────────────────────────────────────────────────────────────

function sectionLabel(sl, text, x, y) {
  sl.addText(text.toUpperCase(), {
    x, y, w: 4, h: 0.22,
    fontSize: 8.5, fontFace: "Calibri", bold: true,
    color: C.pink, charSpacing: 2.5,
  });
}

function card(sl, x, y, w, h, accent) {
  sl.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h,
    fill: { color: C.card },
    line: { color: accent || C.dim, width: 0.6 },
    rectRadius: 0.14,
    shadow: { type: "outer", blur: 8, offset: 2, angle: 45, color: "000000", opacity: 0.4 },
  });
}

function accentBar(sl, x, y, color) {
  sl.addShape(pres.shapes.RECTANGLE, {
    x, y, w: 0.06, h: 0.55,
    fill: { color }, line: { color, width: 0 },
  });
}

function slideHeader(sl, title, subtitle) {
  sl.background = { color: C.bgDark };

  // top accent line
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 13.33, h: 0.045,
    fill: { color: C.pink }, line: { color: C.pink, width: 0 },
  });

  sl.addText(title, {
    x: 0.5, y: 0.2, w: 8, h: 0.55,
    fontSize: 26, fontFace: "Georgia", bold: true, color: C.white,
  });
  if (subtitle) {
    sl.addText(subtitle, {
      x: 0.5, y: 0.72, w: 9, h: 0.28,
      fontSize: 12, fontFace: "Calibri", color: C.muted,
    });
  }

  // separator
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.08, w: 12.33, h: 0.018,
    fill: { color: C.dim }, line: { color: C.dim, width: 0 },
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 1 — MARKET OPPORTUNITY (TAM / SAM / SOM)
// ════════════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  slideHeader(sl, "Market Opportunity", "Global neuro-AI is a $500M+ market — Southeast Asia is underserved and ready");

  // ── Funnel circles ────────────────────────────────────────────────────────
  const circles = [
    { label: "TAM", sub: "Global ICH / Neuro-AI", value: "$500M", color: C.pink,  cx: 2.2, r: 1.55 },
    { label: "SAM", sub: "SEA Hospitals with CT", value: "$60M",  color: C.cyan,  cx: 5.9, r: 1.15 },
    { label: "SOM", sub: "Thailand — Year 1-2",   value: "$320K", color: C.green, cx: 8.9, r: 0.75 },
  ];

  circles.forEach(({ label, sub, value, color, cx, r }) => {
    // outer glow ring
    sl.addShape(pres.shapes.OVAL, {
      x: cx - r - 0.1, y: 2.5 - r - 0.1, w: (r + 0.1) * 2, h: (r + 0.1) * 2,
      fill: { color, alpha: 8 }, line: { color, width: 0.5, alpha: 40 },
    });
    // main circle
    sl.addShape(pres.shapes.OVAL, {
      x: cx - r, y: 2.5 - r, w: r * 2, h: r * 2,
      fill: { color, alpha: 15 }, line: { color, width: 1.5 },
    });
    // label
    sl.addText(label, {
      x: cx - r, y: 2.5 - 0.45, w: r * 2, h: 0.38,
      fontSize: label === "TAM" ? 22 : label === "SAM" ? 18 : 15,
      fontFace: "Georgia", bold: true, color, align: "center",
    });
    // value
    sl.addText(value, {
      x: cx - r, y: 2.5 - 0.1, w: r * 2, h: 0.38,
      fontSize: label === "TAM" ? 15 : label === "SAM" ? 13 : 12,
      fontFace: "Calibri", bold: true, color: C.white, align: "center",
    });
    // sub
    sl.addText(sub, {
      x: cx - 1.5, y: 2.5 + r + 0.12, w: 3, h: 0.32,
      fontSize: 9.5, fontFace: "Calibri", color: C.muted, align: "center",
    });
  });

  // ── Right stats panel ─────────────────────────────────────────────────────
  const stats = [
    { icon: "🏥", val: "800+",  desc: "Thai hospitals with CT scanners" },
    { icon: "⏱",  val: "< 1hr", desc: "ICH treatment window to survive" },
    { icon: "👨‍⚕️", val: "1:12",  desc: "Radiologist-to-rural-hospital ratio" },
    { icon: "📈",  val: "28%",   desc: "Neuro-AI CAGR through 2030" },
  ];

  card(sl, 10.3, 1.25, 2.65, 5.6, C.dim);
  sectionLabel(sl, "Why Now", 10.5, 1.3);

  stats.forEach(({ icon, val, desc }, i) => {
    const sy = 1.65 + i * 1.22;
    sl.addText(icon, {
      x: 10.45, y: sy, w: 0.4, h: 0.35, fontSize: 16, align: "center",
    });
    sl.addText(val, {
      x: 10.88, y: sy, w: 1.9, h: 0.38,
      fontSize: 18, fontFace: "Georgia", bold: true, color: C.yellow,
    });
    sl.addText(desc, {
      x: 10.45, y: sy + 0.35, w: 2.35, h: 0.45,
      fontSize: 9, fontFace: "Calibri", color: C.muted,
    });
  });

  // ── SOM detail box ────────────────────────────────────────────────────────
  card(sl, 0.4, 5.6, 9.6, 1.5, C.green);
  sl.addText("SOM Calculation  ·  80 hospitals × 12,000 THB/mo × 12 = 11.5M THB/year (~$320K)", {
    x: 0.6, y: 5.72, w: 9.2, h: 0.32,
    fontSize: 10, fontFace: "Calibri", bold: true, color: C.green,
  });
  sl.addText("Break-even at just 9 hospitals  ·  Target: 20 hospitals by end of Year 1", {
    x: 0.6, y: 6.05, w: 9.2, h: 0.32,
    fontSize: 10, fontFace: "Calibri", color: C.white,
  });
  sl.addText("Expand to SEA in Year 3 — Vietnam, Indonesia, Philippines add 10× SAM", {
    x: 0.6, y: 6.35, w: 9.2, h: 0.32,
    fontSize: 10, fontFace: "Calibri", color: C.muted,
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 2 — BUSINESS MODEL
// ════════════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  slideHeader(sl, "Business Model", "Four revenue streams — hospital SaaS is the core engine");

  // ── Revenue stream cards (top row) ────────────────────────────────────────
  const streams = [
    {
      icon: "📦",
      name: "SaaS Subscription",
      tag: "CORE",
      tagColor: C.pink,
      lines: ["Monthly / annual plan", "per hospital or hospital group", "5K – 80K THB / month"],
      color: C.pink,
    },
    {
      icon: "🔬",
      name: "Per-Scan API",
      tag: "USAGE",
      tagColor: C.cyan,
      lines: ["Pay-as-you-go", "Private clinics & telemedicine", "15 – 50 THB / scan"],
      color: C.cyan,
    },
    {
      icon: "🌐",
      name: "FL Node License",
      tag: "NETWORK",
      tagColor: C.yellow,
      lines: ["Hospital-group FL participation", "Shared model improvement", "100K THB / year / node"],
      color: C.yellow,
    },
    {
      icon: "🏢",
      name: "White-label / OEM",
      tag: "ENTERPRISE",
      tagColor: C.green,
      lines: ["License to GE, Siemens, etc.", "Integrate into PACS systems", "Negotiated deal"],
      color: C.green,
    },
  ];

  streams.forEach(({ icon, name, tag, tagColor, lines, color }, i) => {
    const x = 0.38 + i * 3.2;
    card(sl, x, 1.22, 3.0, 2.9, color);
    accentBar(sl, x, 1.22, color);

    // icon + name
    sl.addText(icon + "  " + name, {
      x: x + 0.18, y: 1.28, w: 2.75, h: 0.42,
      fontSize: 12.5, fontFace: "Calibri", bold: true, color: C.white,
    });

    // tag pill
    sl.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: x + 0.18, y: 1.72, w: 1.1, h: 0.24,
      fill: { color: tagColor, alpha: 22 }, line: { color: tagColor, width: 0.5 },
      rectRadius: 0.08,
    });
    sl.addText(tag, {
      x: x + 0.18, y: 1.72, w: 1.1, h: 0.24,
      fontSize: 8, fontFace: "Calibri", bold: true, color: tagColor,
      align: "center", valign: "middle",
    });

    // bullet lines
    lines.forEach((line, j) => {
      sl.addText("· " + line, {
        x: x + 0.2, y: 2.08 + j * 0.32, w: 2.65, h: 0.3,
        fontSize: 10, fontFace: "Calibri", color: C.muted,
      });
    });
  });

  // ── Pricing tiers table ───────────────────────────────────────────────────
  sectionLabel(sl, "Pricing Tiers", 0.4, 4.28);

  const tiers = [
    { name: "Starter",  who: "รพช. ชนบท",   price: "5,000 THB/mo",  limit: "≤50 scans",   color: C.muted  },
    { name: "Growth",   who: "รพท.",          price: "15,000 THB/mo", limit: "≤200 scans",  color: C.cyan   },
    { name: "Pro",      who: "รพศ. / รพม.",   price: "35,000 THB/mo", limit: "Unlimited",   color: C.pink   },
    { name: "Network",  who: "กลุ่มโรงพยาบาล", price: "80,000 THB/mo", limit: "5 nodes + FL", color: C.yellow },
  ];

  card(sl, 0.38, 4.55, 9.6, 2.6, C.dim);

  // table header
  ["Tier", "Target", "Price", "Scan Limit"].forEach((h, i) => {
    const xs = [0.58, 2.38, 5.28, 7.68];
    sl.addText(h, {
      x: xs[i], y: 4.65, w: 1.8, h: 0.28,
      fontSize: 9.5, fontFace: "Calibri", bold: true, color: C.pink, charSpacing: 1,
    });
  });

  tiers.forEach(({ name, who, price, limit, color }, i) => {
    const ry = 5.05 + i * 0.5;
    // row bg alt
    if (i % 2 === 0) {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 0.42, y: ry - 0.04, w: 9.5, h: 0.44,
        fill: { color: C.cardAlt, alpha: 60 }, line: { color: C.dim, width: 0 },
      });
    }
    // dot
    sl.addShape(pres.shapes.OVAL, {
      x: 0.6, y: ry + 0.12, w: 0.14, h: 0.14,
      fill: { color }, line: { color, width: 0 },
    });
    sl.addText(name,  { x: 0.82, y: ry, w: 1.5,  h: 0.38, fontSize: 11, fontFace: "Calibri", bold: true,  color: C.white });
    sl.addText(who,   { x: 2.38, y: ry, w: 2.7,  h: 0.38, fontSize: 10, fontFace: "Calibri",              color: C.muted });
    sl.addText(price, { x: 5.28, y: ry, w: 2.2,  h: 0.38, fontSize: 11, fontFace: "Calibri", bold: true,  color });
    sl.addText(limit, { x: 7.68, y: ry, w: 2.1,  h: 0.38, fontSize: 10, fontFace: "Calibri",              color: C.muted });
  });

  // ── Right value prop ──────────────────────────────────────────────────────
  card(sl, 10.3, 1.22, 2.65, 5.93, C.dim);
  sectionLabel(sl, "Key Moats", 10.5, 1.3);

  const moats = [
    { icon: "🔐", title: "PDPA Built-in",    desc: "FL = no patient data leaves hospital" },
    { icon: "⚛️",  title: "Quantum Edge",    desc: "First quantum ICH AI in SEA" },
    { icon: "🌏",  title: "AWS Thailand",    desc: "Data residency, sub-50ms latency" },
    { icon: "🔄",  title: "Network Effect",  desc: "More hospitals = better shared model" },
  ];

  moats.forEach(({ icon, title, desc }, i) => {
    const my = 1.65 + i * 1.3;
    sl.addText(icon, { x: 10.42, y: my, w: 0.4, h: 0.35, fontSize: 16, align: "center" });
    sl.addText(title, {
      x: 10.88, y: my, w: 1.9, h: 0.32,
      fontSize: 11.5, fontFace: "Calibri", bold: true, color: C.white,
    });
    sl.addText(desc, {
      x: 10.45, y: my + 0.32, w: 2.35, h: 0.55,
      fontSize: 9, fontFace: "Calibri", color: C.muted,
    });
  });
}

// ════════════════════════════════════════════════════════════════════════════
// SLIDE 3 — COST STRUCTURE & ROI
// ════════════════════════════════════════════════════════════════════════════
{
  const sl = pres.addSlide();
  slideHeader(sl, "Cost Structure & ROI", "Open-source stack + AWS Thailand = 95%+ gross margin from day one");

  // ── Cost breakdown (left column) ──────────────────────────────────────────
  sectionLabel(sl, "Monthly Cost (Phase 1 — MVP)", 0.4, 1.2);

  const costs = [
    { name: "EC2 t3.medium  (Dashboard + FL Server)",  val: "$33",   note: "ap-southeast-7",  color: C.cyan   },
    { name: "S3 Storage  (weights + cache ~500GB)",    val: "$12",   note: "ap-southeast-7",  color: C.cyan   },
    { name: "Data Transfer  (~100GB/mo)",               val: "$9",    note: "AWS",             color: C.cyan   },
    { name: "HuggingFace Pro  (model hub)",             val: "$9",    note: "AI tooling",      color: C.pink   },
    { name: "PennyLane  (quantum sim)",                 val: "FREE",  note: "Open-source",     color: C.green  },
    { name: "Flower FL framework",                      val: "FREE",  note: "Open-source",     color: C.green  },
    { name: "PyTorch / timm / scikit-learn",            val: "FREE",  note: "Open-source",     color: C.green  },
  ];

  card(sl, 0.38, 1.42, 5.8, 4.6, C.dim);

  costs.forEach(({ name, val, note, color }, i) => {
    const cy = 1.6 + i * 0.56;
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.42, y: cy, w: 5.72, h: 0.48,
      fill: { color: i % 2 === 0 ? C.cardAlt : C.bgDark, alpha: 50 },
      line: { color: C.dim, width: 0 },
    });
    sl.addText(name, {
      x: 0.55, y: cy + 0.06, w: 3.6, h: 0.34,
      fontSize: 9.5, fontFace: "Calibri", color: C.white,
    });
    sl.addText(val, {
      x: 4.18, y: cy + 0.05, w: 0.9, h: 0.36,
      fontSize: 11, fontFace: "Calibri", bold: true, color,
      align: "right",
    });
    sl.addText(note, {
      x: 5.12, y: cy + 0.08, w: 0.95, h: 0.3,
      fontSize: 8, fontFace: "Calibri", color: C.dim, align: "right",
    });
  });

  // total bar
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.42, y: 5.55, w: 5.72, h: 0.42,
    fill: { color: C.pink, alpha: 18 }, line: { color: C.pink, width: 0.6 },
  });
  sl.addText("Total Infrastructure + Tools / month", {
    x: 0.58, y: 5.6, w: 3.5, h: 0.32,
    fontSize: 10.5, fontFace: "Calibri", bold: true, color: C.white,
  });
  sl.addText("~$63 / mo", {
    x: 4.0, y: 5.58, w: 1.9, h: 0.36,
    fontSize: 14, fontFace: "Georgia", bold: true, color: C.pink, align: "right",
  });
  sl.addText("(~2,200 THB)", {
    x: 4.0, y: 5.81, w: 2.05, h: 0.2,
    fontSize: 8.5, fontFace: "Calibri", color: C.muted, align: "right",
  });

  // ── Unit economics (middle column) ────────────────────────────────────────
  sectionLabel(sl, "Unit Economics · Per Hospital", 6.55, 1.2);

  const units = [
    { label: "Revenue",          val: "15,000 THB/mo", color: C.green  },
    { label: "Infra cost share", val: "~150 THB/mo",   color: C.pink   },
    { label: "Gross Margin",     val: "99%",           color: C.yellow },
    { label: "Payback period",   val: "< 1 month",     color: C.cyan   },
  ];

  card(sl, 6.5, 1.42, 3.4, 2.55, C.dim);

  units.forEach(({ label, val, color }, i) => {
    const uy = 1.62 + i * 0.57;
    accentBar(sl, 6.52, uy + 0.04, color);
    sl.addText(label, {
      x: 6.75, y: uy + 0.02, w: 2.0, h: 0.28,
      fontSize: 9.5, fontFace: "Calibri", color: C.muted,
    });
    sl.addText(val, {
      x: 6.75, y: uy + 0.28, w: 2.9, h: 0.3,
      fontSize: 13, fontFace: "Georgia", bold: true, color,
    });
  });

  // break-even callout
  card(sl, 6.5, 4.12, 3.4, 1.1, C.green);
  sl.addText("🎯  Break-even", {
    x: 6.65, y: 4.2, w: 3.1, h: 0.32,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.green,
  });
  sl.addText("Only 9 hospitals needed", {
    x: 6.65, y: 4.5, w: 3.1, h: 0.28,
    fontSize: 10.5, fontFace: "Georgia", bold: true, color: C.white,
  });
  sl.addText("to cover all operating costs", {
    x: 6.65, y: 4.76, w: 3.1, h: 0.28,
    fontSize: 10, fontFace: "Calibri", color: C.muted,
  });

  // ── 2-Year projection bars (right column) ─────────────────────────────────
  sectionLabel(sl, "2-Year Projection (THB)", 10.2, 1.2);

  card(sl, 10.15, 1.42, 2.8, 4.6, C.dim);

  const years = [
    { label: "Year 1", rph: 20, rev: "3.6M",  cost: "1.6M", profit: "2.0M",  bar: 0.38 },
    { label: "Year 2", rph: 80, rev: "14.4M", cost: "3.0M", profit: "11.4M", bar: 1.0  },
  ];

  years.forEach(({ label, rph, rev, cost, profit, bar }, i) => {
    const base = 1.75 + i * 2.1;

    sl.addText(label + "  (" + rph + " hospitals)", {
      x: 10.28, y: base, w: 2.55, h: 0.3,
      fontSize: 10.5, fontFace: "Calibri", bold: true, color: C.white,
    });

    // bar chart (revenue / cost / profit)
    const barData = [
      { label: "Revenue", val: rev,    w: bar * 2.0, color: C.cyan  },
      { label: "Cost",    val: cost,   w: bar * 0.6, color: C.pink  },
      { label: "Profit",  val: profit, w: bar * 1.4, color: C.green },
    ];

    barData.forEach(({ label: bl, val, w, color }, j) => {
      const by = base + 0.38 + j * 0.48;
      sl.addText(bl, {
        x: 10.28, y: by + 0.04, w: 0.85, h: 0.3,
        fontSize: 8.5, fontFace: "Calibri", color: C.muted,
      });
      // bar track
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 11.12, y: by + 0.07, w: 1.55, h: 0.22,
        fill: { color: C.cardAlt }, line: { color: C.dim, width: 0 },
      });
      // filled bar
      sl.addShape(pres.shapes.RECTANGLE, {
        x: 11.12, y: by + 0.07, w: Math.min(w, 1.55), h: 0.22,
        fill: { color, alpha: 80 }, line: { color, width: 0 },
      });
      sl.addText(val, {
        x: 12.7, y: by + 0.04, w: 0.9, h: 0.3,
        fontSize: 9.5, fontFace: "Calibri", bold: true, color, align: "right",
      });
    });
  });

  // ROI summary box at bottom
  card(sl, 0.38, 6.1, 12.57, 1.12, C.yellow);
  sl.addText("💡", { x: 0.5, y: 6.22, w: 0.4, h: 0.5, fontSize: 20, align: "center" });

  const roiPoints = [
    "AWS Thailand = data never leaves Thailand  (PDPA compliant by architecture)",
    "Open-source AI stack = near-zero licensing cost  (99%+ gross margin)",
    "License / month ≈ 1 hour of a radiologist salary — but covers 24/7 AI assistance",
  ];

  roiPoints.forEach((pt, i) => {
    sl.addText("· " + pt, {
      x: 0.98, y: 6.16 + i * 0.33, w: 11.8, h: 0.3,
      fontSize: 9.5, fontFace: "Calibri", color: i === 2 ? C.yellow : C.white,
    });
  });
}

// ── Export ────────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: "QSentinel_Business_Slides.pptx" })
  .then(() => console.log("✅  QSentinel_Business_Slides.pptx created"))
  .catch(console.error);
