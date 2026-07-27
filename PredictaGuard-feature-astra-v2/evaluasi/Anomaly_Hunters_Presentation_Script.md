# PRESENTATION SCRIPT & PRACTICAL CHECKLIST
## Anomaly Hunters - Kerry Group Predictive Maintenance
### Presentasi Besok (Format: 15-20 menit)

---

## **BAGIAN I: PRESENTATION SCRIPT (Master Copy)**

### **[OPENING - 1 menit] 👋**

```
[Tim berdiri, projector on, slide 1 Title]

RASYAAD (Lead):
"Selamat pagi Dewan Juri. Nama saya Rasyaad, Lead Engineer dari Anomaly Hunters.

Kami ingin membuka dengan pertanyaan sederhana:

BERAPA BIAYA jika sebuah pompa di lini pasteurisasi Kerry tiba-tiba RUSAK 
tanpa peringatan, menghentikan 900 juta produk per tahun?

Jawab: Antara USD 100 hingga 500 ribu HANYA untuk satu incident.

Kerry Group menghadapi masalah ini setiap tahun. Mereka menggunakan 
REACTIVE maintenance - ganti onderdil BERDASARKAN JADWAL, bukan kondisi mesin.

Hari ini kami tunjukkan SOLUSI: PredictaGuard, sebuah sistem AI yang memprediksi 
kegagalan SEBELUM terjadi, dan yang LEBIH PENTING - menjelaskan MENGAPA mesin akan gagal,
sehingga teknisi PERCAYA dan segera bertindak.

Mari saya tunjukkan bagaimana."

[Pause 2 detik, lanjut ke slide problem]
```

---

### **[PROBLEM STATEMENT - 2-3 menit] 🔴**

```
[SLIDE: Gambar maintenance engineer bingung, mesin rusak mendadak]

NADINE (ML Engineer):
"Ini adalah Pak Jerry, teknisi pemeliharaan Kerry Group selama 15 tahun.

Setiap bulan dia melihat data dari sensor - temperature, vibration, arus listrik. 
Tapi Pak Jerry dilatih untuk melakukan maintenance SESUAI JADWAL: 
- Ganti bearing pompa setiap 6 bulan
- Service mixer setiap 3 bulan
- Inspect spray dryer setiap bulan

MASALAHNYA: 
1. Jadwal itu BUKAN berdasarkan kondisi mesin yang sebenarnya
2. Mesin yang masih bagus dipaksa diperbaiki (waste)
3. Mesin yang sudah aged tapi belum jadwal, gagal tiba-tiba

Hasilnya:
- Rp 500 juta kerugian per incident (downtime + emergency parts + labor)
- 5-7 unplanned downtime per tahun di Kerry
- Risiko food safety: Jika pasteurization rusak, batch produk tercemar

[SLIDE: Chart cost breakdown]
Mari lihat cost-benefit reality saat ini:
- Reactive maintenance: Rp 5-7 juta/tahun (emergency repairs)
- Plus downtime impact: Rp 500 juta × 5 incidents = Rp 2.5 MILIAR per tahun
- Plus inventory overhead: Spare parts tidak terguna: Rp 200 juta
- TOTAL: Rp 2.7 MILIAR per tahun

Ini karena Kerry tidak mengintegrasikan sensor data dengan sistem maintenance mereka.
SCADA, MES, ERP, IoT sensors - semua exist tapi TIDAK talk to each other.

Data itu just sitting there, tidak digunakan."
```

---

### **[SOLUTION - HIGH LEVEL - 2-3 menit] 💡**

