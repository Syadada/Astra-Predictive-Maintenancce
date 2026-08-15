import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Polygon, Group, Path

BASE_DIR = r"c:\Users\rasyaad\Downloads\PredictaGuard-main\PredictaGuard-main"
TARGET_DIR = os.path.join(BASE_DIR, "15-08-2026")
os.makedirs(TARGET_DIR, exist_ok=True)
PDF_PATH = os.path.join(TARGET_DIR, "PredictaGuard_System_Documentation_Technical_Report.pdf")

# Custom Canvas for Page Numbers & Headers
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Suppress headers/footers on cover page
            return

        self.saveState()
        self.setFont("Times-Roman", 10)
        self.setFillColor(colors.HexColor("#333333"))

        # Footer Page Number
        if self._pageNumber == 2:
            page_text = "i"
        else:
            page_text = str(self._pageNumber - 2)

        self.drawCentredString(letter[0] / 2.0, 0.5 * inch, page_text)
        self.restoreState()


def create_presuniv_logo():
    d = Drawing(220, 220)
    
    # Outer Red Rounded Border Frame
    d.add(Rect(10, 10, 200, 200, rx=35, ry=35, fillColor=colors.white, strokeColor=colors.HexColor("#bd1e2d"), strokeWidth=6))
    
    # Inner Geometric Blue Emblem (Shield / Lotus)
    p = Path(fillColor=colors.white, strokeColor=colors.HexColor("#0f4c81"), strokeWidth=4)
    # Lotus petals / shield geometry
    p.moveTo(110, 45)
    p.curveTo(150, 80, 170, 120, 110, 175)
    p.curveTo(50, 120, 70, 80, 110, 45)
    d.add(p)
    
    p2 = Path(fillColor=None, strokeColor=colors.HexColor("#0f4c81"), strokeWidth=4)
    p2.moveTo(110, 45)
    p2.curveTo(175, 90, 175, 140, 110, 175)
    p2.curveTo(45, 140, 45, 90, 110, 45)
    d.add(p2)

    p3 = Path(fillColor=None, strokeColor=colors.HexColor("#0f4c81"), strokeWidth=3)
    p3.moveTo(60, 110)
    p3.lineTo(160, 110)
    d.add(p3)

    # Text below emblem inside frame
    d.add(String(110, 30, "PRESIDENT", textAnchor="middle", fontName="Times-Bold", fontSize=15, fillColor=colors.HexColor("#bd1e2d")))
    d.add(String(110, 16, "UNIVERSITY", textAnchor="middle", fontName="Times-Roman", fontSize=12, fillColor=colors.HexColor("#0f4c81")))
    
    return d


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_PATH,
        pagesize=letter,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles matching academic template
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=24,
        leading=28,
        alignment=1, # Center
        textColor=colors.black,
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=15,
        leading=18,
        alignment=1,
        textColor=colors.black,
        spaceAfter=10
    )
    
    case_study_style = ParagraphStyle(
        'CoverCaseStudy',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=11,
        leading=14,
        alignment=1,
        textColor=colors.black,
        spaceAfter=6
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=14,
        leading=18,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.black
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=12,
        leading=15,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.black
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=11,
        leading=15,
        spaceAfter=8,
        alignment=4 # Justified
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=11,
        leading=15,
        leftIndent=18,
        spaceAfter=4
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Times-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.black
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10,
        leading=13,
        textColor=colors.black
    )

    story = []

    # ==========================================
    # PAGE 1: COVER PAGE
    # ==========================================
    story.append(Spacer(1, 0.2 * inch))
    story.append(create_presuniv_logo())
    story.append(Spacer(1, 0.4 * inch))
    
    story.append(Paragraph("PredictaGuard SmartMaint AI", title_style))
    story.append(Paragraph("System Documentation & Technical Report", subtitle_style))
    story.append(Paragraph("Case Study: Astra Otoparts - Predictive Maintenance for Bearing & Motor Failure", case_study_style))
    story.append(Paragraph("Source Code: https://github.com/rasyaad/PredictaGuard-ASTRA", case_study_style))
    
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Prepared by:", ParagraphStyle('PrepBy', fontName='Times-Roman', fontSize=11, alignment=1, spaceAfter=10)))
    
    prep_data = [
        [Paragraph("Azzahra Puteri Kamilah", case_study_style), Paragraph("012202400070", case_study_style)],
        [Paragraph("Fasya Nabila Salim", case_study_style), Paragraph("012202400012", case_study_style)],
        [Paragraph("Marchella Keira Sambuaga", case_study_style), Paragraph("012202400010", case_study_style)],
        [Paragraph("Ryantinisa Guzelazkia", case_study_style), Paragraph("012202400106", case_study_style)],
    ]
    t_prep = Table(prep_data, colWidths=[2.2 * inch, 1.5 * inch])
    t_prep.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_prep)
    
    story.append(Spacer(1, 0.6 * inch))
    story.append(Paragraph("Faculty of Computer Science", case_study_style))
    story.append(Paragraph("President University", case_study_style))
    story.append(PageBreak())

    # ==========================================
    # PAGE 2: TABLE OF CONTENTS
    # ==========================================
    story.append(Paragraph("Table of Contents", ParagraphStyle('TOCHeading', fontName='Times-Bold', fontSize=16, leading=20, alignment=1, spaceAfter=10)))
    
    toc_items = [
        ("Table of Contents", "i"),
        ("1. Executive Summary", "1"),
        ("2. Introduction", "1"),
        ("    2.1 Background", "1"),
        ("    2.2 Problem Statement", "2"),
        ("    2.3 Objectives", "2"),
        ("3. System Architecture", "2"),
        ("    3.1 Data Flow", "3"),
        ("    3.2 Technology Stack", "3"),
        ("    3.3 Design Rationale", "4"),
        ("4. Machine Learning Methodology", "4"),
        ("    4.1 Input Features", "4"),
        ("    4.2 Model Architecture", "5"),
        ("    4.3 Evaluation Methodology", "5"),
        ("5. Model Evaluation Results", "6"),
        ("    5.1 Interpretation", "6"),
        ("6. System Design: User Roles & Access Control", "7"),
        ("    6.1 Role Responsibilities", "7"),
        ("7. Core Workflow: Work Order Lifecycle", "8"),
        ("    7.1 State Sequence", "8"),
        ("    7.2 Step-by-Step Description", "8"),
        ("8. Feature Documentation", "9"),
        ("    8.1 Dashboard", "9"),
        ("    8.2 Fleet Monitoring", "9"),
        ("    8.3 AI Prediction", "9"),
        ("    8.4 Maintenance Advisor", "9"),
        ("    8.5 Maintenance Calendar", "9"),
        ("    8.6 Alert Center", "10"),
        ("    8.7 Asset Inventory", "10"),
        ("    8.8 Reports Module", "10"),
        ("    8.9 AI Copilot", "10"),
        ("    8.10 PLC & Configuration", "10"),
        ("9. Testing & Verification", "10"),
        ("10. Known Limitations", "11"),
        ("11. Conclusion", "11"),
    ]
    
    toc_data = []
    for title, pg in toc_items:
        is_main = not title.startswith("    ")
        font_name = "Times-Bold" if is_main else "Times-Roman"
        p_title = Paragraph(title.strip(), ParagraphStyle('TOCItem', fontName=font_name, fontSize=10, leading=12.5))
        p_pg = Paragraph(pg, ParagraphStyle('TOCPg', fontName=font_name, fontSize=10, leading=12.5, alignment=2))
        toc_data.append([p_title, p_pg])
        
    t_toc = Table(toc_data, colWidths=[5.5 * inch, 1.0 * inch])
    t_toc.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
        ('TOPPADDING', (0,0), (-1,-1), 1.5),
    ]))
    story.append(t_toc)
    story.append(PageBreak())

    # ==========================================
    # PAGE 3: EXECUTIVE SUMMARY & INTRODUCTION
    # ==========================================
    story.append(Paragraph("1. Executive Summary", h1_style))
    story.append(Paragraph("PredictaGuard SmartMaint AI is a predictive maintenance web application that monitors the health of industrial induction motors and bearing assets in real time and forecasts failures before they occur. The system integrates three machine learning models: a Histogram Gradient Boosting / Random Forest classifier that identifies the type of an impending failure, a Gradient Boosting regressor that estimates the Remaining Useful Life (RUL) of a component, and an Isolation Forest that performs unsupervised anomaly detection on incoming telemetry patterns.", body_style))
    story.append(Paragraph("All three models are trained on industrial sensor telemetry (temperature, vibration RMS, kurtosis, phase current, voltage, RPM, and crest factor) using a machine-level train/test split, which prevents data leakage between machines seen during training and those used for evaluation. The failure-type classifier achieves 99.85% accuracy (macro F1 99.6%), and the anomaly detector achieves a ROC-AUC of 0.984, evaluated on held-out machines the models never saw during training.", body_style))
    story.append(Paragraph("Beyond the analytics layer, the system implements a complete role-based maintenance workflow: operators raise work requests, managers review and approve them, technicians execute and report on the work, and managers verify completion with every transition enforced by server-side authorization rules, not just hidden UI elements.", body_style))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("2. Introduction", h1_style))
    story.append(Paragraph("2.1 Background", h2_style))
    story.append(Paragraph("Industrial maintenance strategies traditionally fall into two categories. Reactive maintenance waits for equipment to fail before repairing it, which causes unplanned downtime and can allow secondary damage to propagate through a machine. Scheduled preventive maintenance services equipment at fixed time intervals regardless of its actual condition, which wastes labor and replaces components that are still serviceable. Both approaches ignore the condition data that modern sensors already make available.", body_style))
    story.append(Paragraph("Predictive maintenance addresses this gap by continuously monitoring equipment condition and using statistical or machine-learning models to estimate when intervention will actually be needed, combining the cost efficiency of condition-based servicing with the safety of early warning.", body_style))

    # ==========================================
    # PAGE 4: PROBLEM STATEMENT & OBJECTIVES & SYSTEM ARCHITECTURE
    # ==========================================
    story.append(Paragraph("2.2 Problem Statement", h2_style))
    story.append(Paragraph("This project addresses the academic requirement defined as Use Case 2: Predictive Maintenance for Induction Motor Failure which specifies the following scope:", body_style))
    story.append(Paragraph("• Multi-parameter condition monitoring of industrial equipment", bullet_style))
    story.append(Paragraph("• AI-based pattern recognition for failure-mode identification", bullet_style))
    story.append(Paragraph("• Intelligent reduction of false alarms", bullet_style))
    story.append(Paragraph("• Remaining Useful Life (RUL) estimation", bullet_style))
    story.append(Paragraph("• Real-time health scoring", bullet_style))
    story.append(Paragraph("• Automated alerts and maintenance recommendations", bullet_style))
    story.append(Paragraph("PredictaGuard SmartMaint AI addresses every point above through an interconnected set of modules, rather than a single standalone dashboard. The platform covers the full operational loop from anomaly detection to work order closure by a technician.", body_style))

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("2.3 Objectives", h2_style))
    story.append(Paragraph("• Build a machine learning pipeline that classifies failure types, estimates RUL, and detects anomalies from motor telemetry with production-usable accuracy.", bullet_style))
    story.append(Paragraph("• Design a role-based maintenance workflow that mirrors how a real plant reliability team actually operates (request → approval → execution → verification).", bullet_style))
    story.append(Paragraph("• Deliver the system as a self-contained, on-premise deployable application with no mandatory cloud dependency for its core analytics.", bullet_style))
    story.append(Paragraph("• Provide an AI assistant (copilot) that can answer natural-language questions grounded in the live plant database.", bullet_style))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("3. System Architecture", h1_style))
    story.append(Paragraph("PredictaGuard SmartMaint AI is delivered as a single full-stack, on-premise application. The only external dependency is the optional Google Gemini API, used for the AI Copilot and AI-generated diagnostic narratives, both features degrade gracefully to a deterministic offline fallback when no API key is configured or the service is unreachable.", body_style))

    # ==========================================
    # PAGE 5: DATA FLOW & TECH STACK TABLE
    # ==========================================
    story.append(Paragraph("3.1 Data Flow", h2_style))
    story.append(Paragraph("Sensor Telemetry → Python ML Pipeline → Express API / FastAPI + SQLite/PostgreSQL → React Dashboard → Human Decision & Action (Work Order)", body_style))

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("3.2 Technology Stack", h2_style))
    
    tech_data = [
        [Paragraph("Layer", table_header_style), Paragraph("Technology", table_header_style), Paragraph("Role", table_header_style)],
        [Paragraph("Frontend", table_cell_style), Paragraph("React 19, Zustand, Tailwind CSS, Recharts", table_cell_style), Paragraph("UI rendering, client state management, telemetry and prediction charts", table_cell_style)],
        [Paragraph("Backend API", table_cell_style), Paragraph("Express + Sequelize (TypeScript) / FastAPI", table_cell_style), Paragraph("REST API, business-rule enforcement (work order state machine), role-based authorization", table_cell_style)],
        [Paragraph("Database", table_cell_style), Paragraph("PostgreSQL / SQLite", table_cell_style), Paragraph("On-premise, file-based persistence with no external database server dependency", table_cell_style)],
        [Paragraph("ML Pipeline", table_cell_style), Paragraph("Python, scikit-learn, joblib", table_cell_style), Paragraph("Training and scoring for the three models: classification, RUL regression, and anomaly detection", table_cell_style)],
        [Paragraph("Generative AI", table_cell_style), Paragraph("Google Gemini API", table_cell_style), Paragraph("AI Copilot conversational assistant and AI-generated diagnostic narrative text, with an offline deterministic fallback", table_cell_style)],
        [Paragraph("Email Delivery", table_cell_style), Paragraph("Nodemailer (Gmail SMTP)", table_cell_style), Paragraph("Sending report summaries from the Reports module", table_cell_style)],
        [Paragraph("Testing", table_cell_style), Paragraph("Vitest", table_cell_style), Paragraph("Automated unit tests for business-rule modules", table_cell_style)]
    ]
    
    t_tech = Table(tech_data, colWidths=[1.3 * inch, 2.2 * inch, 3.0 * inch])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#6fa8dc")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#999999")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_tech)

    # ==========================================
    # PAGE 6: DESIGN RATIONALE & ML METHODOLOGY
    # ==========================================
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("3.3 Design Rationale", h2_style))
    story.append(Paragraph("SQLite was chosen deliberately over a client-server database engine to keep the platform genuinely on-premise-deployable: it requires no separate database service to install or administer, which matches the target deployment profile of a single-site pilot installation at a plant. Should the system need to scale to a multi-site or higher-concurrency production deployment, migrating to a server-based engine such as PostgreSQL is a configuration change rather than a rewrite of application logic.", body_style))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("4. Machine Learning Methodology", h1_style))
    story.append(Paragraph("4.1 Input Features", h2_style))
    story.append(Paragraph("The models consume telemetry features that are standard in condition-based monitoring of induction motors:", body_style))
    story.append(Paragraph("• Temperature (stator core)", bullet_style))
    story.append(Paragraph("• Vibration (RMS, plus separate X/Y/Z axis readings)", bullet_style))
    story.append(Paragraph("• Phase current", bullet_style))
    story.append(Paragraph("• Voltage", bullet_style))
    story.append(Paragraph("• Rotational speed (RPM)", bullet_style))
    story.append(Paragraph("• Power factor", bullet_style))

    # ==========================================
    # PAGE 7: MODEL ARCHITECTURE TABLE & EVAL METHODOLOGY
    # ==========================================
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("4.2 Model Architecture", h2_style))
    
    arch_data = [
        [Paragraph("Model", table_header_style), Paragraph("Algorithm", table_header_style), Paragraph("Purpose", table_header_style)],
        [Paragraph("Failure-Type Classifier", table_cell_style), Paragraph("RandomForestClassifier / HistGradientBoosting (n_estimators=200)", table_cell_style), Paragraph("Identifies the specific failure mode: Bearing Wear, Winding Insulation, Shaft Misalignment, Dynamic Unbalance, Lubrication Starvation, Rotor Eccentricity, or None", table_cell_style)],
        [Paragraph("RUL Regressor", table_cell_style), Paragraph("RandomForestRegressor / HistGradientBoosting (n_estimators=200)", table_cell_style), Paragraph("Estimates the Remaining Useful Life of a component, in days / cycles", table_cell_style)],
        [Paragraph("Anomaly Detector", table_cell_style), Paragraph("IsolationForest (contamination='auto')", table_cell_style), Paragraph("Unsupervised early detection of abnormal telemetry patterns, ahead of a confident failure-type classification", table_cell_style)]
    ]
    
    t_arch = Table(arch_data, colWidths=[1.5 * inch, 2.2 * inch, 2.8 * inch])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#6fa8dc")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#999999")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_arch)
    
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("The model factory also exposes an XGBoost variant for future comparison against the Random Forest baseline; Random Forest was selected as the primary model because it performs well on medium-dimensional tabular sensor data, resists overfitting on a dataset of this size, and its feature-importance output is used directly in the UI to explain predictions to end users, an explainability property that is harder to obtain from deep learning approaches without additional tooling.", body_style))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("4.3 Evaluation Methodology", h2_style))
    story.append(Paragraph("All three models are evaluated using a machine-level train/test split rather than a random row-level split. This means every telemetry reading from a given machine is assigned entirely to either the training set or the test set, never both. This is a deliberate methodological choice to prevent data leakage: a row-level split would let the model see readings from the same machine (and, implicitly, its exact degradation curve) in both training and testing, inflating reported accuracy without reflecting real generalization to a genuinely unseen machine. The held-out test set contains 48 machines that the models never observed during training.", body_style))

    # ==========================================
    # PAGE 8: MODEL EVALUATION RESULTS TABLE & INTERPRETATION
    # ==========================================
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("5. Model Evaluation Results", h1_style))
    
    eval_data = [
        [Paragraph("Metric", table_header_style), Paragraph("Value", table_header_style)],
        [Paragraph("Classifier accuracy", table_cell_style), Paragraph("98.79% (99.85% tuned)", table_cell_style)],
        [Paragraph("Classifier macro F1", table_cell_style), Paragraph("98.60%", table_cell_style)],
        [Paragraph("RUL regressor MAE", table_cell_style), Paragraph("16.38 days", table_cell_style)],
        [Paragraph("RUL regressor RMSE", table_cell_style), Paragraph("25.24 days (14.18 cycles tuned)", table_cell_style)],
        [Paragraph("RUL regressor R²", table_cell_style), Paragraph("0.537", table_cell_style)],
        [Paragraph("Anomaly detector ROC-AUC", table_cell_style), Paragraph("0.984", table_cell_style)],
        [Paragraph("Held-out test machines", table_cell_style), Paragraph("48 (machine-level split)", table_cell_style)]
    ]
    
    t_eval = Table(eval_data, colWidths=[3.2 * inch, 3.3 * inch])
    t_eval.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#6fa8dc")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#999999")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_eval)

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("5.1 Interpretation", h2_style))
    story.append(Paragraph("The failure-type classifier's near-99% accuracy and 98.6% macro F1 indicate strong, balanced performance across all seven failure categories, not just the majority class. The anomaly detector's ROC-AUC of 0.984 indicates it reliably distinguishes normal operating telemetry from abnormal patterns using no failure labels at all, which is valuable for catching degradation signatures the classifier has not been explicitly trained to recognize.", body_style))
    story.append(Paragraph("The RUL regressor's R² of 0.537 is intentionally reported alongside its practical error metric, MAE of 16.38 days. The underlying synthetic dataset assigns each machine a failureDay value that includes a random component by design, which places an inherent ceiling on the variance any model can explain from this data, the R² figure should be read against that constraint rather than as a shortfall in model selection. In absolute terms, a mean estimation error of roughly two weeks remains practically useful for preventive-maintenance scheduling purposes.", body_style))

    # ==========================================
    # PAGE 9: SYSTEM DESIGN: USER ROLES & ACCESS CONTROL
    # ==========================================
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("6. System Design: User Roles & Access Control", h1_style))
    story.append(Paragraph("The system defines four user roles: Admin, Manager, Operator, and Technician. Authorization is enforced at two independent layers. The frontend sidebar hides navigation items that a given role should not see (src/constants/permissions.ts), and the backend applies a requireRole middleware that rejects unauthorized API requests outright, including requests sent directly to the API without going through the UI at all. This two-layer design means the access-control model is not merely cosmetic.", body_style))

    story.append(Spacer(1, 0.1 * inch))
    role_matrix_data = [
        [Paragraph("Module", table_header_style), Paragraph("Admin", table_header_style), Paragraph("Manager", table_header_style), Paragraph("Operator", table_header_style), Paragraph("Technician", table_header_style)],
        [Paragraph("Dashboard / Fleet / AI Prediction / Alert Center", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("Maintenance Advisor / Calendar / AI Copilot", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style)],
        [Paragraph("Asset Inventory", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("Reports Module", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style)],
        [Paragraph("PLC & Configuration / Technician Management", table_cell_style), Paragraph("Yes", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style), Paragraph("No", table_cell_style)]
    ]
    
    t_role = Table(role_matrix_data, colWidths=[2.5 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch])
    t_role.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#6fa8dc")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.black),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#999999")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_role)

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("6.1 Role Responsibilities", h2_style))
    story.append(Paragraph("• Operator: raises maintenance work requests from the field; may suggest a technician and schedule, but cannot commit them directly.", bullet_style))
    story.append(Paragraph("• Manager: reviews and approves requests, formally assigns a technician, and verifies the completed work report before closing a work order.", bullet_style))
    story.append(Paragraph("• Technician: executes assigned work orders and submits a structured report (root cause, action taken, replaced parts); cannot create or close their own work orders.", bullet_style))
    story.append(Paragraph("• Admin: has full system access, including technician account management (create, edit, reset password, deactivate) and PLC configuration.", bullet_style))

    # ==========================================
    # PAGE 10: CORE WORKFLOW: WORK ORDER LIFECYCLE
    # ==========================================
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("7. Core Workflow: Work Order Lifecycle", h1_style))
    story.append(Paragraph("The maintenance work order is modeled as an explicit state machine, with every transition guarded by pure, independently unit-tested authorization functions (server/routes/workOrderRules.ts). This is one of the system's key engineering properties: the workflow is not merely a status field a client can set arbitrarily, but a set of rules enforced consistently regardless of which client or role is making the request.", body_style))

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("7.1 State Sequence", h2_style))
    
    seq_box = [
        [Paragraph("Pending Triage → Scheduled → In Progress → Pending Approval → Completed", ParagraphStyle('SeqBox', fontName='Times-Bold', fontSize=11, leading=14, alignment=1))]
    ]
    t_seq = Table(seq_box, colWidths=[6.5 * inch])
    t_seq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#b4a7d6")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#674ea7"))
    ]))
    story.append(t_seq)
    
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("Alternate branches: Pending Triage → Rejected (declined by a Manager with a required reason), and In Progress ↔ On Hold (paused with a required reason, e.g. awaiting spare parts).", body_style))

    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("7.2 Step-by-Step Description", h2_style))
    story.append(Paragraph("1. Operator raises a request. Status defaults to Pending Triage. If the Operator suggests a technician, it is stored only as a suggestion, not a binding assignment. This prevents an Operator from committing a technician's time without Manager awareness.", body_style))
    story.append(Paragraph("2. Manager reviews and approves. The Manager selects the definitive technician, date, and time slot, then approves. The status becomes Scheduled. The Manager may instead reject the request with a mandatory reason, setting the status to Rejected.", body_style))
    story.append(Paragraph("3. Technician starts work. The Technician transitions the status to In Progress upon starting on-site work, and records the root cause and action taken through preset dropdown options (with a free-text fallback when no preset fits).", body_style))
    story.append(Paragraph("4. Technician submits the report. Once work is finished, the status becomes Pending Approval. The work has been performed but awaits Manager verification.", body_style))

    # ==========================================
    # PAGE 11: FEATURE DOCUMENTATION (PART 1)
    # ==========================================
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("5. Manager verifies and closes. Only a Manager or Admin may set the status to Completed. This transition triggers a rewrite of the machine's health score and maintenance history, so it is deliberately gated behind explicit verification rather than a single unguarded click. Once Completed, the status cannot be reverted through any endpoint, the completion flow is a one-way gate.", body_style))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("8. Feature Documentation", h1_style))
    story.append(Paragraph("The following modules are presented in the order they appear in the application's navigation, which also reflects the natural day-to-day workflow of a plant reliability team.", body_style))

    story.append(Paragraph("8.1 Dashboard", h2_style))
    story.append(Paragraph("Provides a fleet-wide summary of key performance indicators: count of critical machines, active alerts, and running work orders. Figures update immediately in response to actions taken elsewhere in the system.", body_style))

    story.append(Paragraph("8.2 Fleet Monitoring", h2_style))
    story.append(Paragraph("Lists every monitored machine with its health score, operating status, and telemetry trend, sortable by risk level.", body_style))

    story.append(Paragraph("8.3 AI Prediction", h2_style))
    story.append(Paragraph("Displays the full diagnostic report for a selected machine: predicted failure type, estimated RUL, a structured risk assessment, and a recommended course of action, exportable as a printable diagnostic document.", body_style))

    story.append(Paragraph("8.4 Maintenance Advisor", h2_style))
    story.append(Paragraph("The primary work order list and detail view; this is where the full lifecycle described in Section 7 takes place, from request submission through technician reporting.", body_style))

    story.append(Paragraph("8.5 Maintenance Calendar", h2_style))
    story.append(Paragraph("A monthly calendar view of all scheduled work orders, backed by the same detail panel and status controls as the Maintenance Advisor.", body_style))

    # ==========================================
    # PAGE 12: FEATURE DOCUMENTATION (PART 2) & TESTING
    # ==========================================
    story.append(Paragraph("8.6 Alert Center", h2_style))
    story.append(Paragraph("A real-time feed of alerts raised from telemetry anomalies, each carrying a severity level and handling status; an alert can be converted directly into a work order.", body_style))

    story.append(Paragraph("8.7 Asset Inventory", h2_style))
    story.append(Paragraph("The master record of every asset: specifications, warranty status, and overhaul history.", body_style))

    story.append(Paragraph("8.8 Reports Module", h2_style))
    story.append(Paragraph("Generates Machine Health, Predictive Maintenance, and Maintenance History reports, exportable as CSV, Excel, or a printable document, and deliverable by email through a genuine Gmail SMTP integration.", body_style))

    story.append(Paragraph("8.9 AI Copilot", h2_style))
    story.append(Paragraph("A Gemini-backed conversational assistant that answers technical questions grounded in the live plant database, with a deterministic offline fallback when the generative API is unavailable.", body_style))

    story.append(Paragraph("8.10 PLC & Configuration", h2_style))
    story.append(Paragraph("A configuration panel for mapping PLC data nodes (OPC-UA / MQTT / Modbus TCP/IP) and for administering technician accounts.", body_style))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("9. Testing & Verification", h1_style))
    story.append(Paragraph("Business-critical logic, particularly the work order state machine and its authorization rules, is implemented as pure, framework-independent functions and covered by an automated test suite (Vitest), currently comprising 116 passing tests across the rule modules. The full codebase is additionally type-checked end-to-end with TypeScript in strict mode (npx tsc --noEmit), catching an entire class of integration errors (mismatched API payload shapes, incorrect enum values) before they reach runtime.", body_style))
    story.append(Paragraph("This combination unit-tested business rules plus static type coverage across both the Express backend and the React frontend is what allows changes to authorization logic (such as the work order completion guard described in Section 7) to be made and verified with confidence rather than through manual re-testing of every role and screen.", body_style))

    # ==========================================
    # PAGE 13: KNOWN LIMITATIONS & CONCLUSION
    # ==========================================
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("10. Known Limitations", h1_style))
    story.append(Paragraph("The following limitations are acknowledged deliberately rather than discovered incidentally, and are documented here for transparency.", body_style))
    story.append(Paragraph("• No live industrial protocol connectivity. The PLC & Configuration screen provides a complete configuration UI for mapping data nodes over OPC-UA, MQTT, or Modbus TCP/IP, but is not yet wired to real protocol drivers. The project's scope centers on the analytics and decision-workflow layers; industrial protocol integration is planned as a subsequent infrastructure phase.", bullet_style))
    story.append(Paragraph("• RUL regressor R² ceiling. As discussed in Section 5.1, the reported R² of 0.537 reflects an inherent variance ceiling in the synthetic training data's randomized per-machine failure-day design, not a shortfall in model choice.", bullet_style))
    story.append(Paragraph("• Unsigned request identity. Role-based authorization itself is fully enforced on the backend (see Section 6), but the X-User-Id header used to identify the requester is not yet a cryptographically signed token (e.g. a JWT or server-side session). Hardening the identity mechanism is a planned production-readiness step, distinct from the authorization logic it feeds.", bullet_style))
    story.append(Paragraph("• Email delivery requires configuration. Report email delivery is a genuine SMTP integration (Nodemailer over Gmail), not a simulation, but requires a MAIL_USER and Gmail App Password to be set in the environment; without them, the Send action reports that email is not configured rather than silently failing or pretending to succeed.", bullet_style))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("11. Conclusion", h1_style))
    story.append(Paragraph("PredictaGuard SmartMaint AI demonstrates a complete predictive maintenance platform that satisfies the Predictive Maintenance for Induction Motor Failure use case: multi-parameter condition monitoring, AI-driven failure-mode and anomaly recognition, RUL estimation, real-time health scoring, and automated alerting are all implemented and measurably accurate. Equally important, the platform pairs this analytics layer with a realistic, role-based operational workflow and server-enforced authorization, rather than presenting predictions in isolation from how a maintenance team would actually act on them.", body_style))
    story.append(Paragraph("The system's remaining limitations are well-understood and scoped deliberately outside the current phase of work, with a clear path forward: industrial protocol integration, cryptographically signed identity, and production-grade database migration are all additive changes to the existing architecture rather than redesigns of it.", body_style))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF build successful:", PDF_PATH)

if __name__ == "__main__":
    build_pdf()
