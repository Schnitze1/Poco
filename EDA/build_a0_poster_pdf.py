import os
import sys
from PIL import Image
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

EDA_DIR = r"d:\Repos\Poco\EDA"
ASSETS_DIR = os.path.join(EDA_DIR, "poster_assets")
PDF_OUT = os.path.join(EDA_DIR, "POCO_A0_Poster_CL01_G01.pdf")

# Register system TrueType fonts
FONTS_DIR = r"C:\Windows\Fonts"
try:
    pdfmetrics.registerFont(TTFont("CalibriLight", os.path.join(FONTS_DIR, "calibril.ttf")))
    pdfmetrics.registerFont(TTFont("CalibriLight-Italic", os.path.join(FONTS_DIR, "calibrii.ttf")))
    pdfmetrics.registerFont(TTFont("Calibri-Bold", os.path.join(FONTS_DIR, "calibrib.ttf")))
    pdfmetrics.registerFont(TTFont("Calibri-Regular", os.path.join(FONTS_DIR, "calibri.ttf")))
    F_LIGHT = "CalibriLight"
    F_BOLD = "Calibri-Bold"
    F_ITALIC = "CalibriLight-Italic"
    F_REG = "Calibri-Regular"
except Exception as e:
    print(f"Font registration warning: {e}, falling back to Helvetica")
    F_LIGHT = "Helvetica"
    F_BOLD = "Helvetica-Bold"
    F_ITALIC = "Helvetica-Oblique"
    F_REG = "Helvetica"

# Colors
C_PRIMARY = HexColor("#1F3864")    # Dark navy
C_SECONDARY = HexColor("#2E75B6")  # Medium blue
C_ACCENT = HexColor("#ED7D31")     # Orange accent
C_TEXT = HexColor("#262626")       # Near-black body
C_MUTED = HexColor("#595959")      # Medium grey captions
C_PANEL = HexColor("#F2F2F2")      # Light grey panel
C_BORDER = HexColor("#BFBFBF")     # Divider grey

PAGE_W = 1189 * mm
PAGE_H = 841 * mm
MARGIN = 15 * mm

def draw_paragraph(c, text, x, y, width, font_name, font_size, leading, color, align='left', bold=False):
    style = ParagraphStyle(
        name='CustomStyle',
        fontName=font_name,
        fontSize=font_size,
        leading=leading,
        textColor=color,
        alignment=0 if align == 'left' else (2 if align == 'right' else 1)
    )
    p = Paragraph(text, style)
    w, h = p.wrap(width, 1000 * mm)
    p.drawOn(c, x, y - h)
    return h

def draw_stat_box(c, x, y, w, h, number, label):
    c.setFillColor(C_PANEL)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, 3*mm, fill=1, stroke=1)
    
    c.setFont(F_BOLD, 26)
    c.setFillColor(C_PRIMARY)
    c.drawCentredString(x + w/2, y + h*0.53, number)
    
    c.setFont(F_LIGHT, 19)
    c.setFillColor(HexColor("#404040"))
    c.drawCentredString(x + w/2, y + h*0.18, label)

def draw_image_with_caption(c, img_path, x, y, w, h, caption=None):
    if not os.path.exists(img_path):
        c.setFillColor(HexColor("#FFF0F0"))
        c.setStrokeColor(HexColor("#E06666"))
        c.rect(x, y, w, h, fill=1, stroke=1)
        c.setFont(F_BOLD, 18)
        c.setFillColor(HexColor("#CC0000"))
        c.drawCentredString(x + w/2, y + h/2, f"Figure missing: {os.path.basename(img_path)}")
        return
    
    try:
        c.drawImage(img_path, x, y, width=w, height=h, preserveAspectRatio=True, anchor='c')
    except Exception as e:
        print(f"Error drawing image {img_path}: {e}")

    if caption:
        c.setFont(F_ITALIC, 16)
        c.setFillColor(C_MUTED)
        c.drawCentredString(x + w/2, y - 5*mm, caption)