```
[SLIDE: System Architecture Diagram]

RASYAAD:
"Solusi kami simple tapi powerful: PredictaGuard.

Bayangkan jika Pak Jerry bukan hanya diberitahu 'pompa mungkin gagal',
tapi diberitahu:

'Pompa akan gagal dalam 48 jam, alasannya:
 - Vibration meningkat 45% (pattern match dengan kegagalan bearing 3 bulan lalu)
 - Temperature naik 8°C (menunjukkan friction meningkat)
 - Arus listrik draw naik 12% (motor bekerja lebih keras)

Aksi yang direkomendasikan: Ganti bearing assembly, part #XYZ-123, biaya Rp 2 juta.
Jika TIDAK diganti: Risk downtime 4 jam, loss Rp 500 juta.
Maintenance window tersedia: Besok jam 10 malam - 2 pagi (off-peak).'

Pak Jerry LANGSUNG paham, LANGSUNG percaya, LANGSUNG ORDER spare part.

Ini yang kami buat: XAI Maintenance Copilot.

[SLIDE: 3 Pillar Architecture]

PredictaGuard punya 3 pilar:

PILLAR 1: REAL-TIME ANOMALY DETECTION
- Kami collect sensor data real-time dari vibration, temperature, current
- LSTM Autoencoder mendeteksi ABNORMAL PATTERNS dalam 60-detik rolling windows
- Bukan threshold sederhana, tapi machine learning yang belajar dari history

PILLAR 2: REMAINING USEFUL LIFE (RUL) PREDICTION  
- Temporal Fusion Transformer predict: 'Mesin ini bisa jalan lagi berapa jam?'
- Dengan 90% confidence interval: Bukan 'mungkin 48 jam', tapi '48 jam ± 12 jam'
- Teknis bisa schedule maintenance saat produksi low-demand

PILLAR 3: EXPLAINABILITY (XAI) - INI YANG UNIQUE
- SHAP library: Setiap anomaly score dijelaskan dengan angka
- 'Alert dikarenakan: vibration 52%, temperature trend 28%, current draw 15%, production load 5%'
- Pak Jerry bisa verify: 'Ya, betul, vibration terasa dari mesin itu'
- Trust = adoption = value realization"

[Pause, transition ke slide]
```

---

### **[TECHNICAL APPROACH - 2-3 menit (Skip jika waktu terbatas)] ⚙️**

```
[SLIDE: Tech Stack Table]

RASYAAD:
"Untuk technical folks di sini, tech stack kami:

[POINT ke tabel]

Kenapa pilihan ini?

LSTM Autoencoder > simple threshold alert:
  Threshold: 'Jika vibration > 12mm/s, alert'
  Problem: False alarm tinggi, missed patterns
  
  LSTM: Mengerti temporal context
  Contoh: vibration GRADUALLY naik dari 8 ke 12 dalam 6 jam = high risk
  vs vibration spike to 13 then back to 9 dalam 2 menit = false alarm

Temporal Fusion Transformer > vanilla LSTM:
  Multi-scale attention mechanism
  Bisa handle multiple sensor types simultaneously
  Outperform vanilla LSTM pada benchmark CMAPSS dataset

SHAP vs surrogate models:
  Mathematically rigorous, model-agnostic
  Consistent local accuracy
  Human-interpretable (tidak blackbox)

Phi-3 Mini on-premise:
  3.8B parameters, run on 16GB RAM server
  TIDAK perlu cloud, data sovereignty terjaga
  CRITICAL untuk food manufacturing (regulatory requirement)

InfluxDB + PostgreSQL:
  InfluxDB: Time-series optimized (sensor data)
  PostgreSQL: Relational (maintenance logs, audit trail)
  Better performance dan scalability daripada single DB"

[Note: Skip ini jika judge tidak technical-focused]
```

---

### **[SOLUTION DEMO / VIDEO - 3-4 menit] 🎥**

```
[SLIDE: Play video mock-up atau live demo]

"Mari lihat dashboard-nya langsung.

[PLAY VIDEO atau LIVE DEMO]

Ini adalah real-time view dari PUMP-01 di Kerry plant.

Kalian lihat di kiri:
- Equipment status: PUMP-01 showing ANOMALY DETECTED (87% confidence)
- RUL indicator: 48 hours remaining
- CCP alert badge: CRITICAL (karena ini pasteurization pump)

Di tengah, sensor metrics:
- Vibration: 12.8 mm/s (ABOVE normal range of 8-10)
- Temperature: 82°C (approaching threshold 85°C)
- Current: 12.5A (slightly elevated, ±2%)

Yang PALING PENTING, di bawah: Explainability section

Kalian lihat SHAP contribution chart:
- Vibration adalah top factor: 52% contribution
- Temperature trend: 28%
- Current draw: 15%
- Production load: 5%

Ini PROVEN yang sebenarnya trigger anomaly.

Di bawah itu, historical pattern match:
- Similar failure pattern detected: 2024-02-10
- Similarity score: 87%
- Time-to-failure dalam kasus itu: 48 hours
- Action itu waktu: Bearing replacement

Rekomendasi action:
- Replace bearing assembly
- Part number: PMP-001-B
- Cost if ignored: USD 2,500
- Potential downtime: 4 hours
- Recommended schedule: Tomorrow 22:00-02:00 UTC

Semua bisa di-send langsung ke WhatsApp team, atau create ticket di system.

CCP alert automatically logged untuk HACCP audit compliance.

[PAUSE]

Ini yang bikin berbeda. Bukan cuma 'WARNING: failure risk 87%',
tapi 'Ini MENGAPA, ini BERAPA cost of inaction, ini cara FIX-nya, ini part number, ini cost'.

Pak Jerry bisa langsung ORDER PART, schedule maintenance, handle audit trail.

Dalam 5 menit lebih responsif daripada 3 hari traditional PM meeting."
```

