// Q-Sentinel Mesh Pitch Deck Generator
// Uses pptxgenjs to create a professional 10-slide pitch deck

const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3" x 7.5"
pres.title = "Q-Sentinel Mesh — CEDT Hackathon 2026";
pres.author = "Q-Sentinel Mesh Team";

// Color palette (NO # prefix — pptxgenjs requirement)
const C = {
  bgDark: "1a0a12",
  bgLight: "2a1020",
  pink: "c25b86",
  green: "4c8f6b",
  cyan: "5bc4c2",
  white: "ffffff",
  muted: "b89aa8",
  card: "2d1422",
  darkAlt: "221018",
};

// ─────────────────────────────────────────────────────────
// SLIDE 1 — TITLE
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  // Main title
  sl.addText("Q-Sentinel Mesh", {
    x: 0, y: 1.3, w: 13.33, h: 1.1,
    fontSize: 54, fontFace: "Georgia", bold: true,
    color: C.white, align: "center",
  });

  // Decorative line centered between title and subtitle
  sl.addShape(pres.shapes.RECTANGLE, {
    x: (13.33 - 3) / 2, y: 2.55, w: 3, h: 0.03,
    fill: { color: C.pink }, line: { color: C.pink, width: 0 },
  });

  // Subtitle line 1
  sl.addText("AI-Powered Brain Hemorrhage Detection", {
    x: 0, y: 2.7, w: 13.33, h: 0.5,
    fontSize: 22, fontFace: "Calibri",
    color: C.muted, align: "center",
  });

  // Subtitle line 2
  sl.addText("Federated  ·  Quantum  ·  Post-Quantum Secure", {
    x: 0, y: 3.25, w: 13.33, h: 0.4,
    fontSize: 18, fontFace: "Calibri",
    color: C.pink, align: "center",
  });

  // 3 tech pills bottom row
  const pills = ["EfficientNet-B4", "ML-KEM-512", "Flower FL"];
  const pillW = 1.8;
  const pillH = 0.35;
  const totalPillW = pills.length * pillW + (pills.length - 1) * 0.25;
  const pillStartX = (13.33 - totalPillW) / 2;
  pills.forEach((label, i) => {
    const px = pillStartX + i * (pillW + 0.25);
    sl.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: px, y: 4.1, w: pillW, h: pillH,
      fill: { color: C.card }, line: { color: C.pink, width: 0.5 },
      rectRadius: 0.12,
    });
    sl.addText(label, {
      x: px, y: 4.1, w: pillW, h: pillH,
      fontSize: 11, fontFace: "Calibri", color: C.white,
      align: "center", valign: "middle",
    });
  });

  // Bottom text
  sl.addText("CEDT Hackathon 2026", {
    x: 0, y: 6.9, w: 13.33, h: 0.35,
    fontSize: 14, fontFace: "Calibri",
    color: C.muted, align: "center",
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 2 — THE PROBLEM
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  // Eyebrow
  sl.addText("THE PROBLEM", {
    x: 0.5, y: 0.25, w: 5, h: 0.3,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.pink,
  });

  // Title
  sl.addText("700+ Hospitals. No Radiologist.", {
    x: 0.5, y: 0.7, w: 12, h: 0.7,
    fontSize: 40, fontFace: "Georgia", bold: true, color: C.white,
  });

  // Subtitle
  sl.addText("Brain hemorrhage kills within hours. Rural Thailand has no one to read the scan.", {
    x: 0.5, y: 1.5, w: 12, h: 0.5,
    fontSize: 16, fontFace: "Calibri", color: C.muted,
  });

  // Stat cards
  const cards = [
    { x: 0.3, num: "2–8 hrs", label: "Time to CT diagnosis", sub: "in rural hospitals" },
    { x: 4.4, num: "700+", label: "Hospitals", sub: "without on-site radiologist" },
    { x: 8.5, num: "~10%", label: "Mortality increase", sub: "per 10-min delay in treatment" },
  ];
  cards.forEach(({ x, num, label, sub }) => {
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.4, w: 3.8, h: 2.8,
      fill: { color: C.card }, line: { color: C.pink, width: 0.5 },
    });
    sl.addText(num, {
      x, y: 2.55, w: 3.8, h: 0.9,
      fontSize: 48, fontFace: "Georgia", bold: true, color: C.pink, align: "center",
    });
    sl.addText(label, {
      x, y: 3.5, w: 3.8, h: 0.4,
      fontSize: 13, fontFace: "Calibri", color: C.white, align: "center",
    });
    sl.addText(sub, {
      x, y: 3.95, w: 3.8, h: 0.35,
      fontSize: 11, fontFace: "Calibri", color: C.muted, align: "center",
    });
  });

  // Bottom bar
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 6.9, w: 13.33, h: 0.45,
    fill: { color: C.pink }, line: { color: C.pink, width: 0 },
  });
  sl.addText("Brain hemorrhage = medical emergency. Every minute counts.", {
    x: 0, y: 6.9, w: 13.33, h: 0.45,
    fontSize: 13, fontFace: "Calibri", bold: true, color: C.white, align: "center", valign: "middle",
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 3 — SOLUTION
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  sl.addText("OUR SOLUTION", {
    x: 0.5, y: 0.25, w: 5, h: 0.3,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.pink,
  });
  sl.addText("Q-Sentinel Mesh", {
    x: 0.5, y: 0.7, w: 12, h: 0.7,
    fontSize: 40, fontFace: "Georgia", bold: true, color: C.white,
  });
  sl.addText("5 technologies. 1 unified system.", {
    x: 0.5, y: 1.4, w: 10, h: 0.45,
    fontSize: 18, fontFace: "Calibri", color: C.muted,
  });

  const pillars = [
    { icon: "Brain", title: "EfficientNet-B4", body: "CT scan feature\nextraction\n1,792 features" },
    { icon: "Atom", title: "Quantum VQC", body: "4-qubit circuit\nStrongly Entangling\n24 parameters" },
    { icon: "Globe", title: "Federated\nLearning", body: "3 hospital nodes\nFedAvg aggregation\nFlower 1.9.0" },
    { icon: "Lock", title: "ML-KEM-512", body: "NIST FIPS 203\nPost-quantum KEM\nAES-256-GCM" },
    { icon: "Flash", title: "<5 min", body: "vs 2-8 hrs today\nFull diagnosis\n+ heatmap", titleColor: C.green },
  ];
  const xPositions = [0.3, 2.75, 5.2, 7.65, 10.1];
  const iconChars = ["🧠", "⚛", "🌐", "🔒", "⚡"];
  pillars.forEach((p, i) => {
    const px = xPositions[i];
    sl.addShape(pres.shapes.RECTANGLE, {
      x: px, y: 2.2, w: 2.3, h: 3.6,
      fill: { color: C.card }, line: { color: C.pink, width: 0.5 },
    });
    sl.addText(iconChars[i], {
      x: px, y: 2.35, w: 2.3, h: 0.55,
      fontSize: 28, align: "center",
    });
    sl.addText(p.title, {
      x: px + 0.05, y: 3.0, w: 2.2, h: 0.55,
      fontSize: 14, fontFace: "Calibri", bold: true,
      color: p.titleColor || C.white, align: "center",
    });
    sl.addText(p.body, {
      x: px + 0.05, y: 3.6, w: 2.2, h: 1.8,
      fontSize: 12, fontFace: "Calibri", color: C.muted, align: "center",
    });
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 4 — HOW IT WORKS
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  sl.addText("WORKFLOW", {
    x: 0.5, y: 0.2, w: 4, h: 0.3,
    fontSize: 11, fontFace: "Calibri", color: C.pink,
  });
  sl.addText("How It Works", {
    x: 0.5, y: 0.6, w: 7, h: 0.7,
    fontSize: 40, fontFace: "Georgia", bold: true, color: C.white,
  });

  // Note banner
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 7.8, y: 0.55, w: 5.2, h: 0.4,
    fill: { color: C.green, transparency: 80 },
    line: { color: C.green, width: 0.5 },
  });
  sl.addText("Raw CT data NEVER leaves the hospital", {
    x: 7.8, y: 0.55, w: 5.2, h: 0.4,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.green,
    align: "center", valign: "middle",
  });

  // Row 1 flow boxes
  const row1 = [
    { num: "1", title: "CT Scan Upload", body: "DICOM/NIfTI\n3-channel windowing", numFill: C.pink },
    { num: "2", title: "EfficientNet-B4", body: "Extracts 1,792\nfeatures from CT", numFill: C.pink },
    { num: "3", title: "Quantum VQC", body: "4-qubit circuit\nrefines to 4 values", numFill: C.pink },
  ];
  const row1X = [0.3, 4.6, 8.9];

  row1.forEach((box, i) => {
    const bx = row1X[i];
    sl.addShape(pres.shapes.RECTANGLE, {
      x: bx, y: 1.6, w: 3.8, h: 1.6,
      fill: { color: C.card }, line: { color: C.pink, width: 0.5 },
    });
    // Number circle
    sl.addShape(pres.shapes.OVAL, {
      x: bx + 0.15, y: 1.7, w: 0.38, h: 0.38,
      fill: { color: box.numFill }, line: { color: box.numFill, width: 0 },
    });
    sl.addText(box.num, {
      x: bx + 0.15, y: 1.7, w: 0.38, h: 0.38,
      fontSize: 12, fontFace: "Calibri", bold: true, color: C.white,
      align: "center", valign: "middle",
    });
    sl.addText(box.title, {
      x: bx + 0.6, y: 1.72, w: 3.0, h: 0.4,
      fontSize: 13, fontFace: "Calibri", bold: true, color: C.white,
    });
    sl.addText(box.body, {
      x: bx + 0.15, y: 2.2, w: 3.5, h: 0.75,
      fontSize: 11, fontFace: "Calibri", color: C.muted,
    });
    // Arrow to next (not after last)
    if (i < 2) {
      sl.addShape(pres.shapes.LINE, {
        x: bx + 3.8, y: 2.4, w: 0.8, h: 0,
        line: { color: C.pink, width: 1.5 },
      });
      // Arrowhead
      sl.addText("▶", {
        x: bx + 4.3, y: 2.28, w: 0.3, h: 0.3,
        fontSize: 10, color: C.pink, align: "center",
      });
    }
  });

  // Down arrow between rows
  sl.addShape(pres.shapes.LINE, {
    x: 10.8, y: 3.2, w: 0, h: 0.3,
    line: { color: C.pink, width: 1.5 },
  });
  sl.addText("▼", {
    x: 10.65, y: 3.45, w: 0.3, h: 0.3,
    fontSize: 10, color: C.pink, align: "center",
  });

  // Row 2 flow boxes
  const row2 = [
    { num: "4", title: "Diagnosis Output", body: "6 hemorrhage probs\n+ HiResCAM heatmap", numFill: C.green },
    { num: "5", title: "PQC Encryption", body: "ML-KEM-512\nweights encrypted", numFill: C.pink },
    { num: "6", title: "FedAvg Aggregation", body: "Global model\nimproves each round", numFill: C.pink },
  ];
  const row2X = [0.3, 4.6, 8.9];

  row2.forEach((box, i) => {
    const bx = row2X[i];
    sl.addShape(pres.shapes.RECTANGLE, {
      x: bx, y: 3.5, w: 3.8, h: 1.6,
      fill: { color: C.card }, line: { color: C.pink, width: 0.5 },
    });
    // Number circle
    sl.addShape(pres.shapes.OVAL, {
      x: bx + 0.15, y: 3.6, w: 0.38, h: 0.38,
      fill: { color: box.numFill }, line: { color: box.numFill, width: 0 },
    });
    sl.addText(box.num, {
      x: bx + 0.15, y: 3.6, w: 0.38, h: 0.38,
      fontSize: 12, fontFace: "Calibri", bold: true, color: C.white,
      align: "center", valign: "middle",
    });
    sl.addText(box.title, {
      x: bx + 0.6, y: 3.62, w: 3.0, h: 0.4,
      fontSize: 13, fontFace: "Calibri", bold: true, color: C.white,
    });
    sl.addText(box.body, {
      x: bx + 0.15, y: 4.1, w: 3.5, h: 0.75,
      fontSize: 11, fontFace: "Calibri", color: C.muted,
    });
    if (i < 2) {
      sl.addShape(pres.shapes.LINE, {
        x: bx + 3.8, y: 4.3, w: 0.8, h: 0,
        line: { color: C.pink, width: 1.5 },
      });
      sl.addText("▶", {
        x: bx + 4.3, y: 4.18, w: 0.3, h: 0.3,
        fontSize: 10, color: C.pink, align: "center",
      });
    }
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 5 — RESULTS
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  sl.addText("PERFORMANCE", {
    x: 0.5, y: 0.25, w: 5, h: 0.3,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.pink,
  });
  sl.addText("Real Results", {
    x: 0.5, y: 0.65, w: 8, h: 0.7,
    fontSize: 40, fontFace: "Georgia", bold: true, color: C.white,
  });

  const metrics = [
    { x: 0.3, num: "93.6%", numColor: C.pink, label: "Federated AUC", sub: "Hybrid CNN+VQC model" },
    { x: 3.4, num: "+8.2%", numColor: C.green, label: "AUC Improvement", sub: "vs isolated baseline" },
    { x: 6.5, num: "3R / 2N", numColor: C.cyan, label: "FL Rounds / Nodes", sub: "PQC encrypted all rounds" },
    { x: 9.6, num: "<5 min", numColor: C.green, label: "Diagnosis Time", sub: "vs 2-8 hrs traditional" },
  ];
  metrics.forEach(({ x, num, numColor, label, sub }) => {
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.5, w: 2.9, h: 2.2,
      fill: { color: C.card }, line: { color: C.pink, width: 0.5 },
    });
    sl.addText(num, {
      x, y: 1.65, w: 2.9, h: 0.75,
      fontSize: 44, fontFace: "Georgia", bold: true, color: numColor, align: "center",
    });
    sl.addText(label, {
      x, y: 2.45, w: 2.9, h: 0.38,
      fontSize: 13, fontFace: "Calibri", color: C.white, align: "center",
    });
    sl.addText(sub, {
      x, y: 2.88, w: 2.9, h: 0.35,
      fontSize: 11, fontFace: "Calibri", color: C.muted, align: "center",
    });
  });

  // Quote box
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.0, w: 12.3, h: 0.7,
    fill: { color: C.card }, line: { color: C.pink, width: 0.3 },
  });
  sl.addText("\u201cModel improves every federated round without sharing patient data\u201d", {
    x: 0.5, y: 4.0, w: 12.3, h: 0.7,
    fontSize: 15, fontFace: "Calibri", italic: true, color: C.muted,
    align: "center", valign: "middle",
  });

  // Second visual: a simple performance comparison row
  sl.addText("Round-by-Round AUC Improvement", {
    x: 0.5, y: 5.0, w: 12, h: 0.4,
    fontSize: 14, fontFace: "Calibri", bold: true, color: C.white,
  });

  const rounds = [
    { label: "Baseline", val: 85.4, color: C.muted },
    { label: "Round 1", val: 89.1, color: C.pink },
    { label: "Round 2", val: 91.8, color: C.pink },
    { label: "Round 3", val: 93.6, color: C.green },
  ];
  const barMaxW = 8.0;
  const barMaxVal = 100;
  rounds.forEach((r, i) => {
    const bx = 0.5;
    const by = 5.6 + i * 0.38;
    const barW = (r.val / barMaxVal) * barMaxW;
    sl.addText(r.label, {
      x: bx, y: by, w: 1.3, h: 0.3,
      fontSize: 11, fontFace: "Calibri", color: C.muted, valign: "middle",
    });
    sl.addShape(pres.shapes.RECTANGLE, {
      x: bx + 1.4, y: by + 0.03, w: barMaxW, h: 0.22,
      fill: { color: C.card }, line: { color: C.card, width: 0 },
    });
    sl.addShape(pres.shapes.RECTANGLE, {
      x: bx + 1.4, y: by + 0.03, w: barW, h: 0.22,
      fill: { color: r.color }, line: { color: r.color, width: 0 },
    });
    sl.addText(r.val + "%", {
      x: bx + 1.4 + barW + 0.1, y: by, w: 0.8, h: 0.3,
      fontSize: 11, fontFace: "Calibri", color: C.white, valign: "middle",
    });
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 6 — SECURITY
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  sl.addText("SECURITY LAYER", {
    x: 0.5, y: 0.2, w: 5, h: 0.3,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.pink,
  });
  sl.addText("Post-Quantum Security by Design", {
    x: 0.5, y: 0.65, w: 12.5, h: 0.7,
    fontSize: 36, fontFace: "Georgia", bold: true, color: C.white,
  });
  sl.addText("Resistant to quantum computer attacks. Compliant with NIST FIPS 203.", {
    x: 0.5, y: 1.3, w: 12, h: 0.45,
    fontSize: 15, fontFace: "Calibri", color: C.muted,
  });

  // Encryption pipeline
  const pipelineBoxes = [
    { label: "Hospital\nWeights", fill: C.card, border: C.muted, bold: false },
    { label: "ML-KEM-512\nencaps(pk)", fill: C.card, border: C.pink, bold: true, tinted: true },
    { label: "HKDF-SHA256\nkey derive", fill: C.card, border: C.muted, bold: false },
    { label: "AES-256-GCM\nencrypt", fill: C.card, border: C.pink, bold: true, tinted: true },
    { label: "Server\ndecrypts", fill: C.card, border: C.muted, bold: false },
    { label: "FedAvg\naggregate", fill: C.card, border: C.green, bold: true, greenTinted: true },
  ];
  const pipeX = [0.3, 2.35, 4.4, 6.45, 8.5, 10.55];

  pipelineBoxes.forEach((box, i) => {
    const bx = pipeX[i];
    const fillColor = box.tinted ? "3d1a2c" : (box.greenTinted ? "1a3d2c" : C.card);
    const borderColor = box.border;
    sl.addShape(pres.shapes.RECTANGLE, {
      x: bx, y: 2.2, w: 1.8, h: 1.0,
      fill: { color: fillColor }, line: { color: borderColor, width: 1 },
    });
    sl.addText(box.label, {
      x: bx, y: 2.2, w: 1.8, h: 1.0,
      fontSize: 11, fontFace: "Calibri", bold: box.bold, color: C.white,
      align: "center", valign: "middle",
    });
    if (i < 5) {
      sl.addText("→", {
        x: bx + 1.82, y: 2.58, w: 0.25, h: 0.3,
        fontSize: 14, color: C.muted, align: "center",
      });
    }
  });

  // 3 fact boxes
  const facts = [
    { x: 0.3, icon: "🛡", title: "NIST FIPS 203", body: "ML-KEM-512 standardized\nPost-quantum KEM algorithm", titleColor: C.white },
    { x: 4.4, icon: "🔑", title: "768-byte KEM CT", body: "Ciphertext per transmission\nShared secret never sent", titleColor: C.white },
    { x: 8.5, icon: "✓", title: "Authenticated", body: "AES-256-GCM ensures\ntamper-proof delivery", titleColor: C.green },
  ];
  facts.forEach(({ x, icon, title, body, titleColor }) => {
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: 3.6, w: 3.8, h: 1.6,
      fill: { color: C.card }, line: { color: C.pink, width: 0.3 },
    });
    sl.addText(icon, {
      x, y: 3.68, w: 3.8, h: 0.45,
      fontSize: 20, align: "center",
    });
    sl.addText(title, {
      x, y: 4.15, w: 3.8, h: 0.38,
      fontSize: 14, fontFace: "Calibri", bold: true, color: titleColor, align: "center",
    });
    sl.addText(body, {
      x, y: 4.55, w: 3.8, h: 0.55,
      fontSize: 12, fontFace: "Calibri", color: C.muted, align: "center",
    });
  });

  // Bottom tagline
  sl.addText("Quantum-computer resistant. Today.", {
    x: 0, y: 6.75, w: 13.33, h: 0.45,
    fontSize: 16, fontFace: "Georgia", italic: true, color: C.pink, align: "center",
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 7 — MARKET & ROI
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  sl.addText("BUSINESS CASE", {
    x: 0.5, y: 0.2, w: 5, h: 0.3,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.pink,
  });
  sl.addText("The Business Case", {
    x: 0.5, y: 0.65, w: 8, h: 0.7,
    fontSize: 40, fontFace: "Georgia", bold: true, color: C.white,
  });

  // Left column — Market
  sl.addText("Market Opportunity", {
    x: 0.3, y: 1.45, w: 5.8, h: 0.4,
    fontSize: 16, fontFace: "Calibri", bold: true, color: C.pink,
  });

  const marketCards = [
    { y: 1.9, label: "TAM — Global Medical AI 2030", value: "$20.9B", valColor: C.white },
    { y: 3.25, label: "SAM — CT AI in Southeast Asia", value: "$180M/yr", valColor: C.white },
    { y: 4.6, label: "SOM — Thailand Year 1–3", value: "\u0e3f50\u2013200M", valColor: C.green },
  ];
  marketCards.forEach(({ y, label, value, valColor }) => {
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y, w: 5.8, h: 1.2,
      fill: { color: C.card }, line: { color: C.pink, width: 0.3 },
    });
    sl.addText(label, {
      x: 0.5, y: y + 0.12, w: 5.5, h: 0.32,
      fontSize: 12, fontFace: "Calibri", color: C.muted,
    });
    sl.addText(value, {
      x: 0.5, y: y + 0.5, w: 5.5, h: 0.55,
      fontSize: 28, fontFace: "Georgia", bold: true, color: valColor,
    });
  });

  // Vertical divider
  sl.addShape(pres.shapes.LINE, {
    x: 6.4, y: 1.3, w: 0, h: 5.5,
    line: { color: C.pink, width: 1, transparency: 70 },
  });

  // Right column — ROI
  sl.addText("Return on Investment", {
    x: 6.7, y: 1.45, w: 6.0, h: 0.4,
    fontSize: 16, fontFace: "Calibri", bold: true, color: C.pink,
  });

  const roiRows = [
    { y: 2.0, year: "Year 1", detail: "\u0e3f5M rev / \u0e3f7M cost", pct: "\u201328%", pctColor: C.pink },
    { y: 3.0, year: "Year 2", detail: "\u0e3f25M revenue", pct: "+150%", pctColor: C.green },
    { y: 4.0, year: "Year 3", detail: "\u0e3f60M revenue", pct: "+300%", pctColor: C.green },
  ];
  roiRows.forEach(({ y, year, detail, pct, pctColor }) => {
    sl.addText(year, {
      x: 6.7, y, w: 1.5, h: 0.5,
      fontSize: 13, fontFace: "Calibri", bold: true, color: C.white, valign: "middle",
    });
    sl.addText(detail, {
      x: 8.3, y, w: 2.8, h: 0.5,
      fontSize: 13, fontFace: "Calibri", color: C.muted, valign: "middle",
    });
    sl.addText(pct, {
      x: 11.2, y, w: 1.8, h: 0.5,
      fontSize: 18, fontFace: "Calibri", bold: true, color: pctColor, align: "right", valign: "middle",
    });
  });

  // Break-even banner
  sl.addShape(pres.shapes.RECTANGLE, {
    x: 6.7, y: 5.2, w: 5.8, h: 0.5,
    fill: { color: C.green, transparency: 80 },
    line: { color: C.green, width: 1 },
  });
  sl.addText("Break-even: Month 18", {
    x: 6.7, y: 5.2, w: 5.8, h: 0.5,
    fontSize: 14, fontFace: "Calibri", bold: true, color: C.green,
    align: "center", valign: "middle",
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 8 — ROADMAP
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  sl.addText("GO-TO-MARKET", {
    x: 0.5, y: 0.2, w: 5, h: 0.3,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.pink,
  });
  sl.addText("Scaling Roadmap", {
    x: 0.5, y: 0.65, w: 9, h: 0.7,
    fontSize: 40, fontFace: "Georgia", bold: true, color: C.white,
  });

  // Timeline horizontal line
  sl.addShape(pres.shapes.LINE, {
    x: 0.8, y: 3.0, w: 11.7, h: 0,
    line: { color: C.pink, width: 2 },
  });

  // Milestone nodes
  const milestones = [
    {
      x: 1.5, labelColor: C.pink, nodeColor: C.pink,
      phase: "NOW", title: "MVP Complete", body: "2 machines\nFL + PQC working",
    },
    {
      x: 4.5, labelColor: C.pink, nodeColor: C.pink,
      phase: "+3 Months", title: "Hospital Pilot", body: "Chula · Siriraj · CMU\nReal DICOM data",
    },
    {
      x: 7.5, labelColor: C.pink, nodeColor: C.pink,
      phase: "+12 Months", title: "Regional Scale", body: "20 hospitals\n\u0e2d\u0e22. Class II",
    },
    {
      x: 10.8, labelColor: C.green, nodeColor: C.green,
      phase: "+3 Years", title: "SEA Expansion", body: "Indonesia · Vietnam\nPhilippines",
    },
  ];

  milestones.forEach(({ x, labelColor, nodeColor, phase, title, body }) => {
    // Node circle on timeline
    sl.addShape(pres.shapes.OVAL, {
      x: x - 0.18, y: 2.82, w: 0.36, h: 0.36,
      fill: { color: nodeColor }, line: { color: nodeColor, width: 0 },
    });
    // Above: phase label
    sl.addText(phase, {
      x: x - 0.9, y: 1.35, w: 1.8, h: 0.32,
      fontSize: 14, fontFace: "Calibri", bold: true, color: labelColor, align: "center",
    });
    sl.addText(title, {
      x: x - 0.9, y: 1.72, w: 1.8, h: 0.32,
      fontSize: 12, fontFace: "Calibri", bold: false, color: C.white, align: "center",
    });
    sl.addText(body, {
      x: x - 0.9, y: 2.06, w: 1.8, h: 0.6,
      fontSize: 11, fontFace: "Calibri", color: C.muted, align: "center",
    });
  });

  // Revenue models
  sl.addText("Revenue Models", {
    x: 0.5, y: 3.5, w: 5, h: 0.38,
    fontSize: 14, fontFace: "Calibri", bold: true, color: C.white,
  });

  const revPills = [
    { icon: "🏛", title: "B2G", body: "\u0e3f30\u201380M/yr via \u0e2a\u0e18./\u0e2a\u0e1b\u0e2a\u0e0a." },
    { icon: "☁", title: "SaaS", body: "\u0e3f150/scan · \u0e3f0 upfront" },
    { icon: "🎓", title: "Research", body: "Free license + data partnership" },
  ];
  const revPillX = [0.3, 4.4, 8.5];
  revPills.forEach(({ icon, title, body }, i) => {
    const bx = revPillX[i];
    sl.addShape(pres.shapes.RECTANGLE, {
      x: bx, y: 4.0, w: 3.8, h: 1.2,
      fill: { color: C.card }, line: { color: C.pink, width: 0.5 },
    });
    sl.addText(icon + " " + title, {
      x: bx + 0.15, y: 4.08, w: 3.5, h: 0.38,
      fontSize: 13, fontFace: "Calibri", bold: true, color: C.white,
    });
    sl.addText(body, {
      x: bx + 0.15, y: 4.5, w: 3.5, h: 0.55,
      fontSize: 12, fontFace: "Calibri", color: C.muted,
    });
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 9 — COMPETITIVE
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  sl.addText("COMPETITIVE ADVANTAGE", {
    x: 0.5, y: 0.2, w: 7, h: 0.3,
    fontSize: 11, fontFace: "Calibri", bold: true, color: C.pink,
  });
  sl.addText("Why We Win", {
    x: 0.5, y: 0.65, w: 8, h: 0.7,
    fontSize: 40, fontFace: "Georgia", bold: true, color: C.white,
  });

  // Table header
  const tableX = 0.5;
  const tableY = 1.5;
  const tableW = 12.3;
  const colWidths = [3.8, 2.8, 2.8, 2.9];
  const headers = ["Feature", "Aidoc / Viz.ai", "Traditional AI", "Q-Sentinel Mesh"];
  const headerColors = [C.white, C.white, C.white, C.pink];

  sl.addShape(pres.shapes.RECTANGLE, {
    x: tableX, y: tableY, w: tableW, h: 0.5,
    fill: { color: C.card }, line: { color: C.card, width: 0 },
  });

  let cx = tableX;
  headers.forEach((h, i) => {
    sl.addText(h, {
      x: cx + 0.1, y: tableY + 0.07, w: colWidths[i] - 0.2, h: 0.36,
      fontSize: 14, fontFace: "Calibri", bold: true, color: headerColors[i],
      valign: "middle",
    });
    cx += colWidths[i];
  });

  // Data rows
  const rows = [
    { feature: "Data stays local", col2: "❌", col3: "❌", col4: "✅" },
    { feature: "Quantum enhanced", col2: "❌", col3: "❌", col4: "✅" },
    { feature: "Post-quantum crypto", col2: "❌", col3: "❌", col4: "✅" },
    { feature: "PDPA / HIPAA ready", col2: "⚠️", col3: "❌", col4: "✅" },
    { feature: "Works in rural hospitals", col2: "❌", col3: "⚠️", col4: "✅" },
  ];

  const rowH = 0.7;
  const rowFills = [C.bgDark, "221018", C.bgDark, "221018", C.bgDark];

  rows.forEach((row, ri) => {
    const ry = tableY + 0.5 + ri * rowH;
    sl.addShape(pres.shapes.RECTANGLE, {
      x: tableX, y: ry, w: tableW, h: rowH,
      fill: { color: rowFills[ri] }, line: { color: C.card, width: 0.3 },
    });

    const cellValues = [row.feature, row.col2, row.col3, row.col4];
    cx = tableX;
    cellValues.forEach((val, ci) => {
      let textColor = C.muted;
      if (ci === 0) textColor = C.white;
      else if (val === "✅") textColor = C.green;
      else if (val === "❌") textColor = C.pink;
      else if (val === "⚠️") textColor = "f0c040";

      sl.addText(val, {
        x: cx + 0.1, y: ry, w: colWidths[ci] - 0.2, h: rowH,
        fontSize: 14, fontFace: "Calibri", color: textColor,
        align: ci === 0 ? "left" : "center", valign: "middle",
      });
      cx += colWidths[ci];
    });
  });

  // Bottom tagline
  sl.addText("The only system in SEA combining Federated Learning + Quantum AI + Post-Quantum Cryptography", {
    x: 0, y: 6.7, w: 13.33, h: 0.5,
    fontSize: 14, fontFace: "Calibri", italic: true, color: C.muted, align: "center",
  });
}

// ─────────────────────────────────────────────────────────
// SLIDE 10 — CLOSING
// ─────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: C.bgDark };

  sl.addText("Q-Sentinel Mesh", {
    x: 0, y: 1.0, w: 13.33, h: 1.0,
    fontSize: 52, fontFace: "Georgia", bold: true, color: C.white, align: "center",
  });
  sl.addText("Intelligence grows with the network.", {
    x: 0, y: 1.85, w: 13.33, h: 0.45,
    fontSize: 20, fontFace: "Calibri", color: C.muted, align: "center",
  });
  sl.addText("Security grows with the future.", {
    x: 0, y: 2.3, w: 13.33, h: 0.45,
    fontSize: 20, fontFace: "Calibri", italic: true, color: C.pink, align: "center",
  });

  // Divider
  sl.addShape(pres.shapes.RECTANGLE, {
    x: (13.33 - 4) / 2, y: 2.85, w: 4, h: 0.03,
    fill: { color: C.pink }, line: { color: C.pink, width: 0 },
  });

  // 3 ask cards
  const asks = [
    { x: 0.4, icon: "🏆", title: "Top 5 Selection", body: "Prove the prototype works\nto the judges", border: C.pink },
    { x: 4.7, icon: "🤝", title: "Hospital Pilot", body: "3 hospitals for IRB study\n& real data validation", border: C.cyan },
    { x: 9.0, icon: "💰", title: "Seed Funding", body: "\u0e3f2M \u2192 production-ready\nin 6 months", border: C.green },
  ];
  asks.forEach(({ x, icon, title, body, border }) => {
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: 3.2, w: 3.8, h: 1.8,
      fill: { color: C.card }, line: { color: C.card, width: 0 },
    });
    // Left border accent
    sl.addShape(pres.shapes.RECTANGLE, {
      x, y: 3.2, w: 0.07, h: 1.8,
      fill: { color: border }, line: { color: border, width: 0 },
    });
    sl.addText(icon + " " + title, {
      x: x + 0.15, y: 3.28, w: 3.5, h: 0.45,
      fontSize: 14, fontFace: "Calibri", bold: true, color: C.white,
    });
    sl.addText(body, {
      x: x + 0.15, y: 3.78, w: 3.5, h: 0.95,
      fontSize: 12, fontFace: "Calibri", color: C.muted,
    });
  });

  // Tech stack pills
  const techPills = ["EfficientNet-B4", "VQC 4-qubit", "Flower FL", "ML-KEM-512", "AES-256-GCM", "Streamlit"];
  const pillW = 1.7;
  const pillGap = 0.22;
  const totalW = techPills.length * pillW + (techPills.length - 1) * pillGap;
  const startX = (13.33 - totalW) / 2;
  techPills.forEach((label, i) => {
    const px = startX + i * (pillW + pillGap);
    sl.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: px, y: 5.3, w: pillW, h: 0.32,
      fill: { color: C.card }, line: { color: C.pink, width: 0.5 },
      rectRadius: 0.1,
    });
    sl.addText(label, {
      x: px, y: 5.3, w: pillW, h: 0.32,
      fontSize: 10, fontFace: "Calibri", color: C.white,
      align: "center", valign: "middle",
    });
  });
}

// ─────────────────────────────────────────────────────────
// WRITE FILE
// ─────────────────────────────────────────────────────────
const outPath = "C:\\Users\\parip\\Downloads\\CEDT hack\\q-sentinel-mesh\\Q-Sentinel-Mesh-Pitch.pptx";

pres.writeFile({ fileName: outPath })
  .then(() => {
    console.log("SUCCESS: Pitch deck saved to:", outPath);
  })
  .catch((err) => {
    console.error("ERROR:", err);
    process.exit(1);
  });
