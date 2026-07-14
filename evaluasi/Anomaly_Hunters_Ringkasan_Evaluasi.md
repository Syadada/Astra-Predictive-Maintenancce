# RINGKASAN & EVALUASI PROPOSAL ANOMALY HUNTERS
## Presentasi Besok - Persiapan

---

## **I. RINGKASAN PROPOSAL KALIAN (SESUAI CASE KERRY GROUP)**

### **A. PROBLEM STATEMENT - DIAGNOSA YANG KUAT ✓**

**Masalah Utama yang Diidentifikasi:**
- **Status Quo Kerry Group:** Maintenance berbasis waktu (time-based), bukan kondisi mesin
- **Dampak Negatif:**
  - Unplanned downtime tinggi
  - Emergency repair costs meningkat
  - OEE (Overall Equipment Effectiveness) rendah
  - Food safety risks terjaga tidak optimal
  - Data dari SCADA/MES/ERP/IoT sensors **TIDAK terintegrasikan**

**Bukti yang Dikutip:**
- Deloitte: Unplanned downtime = USD 50 miliar/tahun industri
- McKinsey: Predictive maintenance bisa reduce downtime hingga 50%

**Penilaian:** ✓ SANGAT RELEVAN dengan case, data-driven, menggunakan evidence

---

### **B. SOLUSI - ARCHITECTURE YANG KOMPREHENSIF ✓**

**Naming Strategy: "PredictaGuard" (dalam proposal disebut "Explainable AI Maintenance Copilot")**

**Diferensiator Utama (KUNCI UNIQUE VALUE):**

| Aspek | Conventional PM | PredictaGuard (Kalian) |
|-------|-----------------|----------------------|
| **Output** | Failure probability (%) | Explanation + Action + Cost Impact |
| **Trust Factor** | Rendah (black-box) | Tinggi (XAI/SHAP-based) |
| **Food Safety** | Manual atau tidak ada | **Automated CCP prioritization + HACCP log** |
| **Transparency** | None/Post-hoc | Real-time SHAP per alert |
| **Channels** | Dashboard only | Dashboard + Mobile + WhatsApp + Email |
| **Model** | Static | Continuous learning dari ERP logs |
| **Infrastructure** | Cloud-dependent | On-premise (Phi-3 Mini) |

**KEKUATAN:** Ini adalah competitive advantage yang SERIUS - fokus pada "Human Trust Gap" adalah insight yang belum dieksplorasi pesaing lain.

---

### **C. TECHNICAL APPROACH - STACK YANG SOLID ✓**

**Tech Stack Dipilih:**
```
IoT Transport:     MQTT (Mosquitto Broker)
Streaming:         Apache Kafka
Preprocessing:     Python (Pandas, NumPy)
Anomaly Detection: LSTM Autoencoder (PyTorch)
RUL Prediction:    Temporal Fusion Transformer
Explainability:    SHAP (shap library)
Copilot LLM:       Phi-3 Mini (on-premise, 3.8B params)
Dashboard:         React + Grafana
Database:          PostgreSQL + InfluxDB
```

**Alasan Teknis (Diartikulasikan dengan Baik):**
- LSTM Autoencoder > Threshold alerts (menangkap temporal dependencies)
- TFT > vanilla LSTM (attention mechanism untuk multi-scale patterns)
- SHAP > surrogate models (mathematically rigorous)
- Phi-3 Mini on-premise (data sovereignty untuk food industry)
- InfluxDB (optimized untuk high-frequency sensor data)

**Penilaian:** ✓ Matang, tidak ada teknologi experimental, semua open-source/free-tier

---

### **D. BUSINESS MODEL - FEASIBLE & REALISTIC ✓**

**Model Revenue:**
- **Project-based implementation fee** (design + build + deploy)
- **Annual maintenance retainer** (tied to SLAs: uptime + accuracy)

**Customer Segment:** Kerry Group manufacturing facilities (Critical Control Points)

**Value Proposition:** $50K-$500K cost savings per incident avoided (food manufacturing)

**Key Partners:** Kerry ops teams, IoT vendors, infrastructure providers

**Sustainability:** System improves dengan lebih banyak failure data → ROI jelas

---

### **E. TIMELINE - REALISTIS DAN TERSTRUKTUR ✓**

**Phase Structure (Sesuai kompetisi):**
1. **Concept & Proposal** (Now-12 Juni) → ✓ DONE
2. **Mock-up & Core Model** (15-30 Juni) → Video dashboard mock-up
3. **Prototype Dev** (10 Juli-31 Juli) → Mentoring + Company visit + Full integration
4. **Final Submission** (Aug-23 Sept) → Presentation + Business Matching