---

### **[FOOD SAFETY CONTEXT - 1 menit] 🥫**

```
[SLIDE: HACCP diagram]

SHONIA (Business Lead):
"Untuk food manufacturing, compliance adalah CRITICAL.

HACCP (Hazard Analysis Critical Control Points) memerlukan documented control 
di setiap CCP - pasteurization, mixing, cooling, packaging.

Kalau maintenance equipment di CCP gagal, butuh audit trail:
- When did it fail?
- Why did it fail?
- What corrective action taken?
- Who authorized?
- What's the risk to product batch?

PredictaGuard AUTOMATIC generate HACCP log setiap kali ada anomaly di CCP equipment.

Bukan manual entry (prone to error, time-consuming),
tapi automated dari system.

Ini mengurangi food safety risk DAN operational burden compliance."
```

---

### **[BUSINESS CASE - 2 menit] 💰**

```
[SLIDE: ROI calculation]

SHONIA:
"Mari breakdown business case-nya.

BASELINE (Current situation - reactive maintenance):

Operational downtime: 5-7 events per year
Cost per incident: Rp 500 juta (mix of emergency parts, labor, lost production)
Annual emergency repair cost: Rp 2.5-3.5 miliar

Spare parts inventory waste: Rp 200 juta/tahun
Compliance risk: Potentially catastrophic if food safety breach

DENGAN PredictaGuard:

Target: Reduce unplanned downtime to 1-2 events per year
(Reason: Maintenance jadi PLANNED, bukan emergency)

Cost per incident (jika terjadi): Same Rp 500 juta
Annual emergency repair cost: Rp 500-1000 juta = SAVE Rp 1.5-2.5 miliar/tahun

Spare parts waste reduced 60%: Save Rp 120 juta/tahun

IMPLEMENTATION COST:
- System development + integration: Rp 200 juta (one-time)
- Server infrastructure: Rp 50 juta (one-time)
- Annual support + model retraining: Rp 50 juta

PAYBACK PERIOD:
(200 + 50) / (1500 + 120) = 250 / 1620 = ~2 months

After 6 months: Already break-even plus Rp 700 juta net benefit.

YEAR 1 ROI: 
Net benefit (1620 - 100) = Rp 1520 juta
ROI = 1520 / 250 = 608% in first year

Plus: Risk mitigation dari food safety incidents (yang potentially jutaan kerugian).

Jadi dari finance perspective, ini investment yang SANGAT clear-cut positive."

[SLIDE: Timeline gantt]

"Untuk timeline, kami aligned dengan kompetisi:

Phase 1 (Done): Concept design & proposal
Phase 2 (15-30 Juni): Mock-up dashboard video + core ML models
Phase 3 (10 Juli - 31 Juli): Full prototype development + company visit validation
Phase 4 (Aug-Sept): Final submission + live presentation

Semua tools yang kami gunakan open-source atau free-tier.
Tidak ada teknologi experimental.
Team kami punya skill untuk execute semua ini dalam timeline."
```

---

### **[CLOSING & CTA - 1 menit] 🎯**

