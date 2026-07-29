# MaintenX — AI-Powered Predictive Maintenance Platform
## Executive Technical Presentation & Solution Architecture Master Blueprint for ASTRA

> [!NOTE]
> **Alur Presentasi Solution Architect:**
> Problem → Limitation → Dataset → Database → Data Pipeline → AI Models → Decision Engine → Performance → Dashboard Demo → Q&A

---

## 📋 Table of Contents Slide Deck

1. [Slide 1: Title & Introduction](#slide-1-title--introduction)
2. [Slide 2: Project Overview](#slide-2-project-overview)
3. [Slide 3: Project Limitation (PoC Baseline vs Future Astra)](#slide-3-project-limitation-poc-baseline-vs-future-astra)
4. [Slide 4: Dataset Overview](#slide-4-dataset-overview)
5. [Slide 5: Paderborn Dataset Details](#slide-5-paderborn-dataset-details)
6. [Slide 6: CWRU Dataset Details](#slide-6-cwru-dataset-details)
7. [Slide 7: NASA IMS Dataset (Health Degradation)](#slide-7-nasa-ims-dataset-health-degradation)
8. [Slide 8: NASA CMAPSS & Multi-Dataset Harmonization](#slide-8-nasa-cmapss--multi-dataset-harmonization)
9. [Slide 9: Database Entity Relationship Diagram (ERD)](#slide-9-database-entity-relationship-diagram-erd)
10. [Slide 10: General System Flow & Execution Pipelines](#slide-10-general-system-flow--execution-pipelines)
11. [Slide 11: AI Models Cascade Architecture](#slide-11-ai-models-cascade-architecture)
12. [Slide 12: Model A1 — Anomaly Detection](#slide-12-model-a1--anomaly-detection)
13. [Slide 13: Model A2 — Fault Classification](#slide-13-model-a2--fault-classification)
14. [Slide 14: Model B — Remaining Useful Life (RUL) Prediction](#slide-14-model-b--remaining-useful-life-rul-prediction)
15. [Slide 15: Decision Engine & False Alarm Suppression](#slide-15-decision-engine--false-alarm-suppression)
16. [Slide 16: Model Evaluation & System Performance](#slide-16-model-evaluation--system-performance)
17. [Slide 17: Dashboard Live Demo & Operational Walkthrough](#slide-17-dashboard-live-demo--operational-walkthrough)
18. [Slide 18: Q&A & Integration Next Steps](#slide-18-qa--integration-next-steps)

---

### Slide 1: Title & Introduction

#### 📄 Slide Content
- **Title**: MaintenX
- **Subtitle**: AI-Powered Predictive Maintenance Platform
- **Target Enterprise**: ASTRA Industrial Operations
- **Team**: Solution Architecture & AI Engineering Team

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Selamat pagi jajaran manajemen ASTRA Industrial Operations. Hari ini tim Solution Architect kami mempresentasikan **MaintenX** — platform Predictive Maintenance berbasis AI yang dirancang khusus untuk mendeteksi keausan dan potensi kerusakan mesin industri sebelum terjadi kegagalan fatal.*
> *Tujuan utama project ini adalah mentransformasi perawatan mesin dari reaktif/terjadwal menjadi terprediksi secara akurat dan real-time."*

---

### Slide 2: Project Overview

#### 📄 Slide Content
- **Objective**: Membangun platform Predictive Maintenance berbasis AI terintegrasi untuk mencegah unplanned downtime.
- **Problem Statement**: Kerusakan mendadak pada mesin industri (motor induksi/bearing) mengakibatkan biaya perbaikan mahal, hilangnya kapasitas produksi, dan bahaya keselamatan.
- **Expected Output**: Rekomendasi tindakan maintenance presisi (Normal, Warning, Critical) beserta prediksi waktu sisa umur (RUL) dan sistem alert otomatis.

#### 📊 Architecture Concept Diagram
```
Induction Motor ──► Sensor Data ──► AI Analysis ──► Maintenance Decision
```

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Project ini dibuat karena unplanned downtime pada motor induksi pabrik sangat mahal. Masalah utamanya adalah kegagalan mekanis mendadak pada komponen kritis.*
> *Sistem MaintenX bekerja dengan mengambil sinyal sensor, dianalisis oleh pipeline multi-stage AI, dan menghasilkan **Output Akhir** berupa rekomendasi maintenance konkret bagi tim di lapangan."*

---

### Slide 3: Project Limitation (PoC Baseline vs Future Astra)

#### 📄 Slide Content (Comparison Table)

| Komponen Sistem | Current PoC (Baseline Prototype) | Future Astra Integration |
| :--- | :--- | :--- |
| **Sensor Data Source** | Public Benchmark Datasets (Paderborn, CWRU, IMS, CMAPSS) | Real IoT Vibration, Current & Temp Sensors Astra |
| **Database System** | Simulated Relational In-Memory / Local PostgreSQL | Enterprise Astra Database & Data Lake |
| **User Dashboard** | Prototype Web Dashboard (SPA with XAI Diagnostics) | Production Enterprise Dashboard (Single Sign-On) |
| **Notification System** | Simulated SMTP Email & In-App Toast Engine | Production Work Order CMMS & Astra Push Notification |

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Penting untuk dipahami bahwa pada tahap PoC Baseline saat ini, kami belum memiliki akses langsung ke sensor dan database internal Astra, sehingga kami menggunakan 4 dataset publik terstandar sebagai baseline.*
> *Keunggulan arsitektur MaintenX adalah sifatnya yang **modular**: Ketika nantinya diimplementasikan di infrastruktur Astra, seluruh pipeline AI dan Decision Engine tetap sama — **yang berubah hanyalah data source yang beralih ke sensor Astra**."*

---

### Slide 4: Dataset Overview

#### 📄 Slide Content

| Dataset | Target Machine | Purpose in MaintenX |
| :--- | :--- | :--- |
| **Paderborn** | Induction Motor (1.5 kW) | Fault Classification (Stator Current & Vibration) |
| **CWRU** | Bearing Test Motor (2 HP) | High-Precision Bearing Fault Diagnosis |
| **NASA IMS** | Bearing Test Rig | Health Degradation & Health Index Baseline |
| **NASA CMAPSS** | Turbofan Engine | Remaining Useful Life (RUL) Prediction |

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Kami menggabungkan studi dari empat dataset industri terkemuka. Mengapa menggunakan 4 dataset? Karena **tidak ada satu dataset tunggal di dunia yang memenuhi seluruh kebutuhan predictive maintenance**.*
> *Paderborn memberikan karakteristik motor induksi, CWRU mendiagnosis keretakan spesifik bearing, NASA IMS memodelkan degradasi berbulan-bulan hingga rusak total, dan NASA CMAPSS memodelkan perkiraan sisa umur (RUL)."*

---

### Slide 5: Paderborn Dataset Details

#### 📄 Slide Content
- **Machine**: Induction Motor (1.5 kW, variable load & frequency)
- **Available Sensors**: Phase Currents (64kHz), Accelerometer Vibration, Temperature, Speed
- **Fault Types**: Real Accelerated Damage (pitting, fatigue, inner/outer race defects)
- **Features Used**: 25 Time & Frequency Domain Features (RMS, Kurtosis, Crest Factor, Energy Spectrum)

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Dataset Paderborn berfokus pada motor induksi. Sensor utama yang digunakan adalah arus listrik stator dan getaran. Dari sinyal mentah ini, kami mengesktrak 25 fitur fisik untuk membedakan kondisi normal dan indikasi awal kerusakan mekanis."*

---

### Slide 6: CWRU Dataset Details

#### 📄 Slide Content
- **Machine**: Reliance Electric Motor Test Rig (2 HP)
- **Bearing Fault Types**: Single-Point Defect (Ball Fault, Inner Race Fault, Outer Race Fault)
- **Available Features**: Drive-End & Fan-End Accelerometer Vibration Signals (12k/48k Hz)
- **Purpose**: High-precision 10-class bearing fault classification

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"CWRU berfokus khusus pada bearing fault. Dataset ini kami gabungkan dengan Paderborn untuk memperkuat akurasi klasifikasi kerusakan spesifik pada bola bearing, inner race, maupun outer race."*

---

### Slide 7: NASA IMS Dataset (Health Degradation)

#### 📄 Slide Content
- **Experiment Mode**: Continuous Run-to-Failure Test (35 days uninterrupted run until catastrophic failure)
- **Degradation Target**: Bearing Structural Degradation Curve
- **Available Features**: High-Frequency Vibration Telemetry
- **Purpose**: Baseline for Health Index Calculation (0% to 100%)

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"NASA IMS memberikan gambaran bagaimana komponen terdegradasi seiring waktu selama 35 hari berturut-turut. Dataset ini menjadi dasar bagi algoritma kami dalam menghitung **Health Index** mesin dari 100% (sehat) menurun ke 0% (kritis)."*

---

### Slide 8: NASA CMAPSS & Multi-Dataset Harmonization

#### 📄 Slide Content
- **Top Section**: Remaining Useful Life (RUL) | Multi-Sensor Telemetry | Sequential Sliding Window Features
- **Mapping Flow**:
```
Paderborn ──► CWRU ──► NASA IMS ──► NASA CMAPSS ──► raw_sensor_data
```

- **Harmonized Database Table Schema (`raw_sensor_data`)**:

| timestamp | machine_id | vibration | current | rpm | temperature | torque | source_dataset |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `2026-07-30 00:00:00` | `MTR-01` | `0.42` | `22.4` | `1450` | `48.5` | `NULL` | `paderborn` |

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Pertama, NASA CMAPSS digunakan khusus untuk estimasi Remaining Useful Life (RUL).*
> *Selanjutnya, karena setiap dataset memiliki struktur yang berbeda-beda, kami merancang **Dataset Harmonization**: Seluruh dataset dipetakan ke satu tabel tunggal `raw_sensor_data`.*
> *Jika suatu dataset tidak memiliki parameter tertentu (misal: torque), maka nilainya diisi `NULL`.*
> *Struktur ini dibuat agar pipeline AI tetap sama walaupun sumber data berbeda. **Saat nanti menggunakan data sensor Astra, hanya kolom `source_dataset` yang beralih menjadi `astra_sensor`.** Transisi ini sangat natural menuju arsitektur database (ERD)."*

---

### Slide 9: Database Entity Relationship Diagram (ERD)

#### 📄 Slide Content (ERD Flow Diagram)
```
[raw_sensor_data] ──(Cleaning 30s)──► [clean_sensor_data] ──(Feature Eng)──► [feature_dataset]
                                                                                   │
                                                                             (AI Models 5m)
                                                                                   ▼
[alerts_history] ◄──────(Decision Engine)──────────────────────────── [prediction_results]
```

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Ini adalah Entity Relationship Diagram (ERD) sistem kami. Data mentah ditampung di `raw_sensor_data`, dibersihkan ke `clean_sensor_data`, diekstrak fiturnya ke `feature_dataset`, lalu hasil inferensi AI disimpan di `prediction_results` dan memicu log tindakan pada `alerts_history`."*

---

### Slide 10: General System Flow & Execution Pipelines

#### 📄 Slide Pipeline Chart
```
Sensors ──► PLC / Gateway ──► raw_sensor_data ──► Cleaning Engine (30s) ──► clean_sensor_data ──► Feature Eng ──► feature_dataset ──► AI Scheduler (5m) ──► AI Models ──► Decision Engine ──► Dashboard ──► Maintenance Team
```

#### 🗣️ Yang Dijelaskan secara Detail (Speaker Script)
1. **Sensors & Gateway**:
   > *"Sensor membaca data secara terus menerus (Temperature, Vibration, Current, RPM, Torque). Data dikirim via PLC dan IoT Gateway menuju tabel `raw_sensor_data`."*
2. **Cleaning Engine (Setiap 30 detik)**:
   > *"Setiap 30 detik, Scheduler Python via SQLAlchemy mengambil data mentah. Pandas melakukan validasi data, deduplikasi, penanganan missing value, penyelarasan timestamp, dan noise filtering.*
   > *Selanjutnya dilakukan **Aggregation**: Temperature -> Average, Current -> Average, RPM -> Median, Vibration -> RMS. Hasilnya digabung menjadi **SATU BARIS BERSIH** pada `clean_sensor_data`. Mengapa? Karena model AI membutuhkan timestamp yang seragam untuk seluruh parameter."*
3. **Feature Engineering**:
   > *"Mengambil `clean_sensor_data` dan mengekstrak fitur fisik: Rolling Mean, Rolling Std, RMS, FFT, Peak, Kurtosis yang disimpan di `feature_dataset`. Mengapa? Karena AI bekerja jauh lebih akurat dengan fitur fenomena fisik daripada data mentah."*
4. **Scheduler Model (Setiap 5 menit)**:
   > *"Setiap 5 menit, Scheduler kedua berjalan mengambil `feature_dataset` dan memasukkannya ke AI Model. Mengapa setiap 5 menit? Karena inferensi setiap detik akan sangat membebani server tanpa memberikan nilai tambah pada degradasi mekanis yang terjadi perlahan."*

---

### Slide 11: AI Models Cascade Architecture

#### 📄 Slide Content
```
[feature_dataset] ──► [Model A1: Anomaly Detector] ──► [Model A2: Fault Classifier] ──► [Model B: RUL Estimator]
```

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Seluruh fitur yang telah diekstrak akan diproses secara berurutan (*Cascade Pipeline*) oleh ketiga model AI: Model A1 menentukan ada/tidaknya anomali, Model A2 mendiagnosis jenis kerusakan, dan Model B menghitung perkiraan sisa umur komponen."*

---

### Slide 12: Model A1 — Anomaly Detection

#### 📄 Slide Content
- **Dataset**: SKAB & Paderborn Sensor Baseline
- **Algorithm**: Unsupervised LSTM Autoencoder / Random Forest
- **Input**: 25 Rolling Time & Frequency Domain Features
- **Output**: Anomaly Score & Binary Flag (0: Normal, 1: Anomaly)
- **Workflow**: Reconstruction Error vs Dynamic Threshold (1.005)

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Model A1 merekonstruksi sinyal sensor normal. Jika selisih reconstruction loss melebihi threshold, sistem memicu indikasi awal deviasi kondisi mesin."*

---

### Slide 13: Model A2 — Fault Classification

#### 📄 Slide Content
- **Dataset**: CWRU Bearing & Paderborn Motor Faults
- **Algorithm**: Supervised Gradient Boosting / MLP Classifier
- **Input**: Cleaned Vibration FFT Spectrum & Stator Current
- **Output**: Specific Fault Category (Healthy, Inner Race, Outer Race, Roller)
- **Workflow**: 10-Class Probability Softmax Scoring

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Model A2 mengklasifikasikan lokasi pasti titik kerusakan mekanis (misal: inner race vs outer race) dengan akurasi teruji 88.4% pada pengujian multi-kelas industri."*

---

### Slide 14: Model B — Remaining Useful Life (RUL) Prediction

#### 📄 Slide Content
- **Dataset**: NASA CMAPSS Turbofan FD001
- **Algorithm**: Deep LSTM Regressor dengan Asymmetric Loss
- **Input**: 30-Step Sequential Multi-Sensor Time-Series
- **Output**: RUL Remaining Hours / Cycles
- **Workflow**: Sequence Modeling with NASA Early Prediction Loss Penalty

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Model B memprediksi sisa umur komponen (RUL). Kami menerapkan NASA Asymmetric Loss Function untuk memberikan penalti tinggi pada keterlambatan prediksi, sehingga menjamin keselamatan operasional pabrik."*

---

### Slide 15: Decision Engine & False Alarm Suppression

#### 📄 Slide Flow Chart
```
Prediction ──► Business Rules ──► Persistence Check ──► Context Validation ──► False Alarm Suppression ──► Alert Cooldown ──► Maintenance Recommendation ──► Email Notification ──► Dashboard
```

#### 🗣️ Yang Dijelaskan secara Berurutan (Speaker Script)
1. **Business Rules**: *"Menentukan aturan dasar batas daya/RPM berdasarkan jenis mesin."*
2. **Persistence Check**: *"Alarm harus muncul beberapa kali berturut-turut untuk memastikan bukan transient spike."*
3. **Context Validation**: *"Memastikan kondisi sesuai konteks operasional mesin (misal: saat startup vs steady state)."*
4. **False Alarm Suppression**: *"Menggabungkan hasil Model A1, A2, dan B. Alarm hanya dikirim jika hasil prediksi ketiga model saling mendukung."*
5. **Alert Cooldown**: *"Mencegah spam email notifikasi ke tim maintenance."*
6. **Maintenance Recommendation**: *"Menentukan status Normal, Warning, atau Critical. Jika Critical ➔ Mengirim Email Notifikasi & Menampilkan Work Order di Dashboard."*

---

### Slide 16: Model Evaluation & System Performance

#### 📄 Slide Performance Table

| Evaluation Metric | Industrial Benchmark Value | Evaluation Note |
| :--- | :--- | :--- |
| **Overall Test Accuracy** | **88.4%** | Tested on 10-class bearing & motor fault datasets |
| **Precision Rate** | **92.4%** | High precision to prevent unnecessary replacement |
| **Recall Rate** | **88.6%** | High sensitivity for early micro-fault detection |
| **Weighted F1 Score** | **0.882** | Harmonic mean across balanced/imbalanced classes |
| **RUL Prediction MAE** | **10.24 cycles** | CMAPSS FD001 benchmark evaluation error margin |
| **False Alarm Reduction** | **94.2%** | Achieved via Decision Engine multi-layer consensus rules |
| **Inference Latency** | **12.5 ms** | Ultra-fast inference latency for streaming ingestion |

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Model dievaluasi secara ketat dengan akurasi 88.4%, F1 Score 0.882, kemampuan pengurangan False Alarm hingga 94.2% melalui Decision Engine, serta latensi inferensi ultra-cepat 12.5 ms."*

---

### Slide 17: Dashboard Live Demo & Operational Walkthrough

#### 📄 Slide Demo Scenario Flow
```
Overview ──► Machine Monitoring ──► Machine Detail ──► Prediction ──► Recommendation ──► History ──► Notification
```

#### 🗣️ Yang Dijelaskan (Speaker Script & Skenario Nyata)
> *"Mari kita lihat skenario penggunaan nyata:*
> 1. *Supervisor membuka halaman **Overview** dan melihat KPI Overall Health (46%) dan kartu CCP At Risk.*
> 2. *Supervisor menuju **Machine Monitoring** dan melihat Motor MTR-01 berstatus Critical.*
> 3. *Membuka halaman **Machine Detail** & **Prediction**, melihat grafik getaran naik signifikan dan RUL tersisa 5 hari.*
> 4. *Membaca **Recommendation** tindakan penggantian bearing.*
> 5. *Sistem secara otomatis telah mengirimkan **Email Notification** ke maintenance engineer dan membuat Work Order jadwal perawatan sebelum terjadi breakdown."*

---

### Slide 18: Q&A & Integration Next Steps

#### 📄 Slide Content
- **MaintenX Solution Architecture & Engineering Team**
- **Open Technical Discussion & Q&A Session**
- **Target Integrasi**: Rencana uji coba konektivitas IoT Gateway & Database Astra.

#### 🗣️ Yang Dijelaskan (Speaker Script)
> *"Sekian presentasi arsitektur teknik MaintenX untuk ASTRA. Kami sangat antusias untuk mendiskusikan rencana integrasi lebih lanjut. Kami membuka sesi tanya jawab. Terima kasih!"*
