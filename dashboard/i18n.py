"""
Internationalization (i18n) Module for Q-Sentinel Mesh Dashboard

Supports:  🇬🇧 English (en)  ·  🇹🇭 ไทย (th)

Usage:
    from dashboard.i18n import T
    st.markdown(T("page_title"))
"""

from __future__ import annotations

import streamlit as st

# ═══════════════════════════════════════════════════════════════════════════════
# Translation Dictionary
# ═══════════════════════════════════════════════════════════════════════════════

TRANSLATIONS: dict[str, dict[str, str]] = {

    # ── General / Branding ────────────────────────────────────────────────────
    "brand_name":                   {"en": "Q-Sentinel",                         "th": "Q-Sentinel"},
    "brand_subtitle":               {"en": "Quantum Stroke Intelligence Mesh",   "th": "AI วินิจฉัยหลอดเลือดสมองด้วยควอนตัม"},
    "demo_mode":                    {"en": "Live",                               "th": "ออนไลน์"},
    "page_desc":                    {"en": "Quantum-Federated Stroke Diagnostic Intelligence Network",
                                     "th": "ระบบ AI วินิจฉัยโรคหลอดเลือดสมอง แบบ Federated + Quantum"},
    "online":                       {"en": "Online",                             "th": "ใช้งานได้"},
    "quantum_enhanced":             {"en": "⚛️ Quantum-Enhanced",                "th": "⚛️ เสริมด้วยควอนตัม"},
    "version_line":                 {"en": "Q-Sentinel Mesh v1.0",               "th": "Q-Sentinel Mesh v1.0"},
    "prototype_line":               {"en": "CEDT Hackathon 2026",               "th": "CEDT Hackathon 2026"},

    # ── Sidebar ───────────────────────────────────────────────────────────────
    "system_status":                {"en": "⚙️ System Status",                   "th": "⚙️ สถานะระบบ"},
    "compute":                      {"en": "Compute",                            "th": "ฮาร์ดแวร์"},
    "gpu_mode":                     {"en": "GPU",                                "th": "GPU"},
    "cpu_mode":                     {"en": "CPU Mode",                           "th": "ใช้ CPU"},
    "ai_model_label":               {"en": "AI Model",                          "th": "โมเดล AI"},
    "loaded":                       {"en": "Loaded",                             "th": "พร้อมใช้"},
    "mock":                         {"en": "Offline",                            "th": "ออฟไลน์"},
    "hospital_node":                {"en": "🏥 Hospital Node",                   "th": "🏥 เลือกโรงพยาบาล"},
    "select_node":                  {"en": "Select Node",                        "th": "เลือกโรงพยาบาล"},
    "demo_case":                    {"en": "📋 Patient",                         "th": "📋 ผู้ป่วย"},
    "hemorrhage_type":              {"en": "Hemorrhage Type",                    "th": "ประเภทเลือดออก"},
    "cnn_baseline":                 {"en": "🔷 CNN Baseline",                    "th": "🔷 CNN พื้นฐาน"},
    "qsentinel_hybrid":             {"en": "⚛️ Q-Sentinel Hybrid",               "th": "⚛️ Q-Sentinel ไฮบริด"},
    "export":                       {"en": "📊 Export",                           "th": "📊 ส่งออก"},
    "export_pdf":                   {"en": "📥 Export Report (PDF)",              "th": "📥 ดาวน์โหลดรายงาน (PDF)"},
    "export_coming_soon":           {"en": "📄 Report export — coming soon!",     "th": "📄 ดาวน์โหลดรายงาน — เร็วๆ นี้!"},

    # ── Quick Metrics ─────────────────────────────────────────────────────────
    "active_nodes":                 {"en": "🏥 Active Nodes",                    "th": "🏥 โหนดที่ทำงาน"},
    "federation_online":            {"en": "Federation Online",                  "th": "ระบบสหพันธ์พร้อม"},
    "global_auc":                   {"en": "🎯 Global AUC",                      "th": "🎯 AUC ระบบรวม"},
    "real_trained":                 {"en": "real trained model",                 "th": "จากโมเดลจริง"},
    "run_pipeline":                 {"en": "run pipeline",                       "th": "รัน pipeline ก่อน"},
    "run_pipeline_first":           {"en": "run pipeline first",                 "th": "รัน pipeline ก่อนเลย"},
    "avg_inference":                {"en": "⚡ Avg Inference",                    "th": "⚡ เวลาประมวลผล"},
    "inference_delta":              {"en": "-0.3s from last round",              "th": "-0.3 วิ จากรอบก่อน"},
    "encryption":                   {"en": "🔐 Encryption",                      "th": "🔐 การเข้ารหัส"},

    # ── Tabs ──────────────────────────────────────────────────────────────────
    "tab_diagnostic":               {"en": "🔬  Diagnostic View",                "th": "🔬  วินิจฉัย"},
    "tab_federated":                {"en": "🌐  Federated Intelligence",         "th": "🌐  Federated Learning"},
    "tab_security":                 {"en": "🔐  Security Layer",                 "th": "🔐  ความปลอดภัย"},

    # ── Tab 1: Diagnostic View ────────────────────────────────────────────────
    "ai_analysis":                  {"en": "🤖 AI Analysis",                     "th": "🤖 ผล AI"},
    "run_ai_analysis":              {"en": "⚡ Run AI Analysis",                  "th": "⚡ วิเคราะห์ด้วย AI"},
    "running_analysis":             {"en": "Running Q-Sentinel analysis...",     "th": "AI กำลังวิเคราะห์..."},
    "ai_heatmap_ready":             {"en": "AI Heatmap Ready",                   "th": "กดเพื่อวิเคราะห์"},
    "click_run_ai":                 {"en": 'Click <strong style="color:#00D4FF">Run AI Analysis</strong> to detect hemorrhage and generate an explainability map',
                                     "th": 'กด <strong style="color:#00D4FF">วิเคราะห์ด้วย AI</strong> เพื่อตรวจหาเลือดออกและดูแผนที่อธิบาย'},
    "analysis_config":              {"en": "Analysis Config",                    "th": "ตั้งค่าการวิเคราะห์"},
    "analysis_mode":                {"en": "Analysis Mode",                      "th": "รูปแบบการวิเคราะห์"},
    "what_ai_does":                 {"en": "ℹ️ What the AI does",                "th": "ℹ️ AI ทำอะไรบ้าง"},
    "ai_does_1":                    {"en": "Detects 5 hemorrhage subtypes simultaneously",
                                     "th": "ตรวจเลือดออก 5 ชนิดพร้อมกัน"},
    "ai_does_2":                    {"en": "Generates HiResCAM attention heatmap",
                                     "th": "สร้าง Heatmap แสดงจุดที่ AI สนใจ"},
    "ai_does_3":                    {"en": "Reports per-class confidence scores",
                                     "th": "บอกคะแนนความมั่นใจแต่ละชนิด"},
    "ai_does_4":                    {"en": "Runs in ~1.4 s on GPU",              "th": "ใช้เวลาแค่ ~1.4 วิ บน GPU"},
    "ct_scan_prefix":               {"en": "CT Scan",                            "th": "CT Scan"},
    "original_ct":                  {"en": "Original CT",                        "th": "CT ต้นฉบับ"},
    "ai_attention_map":             {"en": "AI Attention Map",                   "th": "จุดที่ AI สนใจ"},
    "hemorrhage_detected":          {"en": "⚠️ Hemorrhage Detected",             "th": "⚠️ พบเลือดออก"},
    "confidence":                   {"en": "confidence",                         "th": "ความมั่นใจ"},
    "no_hemorrhage":                {"en": "✅ No significant hemorrhage detected",
                                     "th": "✅ ไม่พบเลือดออก"},
    "hemorrhage_breakdown":         {"en": "Hemorrhage Probability Breakdown",   "th": "แยกประเภทเลือดออก"},
    "ai_heatmap_hirescam":          {"en": "AI Heatmap (HiResCAM)",              "th": "Heatmap จาก AI"},
    "most_relevant_slice":          {"en": "📍 Most relevant slice",             "th": "📍 สไลซ์ที่น่าสนใจที่สุด"},
    "high_activation":              {"en": "🔴 Red = High AI activation region", "th": "🔴 แดง = บริเวณที่ AI สนใจมาก"},
    "smart_triage":                 {"en": "SMART TRIAGE",                       "th": "เฝ้าระวังพิเศษ"},
    "suspected_lesion":             {"en": "⚠️ SMART TRIAGE: SUSPECTED LESION",  "th": "⚠️ เฝ้าระวังพิเศษ: ตรวจพบจุดที่น่าสงสัย"},
    "hemorrhage_type_breakdown":    {"en": "Hemorrhage Type Breakdown",          "th": "แยกประเภทเลือดออก"},
    "activation":                   {"en": "Activation",                         "th": "ค่าสนใจ"},
    "volume_prob_profile":          {"en": "Volume Hemorrhage Profile",          "th": "กราฟความน่าจะเป็นรายสไลซ์"},
    "volumetric_est":               {"en": "Estimated Blood Volume",             "th": "ปริมาณเลือดออกโดยประมาณ"},
    "vol_est_disclaimer":           {"en": "Simplified proxy based on probability integration", "th": "ค่าประมาณเบื้องต้นจากความน่าจะเป็นรวม"},
    "clinical_summary":             {"en": "Clinical Findings Summary",          "th": "สรุปผลการวินิจฉัยทางคลินิก"},
    "slice_index":                  {"en": "Slice Index",                        "th": "ลำดับสไลซ์"},
    "selected_slice":               {"en": "Selected Slice",                     "th": "สไลซ์ที่วิเคราะห์"},
    "visualization_settings":       {"en": "Visualization Settings",             "th": "ตั้งค่าการแสดงผล"},
    "heatmap_opacity":              {"en": "Heatmap Opacity",                    "th": "ความจางของ Heatmap"},
    "live_slice_sync":              {"en": "LIVE SLICE SYNC",                    "th": "กำลังแสดงสไลซ์ปัจจุบัน"},
    "current_is_top_focus":         {"en": "CURRENT SLICE IS AI FOCUS POINT",    "th": "สไลซ์ปัจจุบันคือจุดที่ AI สนใจที่สุด"},
    "demo_mode_active":             {"en": "MODEL NOT LOADED",                   "th": "โหลดโมเดลไม่สำเร็จ"},
    "missing_weights_msg":          {"en": "AI weights (.pth) not found. Please ensure weights/high_acc_b4.pth exists.",
                                     "th": "ไม่พบไฟล์โมเดล (.pth) กรุณาตรวจสอบว่ามีไฟล์ weights/high_acc_b4.pth"},
    "ai_sensitivity":               {"en": "Detection Sensitivity Threshold",    "th": "ระดับความไวในการวินิจฉัย (Sensitivity Threshold)"},
    "ai_sensitivity_help":          {"en": "Lower threshold = higher sensitivity (more likely to flag subtle lesions, but higher false positive risk).", 
                                     "th": "ลดค่านี้ลงเพื่อให้ AI ตรวจจับรอยโรคที่จางมากๆ (เพิ่มความไว), แต่อาจมีโอกาสเตือนหลอกเพิ่มขึ้น"},
    "no_hemorrhage_normal":         {"en": "✅ **No significant hemorrhage detected**  \nAI confidence: Normal finding",
                                     "th": "✅ **ไม่พบเลือดออกเทียบกับเป้าหมาย**  \nAI ประเมิน: ไม่ถึงเกณฑ์ที่ตั้งไว้"},

    # ── Hemorrhage Subtypes ───────────────────────────────────────────────────
    "epidural":                     {"en": "Epidural Hematoma",                  "th": "เลือดออกนอกเยื่อหุ้มสมอง"},
    "epidural_desc":                {"en": "Blood between skull and dura mater", "th": "เลือดออกระหว่างกะโหลกศีรษะและเยื่อดูรา"},
    "intraparenchymal":             {"en": "Intraparenchymal Hemorrhage",        "th": "เลือดออกในเนื้อสมอง"},
    "intraparenchymal_desc":        {"en": "Bleeding within brain tissue",       "th": "เลือดออกภายในเนื้อเยื่อสมอง"},
    "intraventricular":             {"en": "Intraventricular Hemorrhage",        "th": "เลือดออกในโพรงสมอง"},
    "intraventricular_desc":        {"en": "Blood in brain ventricles",          "th": "เลือดออกในโพรงสมอง (ventricles)"},
    "subarachnoid":                 {"en": "Subarachnoid Hemorrhage",            "th": "เลือดออกใต้เยื่อหุ้มสมองชั้นกลาง"},
    "subarachnoid_desc":            {"en": "Blood in subarachnoid space",        "th": "เลือดออกในช่องใต้เยื่ออะแร็กนอยด์"},
    "subdural":                     {"en": "Subdural Hematoma",                  "th": "เลือดออกใต้เยื่อหุ้มสมอง"},
    "subdural_desc":                {"en": "Blood between dura and brain",       "th": "เลือดออกระหว่างเยื่อดูราและสมอง"},
    "any_hemorrhage":               {"en": "Any Hemorrhage",                     "th": "เลือดออก (ชนิดใดก็ตาม)"},
    "any_hemorrhage_desc":          {"en": "Hemorrhage detected",                "th": "ตรวจพบเลือดออก"},

    # ── Tab 2: Federated Intelligence ─────────────────────────────────────────
    "fed_title":                    {"en": "🌐 Federated Learning Intelligence", "th": "🌐 Federated Learning"},
    "fed_subtitle":                 {"en": "Model intelligence aggregated from distributed hospitals —",
                                     "th": "โมเดลเรียนรู้ร่วมกันจากหลายโรงพยาบาล —"},
    "no_data_leaves":               {"en": "no patient data ever leaves",        "th": "ไม่ส่งข้อมูลผู้ป่วยออกไปเลย"},
    "local_servers":                {"en": "local servers.",                      "th": "จากเซิร์ฟเวอร์ภายใน"},
    "benchmark_heading":            {"en": "📈 Benchmark: Isolated vs Federated","th": "📈 เปรียบเทียบ: แยก vs รวม"},
    "real_results":                 {"en": "✅ Real trained-model results",       "th": "✅ ผลจากโมเดลจริง"},
    "sim_json_error":               {"en": "⚠️ Simulated (JSON parse error)",    "th": "⚠️ ข้อมูลจำลอง (อ่าน JSON ไม่ได้)"},
    "sim_run_pipeline":             {"en": "⚠️ Simulated — run `python run_all.py` for real results",
                                     "th": "⚠️ ข้อมูลจำลอง — รัน `python run_all.py` เพื่อดูผลจริง"},
    "key_metrics":                  {"en": "📊 Key Metrics",                     "th": "📊 ตัวเลขสำคัญ"},
    "baseline_auc":                 {"en": "Baseline AUC",                       "th": "AUC พื้นฐาน"},
    "hybrid_auc":                   {"en": "Hybrid AUC",                         "th": "AUC ไฮบริด"},
    "federated_auc":                {"en": "Federated AUC",                      "th": "AUC สหพันธ์"},
    "nodes":                        {"en": "Nodes",                              "th": "โหนด"},
    "vs_isolated":                  {"en": "vs isolated",                        "th": "vs แยก"},
    "animate_fed":                  {"en": "▶️  Animate Federated Training",      "th": "▶️  เล่นแอนิเมชันการฝึก"},
    "round_config":                 {"en": "Round Config",                       "th": "การตั้งค่ารอบ"},
    "rounds":                       {"en": "Rounds",                             "th": "รอบ"},
    "hospitals":                    {"en": "Hospitals",                          "th": "โรงพยาบาล"},
    "algorithm":                    {"en": "Algorithm",                          "th": "อัลกอริทึม"},
    "privacy":                      {"en": "Privacy",                            "th": "ความเป็นส่วนตัว"},
    "preserved":                    {"en": "✅ Preserved",                        "th": "✅ ปกป้องแล้ว"},
    "last_sim_results":             {"en": "📊 Last Simulation Results",          "th": "📊 ผลจำลองล่าสุด"},
    "run_full_pipeline":            {"en": "💡 Run the Full Pipeline",            "th": "💡 รัน Pipeline ทั้งหมด"},
    "run_full_pipeline_desc":       {"en": "Train baseline → hybrid → run 3-hospital federated simulation",
                                     "th": "ฝึก baseline → hybrid → จำลอง Federated 3 โรงพยาบาล"},
    "node_status":                  {"en": "🏥 Node Status",                     "th": "🏥 สถานะแต่ละโรงพยาบาล"},
    "local_dataset":                {"en": "Local Dataset",                      "th": "ข้อมูลภายใน"},
    "scans":                        {"en": "scans",                              "th": "สแกน"},
    "local_auc":                    {"en": "Local AUC",                          "th": "AUC คนเดียว"},
    "status":                       {"en": "Status",                             "th": "สถานะ"},

    # ── Tab 3: Security Layer ─────────────────────────────────────────────────
    "pqc_title":                    {"en": "🔐 Post-Quantum Security Layer",     "th": "🔐 ระบบความปลอดภัยหลังควอนตัม"},
    "pqc_subtitle":                 {"en": "All model weight transmissions are protected with <strong style=\"color:#00D4FF;\">ML-KEM-512</strong> (CRYSTALS-Kyber, NIST FIPS 203) — secure against both classical and quantum adversaries.",
                                     "th": "การส่งน้ำหนักโมเดลทั้งหมดถูกปกป้องด้วย <strong style=\"color:#00D4FF;\">ML-KEM-512</strong> (CRYSTALS-Kyber, NIST FIPS 203) — ปลอดภัยจากทั้งคอมพิวเตอร์ทั่วไปและควอนตัม"},
    "secure_flow":                  {"en": "🔄 Secure Weight Transmission Flow", "th": "🔄 ขั้นตอนการส่งน้ำหนักอย่างปลอดภัย"},
    "flow1_title":                  {"en": "Local Training",                     "th": "การฝึกภายใน"},
    "flow1_desc":                   {"en": "Hospital trains model on local CT data → extracts weight deltas",
                                     "th": "โรงพยาบาลฝึกโมเดลด้วยข้อมูล CT ภายใน → ดึงส่วนต่างน้ำหนัก"},
    "flow2_title":                  {"en": "ML-KEM-512 Key Encapsulation",       "th": "การห่อหุ้มกุญแจ ML-KEM-512"},
    "flow2_desc":                   {"en": "Generates shared secret from server's public key (768-byte pk, 1088-byte ciphertext)",
                                     "th": "สร้างความลับร่วมจากกุญแจสาธารณะของเซิร์ฟเวอร์ (pk 768 ไบต์, ciphertext 1088 ไบต์)"},
    "flow3_title":                  {"en": "HKDF-SHA256 + AES-256-GCM Encrypt",  "th": "เข้ารหัส HKDF-SHA256 + AES-256-GCM"},
    "flow3_desc":                   {"en": "Derives 256-bit key → encrypts model weights with authenticated encryption",
                                     "th": "สร้างกุญแจ 256 บิต → เข้ารหัสน้ำหนักโมเดลด้วยการเข้ารหัสพร้อมยืนยันตัวตน"},
    "flow4_title":                  {"en": "Encrypted Payload Transmission",     "th": "การส่งข้อมูลที่เข้ารหัสแล้ว"},
    "flow5_title":                  {"en": "Server Decapsulation & Aggregation", "th": "เซิร์ฟเวอร์ถอดรหัสและรวมข้อมูล"},
    "flow5_desc":                   {"en": "Recovers shared secret → AES-GCM decrypt → FedAvg aggregation → re-encrypts global model",
                                     "th": "กู้คืนความลับร่วม → ถอดรหัส AES-GCM → รวมด้วย FedAvg → เข้ารหัสโมเดลรวมใหม่"},
    "flow6_title":                  {"en": "Global Model Update",               "th": "อัปเดตโมเดลรวม"},
    "flow6_desc":                   {"en": "Hospital receives PQC-encrypted global weights → local model updated",
                                     "th": "โรงพยาบาลรับน้ำหนักรวมที่เข้ารหัส PQC → อัปเดตโมเดลภายใน"},
    "specifications":               {"en": "🛡️ Specifications",                  "th": "🛡️ ข้อมูลจำเพาะ"},
    "kem_algorithm":                {"en": "KEM Algorithm",                      "th": "อัลกอริทึม KEM"},
    "standard":                     {"en": "Standard",                           "th": "มาตรฐาน"},
    "security_level":               {"en": "Security Level",                     "th": "ระดับความปลอดภัย"},
    "security_level_val":           {"en": "NIST Level 1 (128-bit PQ)",          "th": "NIST ระดับ 1 (128 บิต PQ)"},
    "symmetric_cipher":             {"en": "Symmetric Cipher",                   "th": "รหัสสมมาตร"},
    "key_derivation":               {"en": "Key Derivation",                     "th": "การสร้างกุญแจ"},
    "transport":                    {"en": "Transport",                          "th": "การขนส่ง"},
    "data_privacy":                 {"en": "Data Privacy",                       "th": "ความเป็นส่วนตัวของข้อมูล"},
    "data_privacy_val":             {"en": "Federated (no raw data)",            "th": "สหพันธ์ (ไม่มีข้อมูลดิบ)"},
    "compliance":                   {"en": "Compliance",                         "th": "การปฏิบัติตามกฎ"},
    "live_pqc_demo":                {"en": "✅ Live PQC Demo",                    "th": "✅ สาธิต PQC สด"},
    "gen_keypair":                  {"en": "🔑 Generate Key Pair & Demo Encrypt","th": "🔑 สร้างคู่กุญแจและสาธิตการเข้ารหัส"},
    "generating_keys":              {"en": "Generating ML-KEM-512 keys...",      "th": "กำลังสร้างกุญแจ ML-KEM-512..."},
    "pqc_success":                  {"en": "✅ PQC Demo Successful",              "th": "✅ สาธิต PQC สำเร็จ"},
    "decrypt_ok":                   {"en": "✅ OK",                               "th": "✅ สำเร็จ"},
    "decrypt_failed":               {"en": "❌ FAILED",                           "th": "❌ ล้มเหลว"},
    "pqc_not_installed":            {"en": "pqcrypto not installed. Run `setup_env.bat` first.",
                                     "th": "ยังไม่ได้ติดตั้ง pqcrypto รัน `setup_env.bat` ก่อน"},
    "why_pqc":                      {"en": "🔮 Why Post-Quantum Cryptography?",  "th": "🔮 ทำไมต้องใช้การเข้ารหัสหลังควอนตัม?"},
    "why_pqc_text":                 {"en": 'Current <strong style="color:#94A3B8;">RSA/ECC</strong> encryption is vulnerable to Shor\'s Algorithm on quantum computers. <strong style="color:#00D4FF;">ML-KEM-512</strong> is based on the hardness of <strong style="color:#94A3B8;">Module Learning With Errors (MLWE)</strong> — believed intractable even for quantum adversaries — future-proofing patient data and model intellectual property against the coming quantum era.',
                                     "th": 'การเข้ารหัส <strong style="color:#94A3B8;">RSA/ECC</strong> แบบเดิมโดนอัลกอริทึม Shor บนคอมพิวเตอร์ควอนตัมได้ <strong style="color:#00D4FF;">ML-KEM-512</strong> ใช้ความยากของ <strong style="color:#94A3B8;">MLWE</strong> — แกไม่ได้แม้ด้วยควอนตัม — ปกป้องข้อมูลผู้ป่วยจากยุค Quantum ที่กำลังจะมาถึง'},

    # ── Charts (fed_chart.py) ─────────────────────────────────────────────────
    "improvement_gap":              {"en": "Improvement Gap",                    "th": "ความต่างที่ดีขึ้น"},
    "num_fed_nodes":                {"en": "Number of Federated Nodes",          "th": "จำนวนโรงพยาบาล"},
    "auc_pct":                      {"en": "AUC (%)",                            "th": "AUC (%)"},
    "chart_title_grows":            {"en": "Q-Sentinel Mesh: Intelligence Grows with the Network",
                                     "th": "Q-Sentinel Mesh: ยิ่งรวม ยิ่งฉลาด"},
    "hospital_singular":            {"en": "Hospital",                           "th": "โรงพยาบาล"},
    "hospital_plural":              {"en": "Hospitals",                          "th": "โรงพยาบาล"},
    "fed_sim_not_run":              {"en": "Federated simulation not yet run. Launch simulation from the sidebar.",
                                     "th": "ยังไม่ได้รัน simulation เลย"},
    "global_auc_round":             {"en": "Global AUC per Federated Round",     "th": "AUC รวมแต่ละรอบ"},
    "global_loss_round":            {"en": "Global Loss per Federated Round",    "th": "Loss รวมแต่ละรอบ"},
    "round":                        {"en": "Round",                              "th": "รอบ"},
    "loss":                         {"en": "Loss",                               "th": "Loss"},
    "per_hospital_auc":             {"en": "Per-Hospital AUC Progression",       "th": "AUC แต่ละโรงพยาบาล"},
    "global_fedavg":                {"en": "Global (FedAvg)",                    "th": "รวม (FedAvg)"},
    "fed_round":                    {"en": "Federated Round",                    "th": "รอบการฝึก"},
    "fed_sim_title":                {"en": "🔄 Federated Intelligence Simulation",
                                     "th": "🔄 จำลอง Federated Training"},
    "isolated_hospital":            {"en": "Isolated Hospital (No Federation)",  "th": "โรงพยาบาลแยก"},
    "qsentinel_federated":          {"en": "Q-Sentinel Mesh (Federated)",        "th": "Q-Sentinel รวมกัน"},
    "round_n_sharing":              {"en": "Hospitals sharing intelligence...",   "th": "โรงพยาบาลกำลังแชร์ย์โมเดล..."},
    "fed_complete":                 {"en": "Federated training complete!",       "th": "Federated Training เสร็จ!"},
    "auc_improved":                 {"en": "Global AUC improved from",           "th": "AUC เพิ่มจาก"},
    "isolated":                     {"en": "isolated",                           "th": "แยก"},
    "hospitals_count":              {"en": "3 hospitals",                         "th": "3 โรงพยาบาล"},

    # ── CT Viewer ─────────────────────────────────────────────────────────────
    "axial_slice":                  {"en": "Axial Slice",                        "th": "สไลซ์"},
    "scroll_slices":                {"en": "Scroll through axial CT slices",     "th": "เลื่อนดูสไลซ์ CT"},
    "window":                       {"en": "Window",                             "th": "Window"},
    "depth":                        {"en": "depth",                              "th": "ความลึก"},
    "hu_histogram":                 {"en": "📊 HU Histogram",                    "th": "📊 กราฟ HU"},
    "hu_value":                     {"en": "HU Value",                           "th": "ค่า HU"},
    "count":                        {"en": "Count",                              "th": "จำนวน"},
    "slices":                       {"en": "slices",                             "th": "สไลซ์"},

    # ── Window Presets ────────────────────────────────────────────────────────
    "win_brain":                    {"en": "Brain",                              "th": "สมอง"},
    "win_blood":                    {"en": "Blood",                              "th": "เลือด"},
    "win_subdural":                 {"en": "Subdural",                           "th": "ใต้เยื่อหุ้มสมอง"},
    "win_bone":                     {"en": "Bone",                               "th": "กระดูก"},
    "win_wide":                     {"en": "Wide",                               "th": "กว้าง"},

    # ── Scan Counter & Model Comparison ──────────────────────────────────────
    "scans_analyzed":               {"en": "🔬 Scans Analyzed",                   "th": "🔬 สแกนที่วิเคราะห์"},
    "this_session":                 {"en": "this session",                        "th": "เซสชันนี้"},
    "model_comparison":             {"en": "Model Comparison (AUC)",              "th": "เปรียบเทียบโมเดล (AUC)"},
    "quantum_gain":                 {"en": "Quantum Gain",                        "th": "ประโยชน์จาก Quantum"},

    # ── PDF Export ────────────────────────────────────────────────────────────
    "generating_pdf":               {"en": "Generating PDF report...",            "th": "กำลังสร้างรายงาน PDF..."},
    "export_pdf_disabled":          {"en": "📥 Run AI first to export",           "th": "📥 วิเคราะห์ AI ก่อนดาวน์โหลด"},

    # ── Language Toggle ───────────────────────────────────────────────────────
    "language":                     {"en": "🌐 Language",                         "th": "🌐 ภาษา"},

    # ── DICOM Upload ──────────────────────────────────────────────────────────
    "upload_section":               {"en": "📂 Upload CT Scan",                  "th": "📂 อัปโหลด CT Scan"},
    "upload_dicom":                 {"en": "Choose .dcm files",                  "th": "เลือกไฟล์ .dcm"},
    "upload_dicom_help":            {"en": "Upload all .dcm slices from one CT series (they will be sorted automatically by slice order)",
                                     "th": "อัปโหลดไฟล์ .dcm ทุกสไลซ์จาก CT series เดียวกัน (ระบบเรียงลำดับให้อัตโนมัติ)"},
    "load_dicom_btn":               {"en": "⬆️ Load DICOM Volume",               "th": "⬆️ โหลด CT จาก DICOM"},
    "loading_dicom":                {"en": "Loading DICOM slices...",            "th": "กำลังโหลดสไลซ์ DICOM..."},
    "upload_dicom_success":         {"en": "Real CT volume loaded!",             "th": "โหลด CT จริงสำเร็จ!"},
    "upload_dicom_error":           {"en": "Failed to load DICOM",               "th": "โหลด DICOM ไม่สำเร็จ"},
    "using_real_ct":                {"en": "Real CT Loaded",                     "th": "CT จริง (อัปโหลดแล้ว)"},
    "using_mock_ct":                {"en": "CT-ICH Dataset",                     "th": "CT จากชุดข้อมูล CT-ICH"},
    "clear_real_ct":                {"en": "🗑️ Remove Real CT",                  "th": "🗑️ ลบ CT ที่อัปโหลด"},
    "intensity_adjusted":           {"en": "Intensity Adjusted",                 "th": "ปรับแก้น้ำหนักสีภาพ"},
    "model_input_debug":            {"en": "🧠 Model View (Preprocessing Insight)", "th": "🧠 ภาพที่ AI เห็น (เพื่อตรวจสอบ)"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Helper Function
# ═══════════════════════════════════════════════════════════════════════════════

def T(key: str) -> str:
    """Get English string for the given key."""
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get("en", key)


def get_lang() -> str:
    """Return current language code (always English)."""
    return "en"