```
[SLIDE: Thank you slide + team photo]

RASYAAD:
"Jadi untuk summarize:

Kerry Group face real problem: maintenance reactive, cost high, risk to food safety.

Kami propose solution yang UNIQUE: Not just predict, but EXPLAIN dan RECOMMEND.

Technical approach solid: LSTM for anomaly, TFT untuk RUL, SHAP untuk explainability.

Business case strong: Payback dalam 2 bulan, ROI 600%+ tahun pertama.

Team kami ready: 4 skilled engineers, all skill set covered.

Terima kasih sudah mendengar. Kami siap untuk Q&A."

[SLIDE: Q&A slide]

"Ada pertanyaan?"
```

---

## **BAGIAN II: ANTICIPATED Q&A + ANSWER SCRIPT**

### **Q1: Data mana yang kalian gunakan untuk training model?**

**NADINE Answer:**
"Good question. Kami punya 3 source data:

1. **Historical maintenance records dari Kerry**: 
   - MTBF/MTTR logs, work orders, failure modes dari ERP system
   - Kami belum punya akses real data Kerry (belum Phase 3 company visit),
   - Jadi saat ini kami working dengan synthetic data dan public datasets

2. **NASA CMAPSS public dataset**:
   - 6000+ engine degradation cycles
   - Kami gunakan ini untuk pre-training model
   - Ini adalah standard benchmark dalam RUL prediction community
   
3. **Synthetic data augmentation**:
   - Kami generate synthetic sensor streams berdasarkan equipment manufacturer specs
   - Monte Carlo simulation dari degradation curves
   - Ini augment training data untuk equipment types yang sparse history-nya

Untuk Phase 3 (end of July), kami akan visit Kerry plant, 
akses real SCADA/MES data mereka, fine-tune model dengan actual operational patterns.

Strategy ini standard dalam ML practice: Pre-train on public dataset, 
fine-tune on client data."

---

### **Q2: Bagaimana guarantee akurasi model?**

**RASYAAD Answer:**
"Excellent question. Accuracy guarantee di ML always context-dependent.

Untuk PredictaGuard, kami define 2 metrics:

**Anomaly Detection accuracy**:
- Initial target: 80%+ sensitivity (catch real anomalies)
- 90%+ specificity (minimize false alarms yang frustrate teknisi)
- Continuous retraining: Setiap bulan model di-retrain dengan baru data
- Accuracy improve over time (more failure examples, better model)

**RUL Prediction accuracy**:
- Target: ±24 hour window (jika predict 48h failure, actual happen 24-72h)
- Initial 90% confidence interval: Bukan point estimate 'exactly 48h'
  tapi range '48h ±12h'
- Confidence interval shrink over time seiring lebih banyak data

**Safeguard mechanisms**:
- Model never di-deploy langsung tanpa validation terhadap recent historical data
- If model drift detected, alert sent ke ops team
- Manual override capability untuk teknisi (jika confidence low)

**SLA untuk production**:
- Annual maintenance retainer fee tied to SLAs:
  - Uptime goal: 99.5% (max 4.4 hours downtime/month yang unexpected)
  - Prediction accuracy goal: 85%+
- Jika tidak achieve, ada service credit untuk Kerry"

---

### **Q3: Bagaimana scale ke equipment lain atau pabrik lain?**

**RASYAAD Answer:**
"Great question, shows thinking about sustainability.

Architecture kami dirancang MODULAR untuk scalability.

**Horizontal scaling (more equipment):**
- Setiap equipment punya separate MQTT topic di Kafka broker
- Preprocessing pipeline sama untuk semua equipment (just read different topic)
- ML models bisa share architecture tapi separate weights per equipment type
- Adding new pump: Just register new MQTT topic, copy model from existing pump, fine-tune

**Vertical scaling (more plants):**
- Entire stack containerized (Docker)
- Deploy multiple containers di berbagai plant servers
- Central monitoring dashboard di HQ via REST API aggregation
- Data dari setiap plant stay on-premise (sovereignty), only metrics/alerts sync to central

**Technology stack maturity:**
- Kafka: Proven untuk industrial streaming (bank-grade reliability)
- Docker/Kubernetes: Standard container orchestration
- API middleware: Handle protocol conversion antara legacy SCADA systems