**Penilaian:** ✓ Feasible dalam timeline kompetisi, milestone jelas

---

### **F. TEAM COMPOSITION - WELL-BALANCED ✓**

| Nama | Expertise | Role |
|------|-----------|------|
| Rasyaad (Lead) | Data Science, AI/ML, Full-Stack | XAI layer + system integration |
| Nadine | Python, Analytical thinking | ML Pipeline + RUL model |
| Nor Umayah | Detail-oriented, QA | System validation + documentation |
| Shonia | Structured thinking, Business | Business architecture + feasibility |

**Kekuatan:** 4 dari 4 orang punya role spesifik, skill complementary

---

## **II. EVALUASI KRITIS - AREA YANG PERLU DIPERHATIKAN**

### **⚠️ POIN RAWAN untuk Presentasi:**

#### **1. DATA QUALITY RISK (ACKNOWLEDGED tapi perlu stress)**
- Proposal kalian **tahu** ketergantungan pada historical MTBF/MTTR data dari Kerry
- **Solusi kalian:** Transfer learning dari NASA CMAPSS dataset (6000+ cycles)
- **Saran untuk presentasi besok:**
  - ✓ Jelaskan **bagaimana kalian handle sparse data** (synthetic augmentation via Monte Carlo)
  - ✓ Tunjukkan bahwa **pre-training dengan CMAPSS bisa mitigasi cold-start problem**
  - Siapkan slide: "Data Contingency" - jika data Kerry tidak cukup, fallback strategy apa?

#### **2. FOOD SAFETY COMPLIANCE (Critical Control Point)**
- Kalian mention HACCP + CCP alert prioritization
- **APA DEFINISI CCP KALIAN?**
  - Pasteurization equipment? Mixing tanks? Packaging lines?
  - Setiap CCP punya threshold risk berbeda
- **Saran:** Siapkan contoh konkrit:
  - "Jika pump di pasteurization line menunjukkan anomaly, alert dijadikan PRIORITY 1 + auto-logged untuk audit"

#### **3. EXPLAINABILITY (XAI) - JANTUNG DIFFERENTIATOR**
- Proposal kalian: "SHAP translates anomaly score into structured explanation"
- **TAPI... demo konkritnya?**
  - "Sensor A (vibration) crossed threshold X"
  - "Pattern matches 87% dengan historical failure Y pada 2023-03-15"
  - "Recommended action: Replace bearing, spare part #XYZ-123, cost impact: $2500 if ignored → downtime 4 hours"
- **Saran:** Kalian **WAJIB punya screenshot/video konkrit XAI output** untuk presentasi

#### **4. IMPLEMENTASI vs SCOPE**
- Proposal kalian fokus pada 4 equipment: pumps, mixers, spray dryers, compressors
- **Berapa banyak units di Kerry?** 50? 200? 500?
- **MVP phase:** Fokus pada 1-2 equipment jenis dulu? Atau semua sekaligus?
- **Saran:** Jelaskan phasing:
  - Phase 1 (6 bulan): Pilot pada 10 pump units → validate accuracy
  - Phase 2 (6 bulan): Scale ke mixer + dryer
  - Phase 3: Compressors + other critical assets

---

## **III. KEKUATAN PROPOSAL KALIAN (HIGHLIGHT SAAT PRESENTASI)**

### **🎯 TOP 3 UNIQUE SELLING POINTS:**

**1. Human Trust Gap Solved (PALING KUAT)**
   - Kompetitor: "Pump gagal dengan 85% probability"
   - Kalian: "Pump gagal dengan 85% probability KARENA vibration melebihi threshold 12mm/s selama 6 jam, mirip failure pada 2024-02-10, SOLUSI: ganti bearing, cost: $2500, budget untuk spare part sekarang, atau risk downtime Rp 500 juta"

**2. Food Safety Integrated (NICHE ADVANTAGE)**
   - Bukan hanya maintenance → juga compliance record untuk HACCP audit
   - Unique di food manufacturing industry

**3. On-Premise LLM (DATA SOVEREIGNTY)**
   - Phi-3 Mini bisa jalan di local server, data tidak keluar
   - Critical untuk manufaktur food dengan data sensitif

---

## **IV. SARAN UNTUK PRESENTASI BESOK**

### **A. STRUKTUR PRESENTASI (Waktu 15-20 menit)**