def generate_pdf():
    print(f"Creating A0 Landscape competition poster: {PDF_OUT}")
    c = canvas.Canvas(PDF_OUT, pagesize=(PAGE_W, PAGE_H))

    # Background
    c.setFillColor(HexColor("#FFFFFF"))
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # -------------------------------------------------------------------------
    # 1. TOP BAND (Y from 826mm down to 766mm)
    # -------------------------------------------------------------------------
    top_y = PAGE_H - MARGIN # 826 mm
    
    # Left: Title & Subtitle
    c.setFont(F_BOLD, 68)
    c.setFillColor(C_PRIMARY)
    c.drawString(MARGIN, top_y - 20*mm, "Poco — Preserve Originals, Conceal Only")

    c.setFont(F_LIGHT, 34)
    c.setFillColor(HexColor("#404040"))
    c.drawString(MARGIN, top_y - 35*mm, "Privacy-first PII anonymisation for LLM workflows, with a fully automated multi-environment DevOps pipeline")

    # Right: Unit, Group, Team
    right_x = PAGE_W - MARGIN # 1174 mm
    c.setFont(F_BOLD, 26)
    c.setFillColor(C_PRIMARY)
    c.drawRightString(right_x, top_y - 12*mm, "SWE40006 Software Deployment and Evolution")

    c.setFont(F_LIGHT, 23)
    c.setFillColor(C_TEXT)
    c.drawRightString(right_x, top_y - 23*mm, "Group CL01_G01 | Tutorial: Wednesday 10:30")

    c.setFont(F_LIGHT, 23)
    c.setFillColor(HexColor("#404040"))
    c.drawRightString(right_x, top_y - 34*mm, "Jamie Soo (104559690) · Timothy Schabel (105334128) · Sahil (105295665)")

    # Divider line below top band (2pt #1F3864)
    div_y = top_y - 45*mm # ~781 mm
    c.setStrokeColor(C_PRIMARY)
    c.setLineWidth(2.2)
    c.line(MARGIN, div_y, right_x, div_y)

    # -------------------------------------------------------------------------
    # 2. COLUMN GEOMETRY
    # -------------------------------------------------------------------------
    col_w = 380 * mm
    gutter = 9.5 * mm
    col1_x = MARGIN                      # 15 mm
    col2_x = MARGIN + col_w + gutter     # 404.5 mm
    col3_x = col2_x + col_w + gutter     # 794 mm
    col3_w = right_x - col3_x            # 380 mm

    body_top_y = div_y - 8*mm            # ~773 mm
    body_bot_y = MARGIN + 58*mm          # ~73 mm
    body_h = body_top_y - body_bot_y     # ~700 mm

    # =========================================================================
    # LEFT COLUMN (Sections 1 to 5)
    # =========================================================================
    cur_y = body_top_y

    # Section 1: The Problem
    c.setFont(F_BOLD, 38)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cur_y - 11*mm, "The Problem")
    cur_y -= 15*mm

    h = draw_paragraph(c, "Every day, people paste contracts, medical notes, and CVs into ChatGPT. Once they do, names, addresses, and financial details are outside their control. Poco makes that safe.",
                       col1_x, cur_y, col_w, F_LIGHT, 24, 28, C_TEXT)
    cur_y -= (h + 8*mm)

    # Section 2: How Poco Works
    c.setFont(F_BOLD, 38)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cur_y - 11*mm, "How Poco Works")
    cur_y -= 15*mm

    h = draw_paragraph(c, "Poco detects personal information, replaces each value with a reversible token like [PERSON_1] or [EMAIL_1], and stores the mapping in an encrypted session vault. The redacted text is sent to any LLM, and the response is restored to its original form when it returns.",
                       col1_x, cur_y, col_w, F_LIGHT, 23, 27, C_TEXT)
    cur_y -= (h + 4*mm)

    # Flow diagram
    flow_h = 58 * mm
    draw_image_with_caption(c, os.path.join(ASSETS_DIR, "flow_diagram.png"), col1_x, cur_y - flow_h, col_w, flow_h)
    cur_y -= (flow_h + 10*mm)

    # Section 3: Architecture
    c.setFont(F_BOLD, 38)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cur_y - 11*mm, "Architecture")
    cur_y -= 15*mm

    arch_h = 135 * mm
    draw_image_with_caption(c, os.path.join(ASSETS_DIR, "poco_architecture.png"), col1_x, cur_y - arch_h, col_w, arch_h,
                            caption="Figure 1. Two-pass hybrid PII detection engine.")
    cur_y -= (arch_h + 14*mm)

    # Section 4: DevOps Pipeline
    c.setFont(F_BOLD, 38)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cur_y - 11*mm, "DevOps Pipeline")
    cur_y -= 15*mm

    h = draw_paragraph(c, "Every code change flows through GitHub Actions, which builds the Rust backend inside the Cargo Lambda container, runs unit, integration, and browser acceptance tests, and deploys to four isolated AWS environments (Development, Testing, Staging, Production). Failed tests block promotion.",
                       col1_x, cur_y, col_w, F_LIGHT, 23, 27, C_TEXT)
    cur_y -= (h + 4*mm)

    pipe_h = 52 * mm
    draw_image_with_caption(c, os.path.join(ASSETS_DIR, "devops_pipeline.png"), col1_x, cur_y - pipe_h, col_w, pipe_h)
    cur_y -= (pipe_h + 10*mm)

    # Section 5: Demo
    c.setFont(F_BOLD, 38)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cur_y - 11*mm, "Demo")
    cur_y -= 14*mm

    # QR Demo + beside text
    qr_sz = 45 * mm
    c.drawImage(os.path.join(ASSETS_DIR, "qr_demo.png"), col1_x, cur_y - qr_sz, width=qr_sz, height=qr_sz)
    c.setFont(F_BOLD, 23)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x + qr_sz + 6*mm, cur_y - 16*mm, "Live demo:")
    c.setFont(F_BOLD, 23)
    c.setFillColor(C_SECONDARY)
    c.drawString(col1_x + qr_sz + 6*mm, cur_y - 27*mm, "littlepoco.me")
    cur_y -= (qr_sz + 6*mm)

    ui_h = 115 * mm
    draw_image_with_caption(c, os.path.join(ASSETS_DIR, "poco_encode_view.png"), col1_x, cur_y - ui_h, col_w, ui_h,
                            caption="Figure 2. Poco encode view with coloured token highlighting.")

    # =========================================================================
    # CENTRE COLUMN (Sections 6 to 11)
    # =========================================================================
    cur_y = body_top_y

    # Section 6: Dataset: AI4Privacy OpenPII 1.5M
    c.setFont(F_BOLD, 38)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cur_y - 11*mm, "Dataset: AI4Privacy OpenPII 1.5M")
    cur_y -= 15*mm

    h = draw_paragraph(c, "Analysis of 1,636,375 multilingual documents across 30 languages, 11.9 million PII annotations, and 43 discovered PII entity classes. Full-corpus census completed and cached to Parquet.",
                       col2_x, cur_y, col_w, F_LIGHT, 23, 27, C_TEXT)
    cur_y -= (h + 5*mm)

    # Key stats box
    stat_box_w = (col_w - 9*mm) / 4
    stat_box_h = 38 * mm
    draw_stat_box(c, col2_x, cur_y - stat_box_h, stat_box_w, stat_box_h, "1,636,375", "Total examples")
    draw_stat_box(c, col2_x + (stat_box_w + 3*mm), cur_y - stat_box_h, stat_box_w, stat_box_h, "11,887,370", "Annotations")
    draw_stat_box(c, col2_x + 2*(stat_box_w + 3*mm), cur_y - stat_box_h, stat_box_w, stat_box_h, "43", "PII classes")
    draw_stat_box(c, col2_x + 3*(stat_box_w + 3*mm), cur_y - stat_box_h, stat_box_w, stat_box_h, "30", "Languages")
    cur_y -= (stat_box_h + 10*mm)

    # Section 7: Label Distribution (Figs 1 & 2 side by side)
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cur_y - 9*mm, "Label Distribution")
    cur_y -= 13*mm

    half_w = (col_w - 6*mm) / 2
    f1_h = 100 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig1_label_distribution.png"), col2_x, cur_y - f1_h, half_w, f1_h,
                            caption="Figure 3. Top 25 PII labels by viability.")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig2_label_log.png"), col2_x + half_w + 6*mm, cur_y - f1_h, half_w, f1_h,
                            caption="Figure 4. 43-label taxonomy (log scale).")
    cur_y -= (f1_h + 14*mm)

    # Section 8: Class Viability
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cur_y - 9*mm, "Class Viability")
    cur_y -= 13*mm

    h = draw_paragraph(c, "Only 20 of the 43 discovered labels are viable for supervised training. 4 are marginal, and 19 are unviable (<100 corpus annotations, down to single occurrences). The unviable labels are handled by deterministic regex in Poco.",
                       col2_x, cur_y, col_w, F_LIGHT, 22, 26, C_TEXT)
    cur_y -= (h + 7*mm)

    # Section 9: Language Coverage (Figs 3 & 4 side by side)
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cur_y - 9*mm, "Language Coverage")
    cur_y -= 13*mm

    f3_h = 92 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig3_languages.png"), col2_x, cur_y - f3_h, half_w, f3_h,
                            caption="Figure 5. 30 languages representation.")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig4_region_lang.png"), col2_x + half_w + 6*mm, cur_y - f3_h, half_w, f3_h,
                            caption="Figure 6. Region × language mapping.")
    cur_y -= (f3_h + 14*mm)

    # Section 10: Document Lengths (Figs 5 & 7 side by side)
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cur_y - 9*mm, "Document Lengths")
    cur_y -= 13*mm

    f5_h = 82 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig5_entities_per_example.png"), col2_x, cur_y - f5_h, half_w, f5_h,
                            caption="Figure 7. Entities per document.")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig7_token_lengths.png"), col2_x + half_w + 6*mm, cur_y - f5_h, half_w, f5_h,
                            caption="Figure 8. Token length distribution.")
    cur_y -= (f5_h + 14*mm)

    # Section 11: Entity Span Lengths & Co-occurrence (Figs 8 & 6 side by side)
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cur_y - 9*mm, "Entity Span Lengths & Co-occurrence")
    cur_y -= 13*mm

    f8_h = 92 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig8_span_lengths.png"), col2_x, cur_y - f8_h, half_w, f8_h,
                            caption="Figure 9. Word span length by class.")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig6_cooccurrence.png"), col2_x + half_w + 6*mm, cur_y - f8_h, half_w, f8_h,
                            caption="Figure 9b. Entity co-occurrence matrix.")
    cur_y -= (f8_h + 10*mm)

    # =========================================================================
    # RIGHT COLUMN (Sections 12 to 19)
    # =========================================================================
    cur_y = body_top_y

    # Section 12: Per-Language Composition
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cur_y - 9*mm, "Per-Language Composition")
    cur_y -= 12*mm

    f9_h = 80 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig9_language_entity_composition.png"), col3_x, cur_y - f9_h, col3_w, f9_h,
                            caption="Figure 10. Per-language entity composition across 8 Asia-Pacific languages.")
    cur_y -= (f9_h + 10*mm)

    h = draw_paragraph(c, "Chi-square p < 10⁻³⁰⁰, but Cramér's V = 0.017 shows the effect is negligible — the synthetic generator produces uniform proportions.",
                       col3_x, cur_y, col3_w, F_LIGHT, 20, 24, C_TEXT)
    cur_y -= (h + 5*mm)

    # Section 13: Data Quality (4 plots in 2x2 grid)
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cur_y - 9*mm, "Data Quality & Diagnostic Boxplots")
    cur_y -= 12*mm

    q_w = (col3_w - 6*mm) / 2
    q_h = 52 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig10_precleaning_boxplots.png"), col3_x, cur_y - q_h, q_w, q_h,
                            caption="Figure 11. Pre-cleaning boxplots.")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig11_precleaning_histograms.png"), col3_x + q_w + 6*mm, cur_y - q_h, q_w, q_h,
                            caption="Figure 12. Pre-cleaning histograms.")
    cur_y -= (q_h + 12*mm)

    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig12_cleaned_boxplots.png"), col3_x, cur_y - q_h, q_w, q_h,
                            caption="Figure 13. Winsorised boxplots (P99).")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig13_cleaned_histograms.png"), col3_x + q_w + 6*mm, cur_y - q_h, q_w, q_h,
                            caption="Figure 14. Cleaned histograms.")
    cur_y -= (q_h + 12*mm)

    # Section 14 & 15: Normalisation & Correlation Matrix
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cur_y - 9*mm, "Normalisation & Correlation Structure")
    cur_y -= 12*mm

    f14_h = 70 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig14_normalisation_comparison.png"), col3_x, cur_y - f14_h, q_w, f14_h,
                            caption="Figure 15. Transform comparison.")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig15_correlation_heatmap.png"), col3_x + q_w + 6*mm, cur_y - f14_h, q_w, f14_h,
                            caption="Figure 16. Pearson correlation matrix.")
    cur_y -= (f14_h + 12*mm)

    # Section 15 & 16: Bivariate Pairplots & Target Stratification
    f16_h = 70 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig16_pairplots.png"), col3_x, cur_y - f16_h, q_w, f16_h,
                            caption="Figure 17. Bivariate pairplots.")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig17_target_vs_predictors_boxplots.png"), col3_x + q_w + 6*mm, cur_y - f16_h, q_w, f16_h,
                            caption="Figure 18. Stratified entity count.")
    cur_y -= (f16_h + 12*mm)

    # Section 17 & 18: Tokenizer Expansion & Split Parity Audit
    c.setFont(F_BOLD, 32)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cur_y - 9*mm, "Tokenizer Expansion & Split Parity")
    cur_y -= 12*mm

    h = draw_paragraph(c, "Full-corpus census confirmed that all 20 viable classes follow the 80.05% / 19.95% train/val split with |Δ| < 0.08%.",
                       col3_x, cur_y, col3_w, F_LIGHT, 20, 24, C_TEXT)
    cur_y -= (h + 4*mm)

    t_w = (col3_w - 8*mm) / 3
    t_h = 62 * mm
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig18_cjk_token_efficiency.png"), col3_x, cur_y - t_h, t_w, t_h,
                            caption="Fig 19. CJK expansion (2.4×).")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig19_train_val_split_parity.png"), col3_x + t_w + 4*mm, cur_y - t_h, t_w, t_h,
                            caption="Fig 20. Split parity.")
    draw_image_with_caption(c, os.path.join(EDA_DIR, "fig20_rare_label_imbalance.png"), col3_x + 2*(t_w + 4*mm), cur_y - t_h, t_w, t_h,
                            caption="Fig 21. Rare label imbalance.")
    cur_y -= (t_h + 13*mm)

    # Section 19: Key Findings
    c.setFont(F_BOLD, 38)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cur_y - 11*mm, "Key Findings")
    cur_y -= 15*mm

    findings_h = 78 * mm
    c.setFillColor(C_PANEL)
    c.setStrokeColor(C_PRIMARY)
    c.setLineWidth(1.5)
    c.roundRect(col3_x, cur_y - findings_h, col3_w, findings_h, 3*mm, fill=1, stroke=1)
    
    # Left accent bar
    c.setFillColor(C_PRIMARY)
    c.rect(col3_x, cur_y - findings_h, 4*mm, findings_h, fill=1, stroke=0)

    findings = [
        "1. 20 of 43 discovered labels are viable for supervised training",
        "2. 8 labels have zero validation instances — Vault manual mapping is required",
        "3. Chinese text consumes 2.4× more tokens per character than Latin",
        "4. Class imbalance is 73:1 between GIVENNAME and TIME",
        "5. Perfect 80/20 train/val parity on all viable labels"
    ]
    fy = cur_y - 10*mm
    for f in findings:
        c.setFont(F_BOLD, 20)
        c.setFillColor(C_PRIMARY)
        c.drawString(col3_x + 8*mm, fy, f)
        fy -= 14*mm

    # -------------------------------------------------------------------------
    # 3. BOTTOM BAND (Y from 65mm down to 15mm)
    # -------------------------------------------------------------------------
    bot_y = MARGIN + 46*mm # ~61 mm
    
    # Divider above bottom band (1.5pt #1F3864)
    c.setStrokeColor(C_PRIMARY)
    c.setLineWidth(1.8)
    c.line(MARGIN, bot_y, right_x, bot_y)

    # Left third: Repo QR (40mm) + text
    qr_b_sz = 38 * mm
    c.drawImage(os.path.join(ASSETS_DIR, "qr_repo.png"), MARGIN, MARGIN + 2*mm, width=qr_b_sz, height=qr_b_sz)
    c.setFont(F_BOLD, 21)
    c.setFillColor(C_PRIMARY)
    c.drawString(MARGIN + qr_b_sz + 6*mm, MARGIN + 26*mm, "Repository:")
    c.setFont(F_LIGHT, 19)
    c.setFillColor(C_SECONDARY)
    c.drawString(MARGIN + qr_b_sz + 6*mm, MARGIN + 14*mm, "github.com/Schnitze1/SWE40006-Group-Project")

    # Centre third: EDA QR (40mm) + text
    c.drawImage(os.path.join(ASSETS_DIR, "qr_eda.png"), col2_x, MARGIN + 2*mm, width=qr_b_sz, height=qr_b_sz)
    c.setFont(F_BOLD, 21)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x + qr_b_sz + 6*mm, MARGIN + 26*mm, "Full EDA Report:")
    c.setFont(F_LIGHT, 19)
    c.setFillColor(C_SECONDARY)
    c.drawString(col2_x + qr_b_sz + 6*mm, MARGIN + 14*mm, "woojin1069/pii-masking-openpii-1.5m")

    # Right third: Poco credits
    c.setFont(F_BOLD, 22)
    c.setFillColor(C_PRIMARY)
    c.drawRightString(right_x, MARGIN + 26*mm, "Poco — Preserve Originals, Conceal Only")
    c.setFont(F_LIGHT, 20)
    c.setFillColor(C_MUTED)
    c.drawRightString(right_x, MARGIN + 14*mm, "SWE40006 | CL01_G01 | October 2026")

    c.showPage()
    c.save()
    print("PDF generation complete!")

if __name__ == "__main__":
    generate_pdf()