**Estimated effort:**
- Phase 1 implementation (Kerry plant 1): 200 juta, 4 bulan (kami sedang lakukan)
- Phase 2 (plant 2): 100 juta, 2 bulan (mostly just deployment + local fine-tuning)
- Phase 3+ (additional plants): ~100 juta each, 1-2 month per plant

So incremental cost/benefit di subsequent plants very attractive."

---

### **Q4: Siapa yang maintain sistem? Apa jika ada masalah?**

**SHONIA Answer:**
"Good operational question.

**Responsibility matrix:**

Infrastructure/Deployment:
- Kerry IT team maintain server, backups, security patches
- (Kami transfer knowledge via documentation + training)

Model updates/optimization:
- Kami (Anomaly Hunters) handle model retraining, testing, deployment
- Monthly cycle: Review new failure data, retrain, validate, push update
- Kerry QA team validate sebelum production (gated release)

24/7 Support:
- For initial 6 months (phase 4-5), kami provide 8/5 support via email/WhatsApp
- After 6 months, transition ke periodic optimization review (monthly)
- SLA: Critical issues (model down) = 4 hour response, 24 hour resolution

Long-term sustainability:
- Kami plan to train 1-2 Kerry IT staff untuk basic model retraining
- Akan provide documented playbook + automated scripts
- Quarterly check-in calls untuk optimize model based pada new failure patterns

**Risk mitigation:**
- Jika kami (startup) dissolved, all code opensource + documented
- Kerry can maintain in-house atau hire other ML vendor
- Source control di GitHub, models di standardized format (PyTorch/ONNX)"

---

### **Q5: Apa terjadi jika data quality Kerry ternyata jelek?**

**NADINE Answer:**
"Honest question, dan we appreciate it.

Kami sudah anticipate ini di proposal. Data quality risk adalah known limitation.

**Mitigation strategy kami:**

1. **Pre-training robustness**:
   - Model trained on CMAPSS public data + synthetic augmentation
   - NOT over-fitted ke Kerry data only
   - So even jika Kerry data sparse/noisy, model punya base knowledge

2. **Incremental improvement**:
   - MVP Phase: Deploy dengan conservative thresholds
   - Production jangan aggressive, false alert OK (better safe than sorry)
   - Collect good quality data for 2-3 bulan
   - Phase 2: Retrain dengan accumulated real data, threshold optimize

3. **Data cleaning workflow**:
   - Preprocessing pipeline built-in outlier detection
   - Maintenance log validation: Kalau ERP entry jelek, flag untuk manual review
   - Iterative improvement dengan Kerry maintenance team feedback

4. **Fallback strategy**:
   - Jika data quality continue suboptimal, pivot ke 'soft sensor' approach
   - Use proxy signals (power draw, acoustic signatures) 
   - atau recommend IoT retrofit (install better sensors)

**Honest timeline adjustment**:
- If data quality issue discovered at Phase 3 company visit,
  we adjust timeline dan adjust scope (focus on fewer equipment types)
  untuk ensure quality over quantity

Data quality is foundation of ML. Better adjust expectation early 
daripada deploy model yang tidak reliable.

We'd rather be honest dan under-promise, over-deliver,
daripada over-promise dan disappoint."

---

### **Q6: Bagaimana kompetisi dengan existing commercial solutions?**

**RASYAAD Answer (Competitive positioning):**
"Great question. Market sudah ada beberapa option.

Existing solutions:
- **General industrial IoT platforms** (Siemens MindSphere, GE Predix, Schneider EcoStruxture):
  ✓ Mature, proven, 24/7 support
  ✗ Generic (tidak optimized untuk food manufacturing)
  ✗ Blackbox predictions (no explainability)
  ✗ Very expensive (jutaan/tahun)
  ✗ Cloud-only (data sovereignty risk untuk food industry)

- **Dedicated predictive maintenance startups** (Lookahead, Augmento, Zebra):
  ✓ Domain-specific
  ✗ Still often lack explainability
  ✗ Limited food safety compliance focus
  ✗ Proprietary models, not transparent

Our advantage:
✓ EXPLAINABILITY: SHAP-based, Pak Jerry paham WHY
✓ FOOD SAFETY: Built-in HACCP compliance, CCP prioritization
✓ DATA SOVEREIGNTY: On-premise LLM, data tidak keluar Kerry network
✓ COST: 250 juta vs 500 juta+ per year dari vendors asing
✓ CUSTOMIZATION: Kami will work closely dengan Kerry untuk fine-tune
✓ TRANSPARENCY: Code well-documented, model interpretable