```
[0-2 min]   Opening: "Kerry produces 900M+ products/year. 
                      Satu unplanned downtime = USD 500K loss"
            
[2-5 min]   Problem: Gambarin maintenance engineer Jerry yang
            "Mesin ini bagus nih..." padahal besok bisa failure
            
[5-8 min]   Solution Architecture (DEMO/VIDEO ANIMASI):
            Sensor → Kafka → ML → SHAP explanation → Action
            
[8-12 min]  Live Demo atau Video Walk-through:
            - Dashboard screenshot
            - XAI explanation output (KONKRIT!)
            - CCP alert priority system
            
[12-15 min] Business Case:
            "Dari baseline: 5 downtime/tahun × $100K = $500K loss
             Dengan PredictaGuard: 1 downtime/tahun × $100K = $100K loss
             ROI break-even: 6 bulan"
             
[15-18 min] Timeline & Team:
            Gantt chart (mock-up done by 30 June, full proto by 31 July)
            
[18-20 min] Q&A siap
```

### **B. SLIDE YANG HARUS ADA:**

- ✓ Problem severity (dengan angka: Rp X downtime/tahun)
- ✓ Competitive positioning table (3-4 kompetitor atau generic approach)
- ✓ **XAI Output Example** (VISUAL!)
- ✓ Food safety compliance diagram
- ✓ Cost-benefit analysis
- ✓ Risk mitigation (data quality, accuracy tolerance, rollback plan)
- ✓ Reference architecture diagram (from your proposal sudah ada di page 6-7)

### **C. MATERIA YANG HARUS DISIAPKAN:**

1. **Video Demo Dashboard** (untuk phase 2, pastikan quality tinggi)
2. **Live Demo (jika laptop baik):** Load data, show anomaly, explain via SHAP, show CCP alert
3. **Physical mockup atau Figma prototype** dari interface
4. **Cost breakdown**: Berapa maintenance cost sekarang vs nanti
5. **Risk register**: Apa yg bisa gagal & bagaimana handle

---

## **V. PERTANYAAN YANG AKAN DITANYA JUDGE**

### **Siapkan jawaban untuk:**

1. **"Data mana yang kalian gunakan untuk training?"**
   - Jawab: "Historical maintenance records dari Kerry (jika ada), CMAPSS public dataset untuk pre-training, synthetic data dari Monte Carlo untuk augmentation"

2. **"Bagaimana jaminan akurasi model?"**
   - Jawab: "Initial phase: 80%+ sensitivity untuk anomaly, continuous retraining meningkatkan accuracy. SLA target: 90% precision untuk RUL prediction dalam ±24 jam window"

3. **"Berapa biaya implementasi?"**
   - Jawab: "Development: 200 juta (including hardware), annual support: 50 juta. ROI: Hindari 2-3 downtime events = payback 3-4 bulan"

4. **"Bagaimana dengan equipment yang belum punya sensor?"**
   - Jawab: "IoT retrofit atau soft-sensor approach menggunakan proxy signals (power, temperature)"

5. **"Scalability ke pabrik lain?"**
   - Jawab: "Architecture modular via Kafka topics + containerized services. Bisa replicate ke pabrik lain dengan retrain model lokal"

6. **"Siapa yang maintain sistem?"**
   - Jawab: "Kerry IT team akan handle infrastructure, kami support model updates & optimization"

---

## **VI. FINAL CHECKLIST SEBELUM PRESENTASI**

- [ ] Presentasi deck dibuat (Figma/PowerPoint)
- [ ] Video mock-up dashboard selesai 30 Juni
- [ ] Live demo siap (atau backup dengan video)
- [ ] Printout proposal untuk jurys
- [ ] Backup USB dengan semua file
- [ ] Siapkan 1 halaman ringkasan (executive summary untuk leave-behind)
- [ ] Practice presentasi 3x, role-play Q&A
- [ ] Dress code rapi (kerja profesional)
- [ ] Tiba 15 menit lebih awal

---

## **KESIMPULAN KESELURUHAN**

**Proposal kalian SOLID dengan skor ~8/10:**

**Kekuatan:**
- ✓ Unique value: XAI + Human Trust (belum banyak yg fokus)
- ✓ Food safety angle (niche advantage)
- ✓ Technical depth (stack matang, no experimental tech)
- ✓ Business model realistis
- ✓ Team balanced & skilled

**Area improvement:**
- ⚠️ Need concrete XAI demo/example
- ⚠️ Food safety CCP definition lebih detail
- ⚠️ Competitive analysis vs existing solutions lebih depth
- ⚠️ Implementation phasing lebih konkrit (Phase 1 MVP scope)

**Probabilitas menang:** 60-70% jika presentasi execution bagus dan demo XAI impressive