So positioning kami: Best-fit untuk food manufacturing, 
dengan food safety + explainability as core differentiators.

Not trying to be everything to everyone (like GE Predix),
but BEST solution for Kerry's specific needs."

---

## **BAGIAN III: PRACTICAL CHECKLIST BEFORE PRESENTATION**

### **1 HARI SEBELUM (Jam 17:00 onwards)**

- [ ] **Prepare slides** (Google Slides / PowerPoint)
  - [ ] Opening slide (team + title)
  - [ ] Problem statement dengan cost breakdown
  - [ ] Solution architecture diagram
  - [ ] Dashboard screenshot (atau video)
  - [ ] XAI explanation visual (SHAP bar chart)
  - [ ] Tech stack table
  - [ ] CCP alert screen
  - [ ] Business case ROI calculation
  - [ ] Timeline gantt chart
  - [ ] Team composition slide
  - [ ] Closing slide (QA)
  - [ ] TOTAL: ~20-25 slides

- [ ] **Prepare demo / video**
  - [ ] Mock-up video dashboard (30-60 detik)
  - [ ] Atau: Live demo laptop with backup video jika demo gagal
  - [ ] Test video playback di projector
  - [ ] Audio on video clear

- [ ] **Print materials**
  - [ ] 5-10 copy proposal print (untuk juri)
  - [ ] 1-halaman executive summary (leave-behind)
  - [ ] Business card dengan kontak semua team member

- [ ] **Technical preparation**
  - [ ] Laptop charger bawa
  - [ ] HDMI adaptor + VGA adaptor (jaga-jaga projector compatibility)
  - [ ] USB drive: Semua file backup (presentation, video, proposal PDF)
  - [ ] Wifi test: Pastikan laptop bisa connect ke venue wifi (kalau live demo internet-dependent)

- [ ] **Team rehearsal**
  - [ ] Practice presentasi 3x, role-play setiap orang
  - [ ] Time it: Aim 15-18 menit, max 20
  - [ ] Practice Q&A: 1 orang bertanya, others answer
  - [ ] Clarify role siapa answer Q1, Q2, dst

- [ ] **Personal preparation**
  - [ ] Check weather, outfit (professional business casual)
  - [ ] Sleep well (no late night!)
  - [ ] Prepare water, snacks
  - [ ] Phone on silent mode saat present

---

### **PAGI HARI PRESENTASI (Jam 06:00-07:00)**

- [ ] **Final checks**
  - [ ] Laptop battery charged 100%
  - [ ] Presentation open, slide 1 ready
  - [ ] Video file confirmed playable
  - [ ] Slide presenter notes di masing-masing speaker laptop
  - [ ] Whiteboard markers available (jika ada Q&A yang butuh drawing)

- [ ] **Arrival at venue (15 menit early)**
  - [ ] Find registration, check slot time
  - [ ] Locate presentation room
  - [ ] Test projector + audio
  - [ ] Test mouse/clicker
  - [ ] Walk through floor plan (jangan tersesat)

- [ ] **Mental preparation**
  - [ ] Deep breath, calm down
  - [ ] Remind team: "Kita udah prepare dengan baik, tinggal deliver"
  - [ ] Positive mindset

---

### **SAAT PRESENTASI (15-20 menit)**

**[0-2 min: Opening]**
- Rasyaad introduce team + problem severity

**[2-5 min: Problem]**
- Nadine explain maintenance challenge, cost breakdown

**[5-8 min: Solution architecture]**
- Rasyaad explain 3 pillars, high-level approach

**[8-12 min: Demo/Video]**
- Nadine/Rasyaad: Play video atau live demo dashboard
- Point out: XAI, RUL, CCP alert

**[12-15 min: Business case + Timeline]**
- Shonia: ROI, payback, timeline

**[15-18 min: Risk mitigation + Scalability]**
- Rasyaad: How handle data quality, how scale

**[18-20 min: Team + Closing]**
- Shonia show team slide
- Rasyaad close with call to action

**[20+ min: Q&A]**
- Listen carefully
- Answer specific, not rambling
- If tidak tahu, jujur: "Good question, kita research dulu dan follow-up"

---

### **AFTER PRESENTATION**

- [ ] **Collect business cards** dari juri (jika ada)
- [ ] **Thank you gesture** (beri proposal print ke main juri/organizer)
- [ ] **Team photo** dengan juri (jika ditawarkan)
- [ ] **Timeline follow-up** (jika ada next-round interview, catat schedulenya)

---

## **BAGIAN IV: SLIDE DECK OUTLINE (Detailed)**

```
SLIDE 1: Title Slide
┌─────────────────────────────────────────────────┐
│ PREDICTAGUARD                                   │
│ AI-Powered Predictive Maintenance for Kerry   │
│ Anomaly Hunters Team                            │
│ Rasyaad | Nadine | Nor Umayah | Shonia         │
│ AI Open Innovation Challenge 2026               │
└─────────────────────────────────────────────────┘

SLIDE 2: Opening Hook
[Gambar: pompa rusak, maintenance engineer stressed]
Text: "$500K downtime. 5-7x per year. No early warning."
Call: "What if you could predict 48 hours before?"

SLIDE 3: Kerry Group Profile
- Leading food manufacturer (900M+ products/year)
- Multiple facilities worldwide
- Critical focus: Food safety + operational excellence

SLIDE 4: Problem - Timeline Maintenance
[Diagram showing: Time-based = reactive]
- Pump scheduled service: every 6 months
- But fails at month 5 or month 8 (unpredictable)

SLIDE 5: Cost Breakdown
- Emergency repair: Rp 5-7M per incident
- Downtime: Rp 500M per incident (lost production)
- 5-7 incidents/year = Rp 2.5-3.5B annually
- Spare parts waste: Rp 200M

SLIDE 6: Solution - PredictaGuard Overview
[Architecture diagram: Sensors → Kafka → ML → Dashboard]
3 Pillars: Anomaly Detection | RUL Prediction | Explainability (XAI)

SLIDE 7: Technical Approach
[Table: Tech stack rationale]

SLIDE 8: Dashboard Mock-up
[Screenshot atau video]

SLIDE 9: XAI Explanation Example
[SHAP bar chart visualization]

SLIDE 10: RUL Prediction
[Time-series forecast chart]

SLIDE 11: Food Safety Integration
[CCP alert + HACCP log generation]

SLIDE 12: Competitive Positioning
[Table: PredictaGuard vs existing solutions]

SLIDE 13: ROI Calculation
Baseline: Rp 2.5B emergency costs/year
With PredictaGuard: Rp 500M/year
Implementation cost: Rp 250M
Payback: 2 months
Year 1 ROI: 608%

SLIDE 14: Timeline
Phase 1 (Done): Concept
Phase 2 (15-30 Juni): Mock-up
Phase 3 (10-31 Juli): Prototype + validation
Phase 4 (Aug-Sept): Final submission

SLIDE 15: Team Composition
[Photo + roles]

SLIDE 16: Risk Mitigation
- Data quality: Pre-training + synthetic data
- Scalability: Modular, containerized
- Support: Clear SLAs, knowledge transfer

SLIDE 17: Next Steps & CTA
- Phase 2 mock-up video (30 Juni)
- Phase 3 company visit & validation (late July)
- Final prototype (31 Juli)
- Live demonstration available

SLIDE 18: Thank You / Q&A
[Contact info]
```

---

## **SUMMARY: CHECKLIST PRESENTASI BESOK**

**The 3 Keys to Winning Presentation:**

1. **CLARITY**: Juri harus paham problem dan solution dalam 2 menit
   → Use concrete numbers, relatable examples (Pak Jerry)

2. **CREDIBILITY**: Show technical depth tanpa over-explain
   → Tech stack justified, risk mitigation planned, data quality acknowledged

3. **COMPELLING**: Leave them wanting to know more
   → Clear ROI, unique differentiators (XAI + food safety), achievable timeline

**If presentations nervous, remember:**
- You've prepared well
- You know the content deeply
- Juri WANT anda succeed (they funded this)
- Just tell the story clearly, answer Q honestly

**Good luck 💪**

