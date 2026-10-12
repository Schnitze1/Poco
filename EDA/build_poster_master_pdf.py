import os
import sys
from PIL import Image
import docx
from docx.shared import Mm, Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from pptx import Presentation
from pptx.util import Inches as PptInches, Pt as PptPt, Cm as PptCm
from pptx.dml.color import RGBColor as PptRGBColor
from pptx.enum.text import PP_ALIGN

from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

EDA_DIR = r"d:\Repos\Poco\EDA"
ASSETS_DIR = os.path.join(EDA_DIR, "poster_assets")
POSTER_DIR = r"d:\Repos\Poco\Poster"
os.makedirs(POSTER_DIR, exist_ok=True)

# Register Fonts for ReportLab
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
    print(f"Font registration warning: {e}")
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

# =============================================================================
# PART 1: REPORTLAB FULL-SCALE A0 PDF GENERATION (1189mm x 841mm, 1 PAGE)
# =============================================================================
def generate_master_pdf():
    pdf_path = os.path.join(POSTER_DIR, "POCO_A0_Poster_CL01_G01.pdf")
    print(f"Generating full-scale A0 Landscape PDF: {pdf_path}")
    
    PAGE_W = 1189 * mm
    PAGE_H = 841 * mm
    MARGIN = 15 * mm
    
    c = canvas.Canvas(pdf_path, pagesize=(PAGE_W, PAGE_H))
    c.setFillColor(HexColor("#FFFFFF"))
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # Coordinates
    # Top Margin Y = 826 mm, Bottom Margin Y = 15 mm
    # Row 1 (Title): Y: 826 to 776 mm (Height: 50 mm)
    # Row 2 (Key Findings Strip): Y: 772 to 732 mm (Height: 40 mm)
    # Row 3 (Main Body 3 Cols): Y: 726 to 96 mm (Height: 630 mm)
    # Row 4 (Demo / QR Strip): Y: 90 to 50 mm (Height: 40 mm)
    # Row 5 (Footer Strip): Y: 46 to 16 mm (Height: 30 mm)

    right_x = PAGE_W - MARGIN # 1174 mm
    usable_w = right_x - MARGIN # 1159 mm

    # -------------------------------------------------------------------------
    # ROW 1: TITLE BAND (Centred)
    # -------------------------------------------------------------------------
    r1_top = PAGE_H - MARGIN # 826 mm
    c.setFont(F_BOLD, 72)
    c.setFillColor(C_PRIMARY)
    c.drawCentredString(PAGE_W / 2, r1_top - 20*mm, "Poco — Preserve Originals, Conceal Only")

    c.setFont(F_REG, 32)
    c.setFillColor(HexColor("#404040"))
    c.drawCentredString(PAGE_W / 2, r1_top - 36*mm, "Privacy-first PII anonymisation for LLM workflows, with a fully automated multi-environment DevOps pipeline")

    # Divider below title
    c.setStrokeColor(C_PRIMARY)
    c.setLineWidth(2.0)
    c.line(MARGIN, r1_top - 47*mm, right_x, r1_top - 47*mm)

    # -------------------------------------------------------------------------
    # ROW 2: KEY FINDINGS STRIP (5 Nested Finding Blocks)
    # -------------------------------------------------------------------------
    r2_top = r1_top - 50*mm # 776 mm
    r2_h = 38 * mm
    r2_y = r2_top - r2_h

    # Container panel
    c.setFillColor(C_PANEL)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(1)
    c.roundRect(MARGIN, r2_y, usable_w, r2_h, 3*mm, fill=1, stroke=1)

    findings = [
        ("20 / 43", "PII labels viable for training"),
        ("8", "labels with zero validation instances"),
        ("2.4×", "more tokens per character for Chinese"),
        ("73:1", "class imbalance (GIVENNAME : TIME)"),
        ("99.99%", "of annotations in viable labels")
    ]
    block_w = usable_w / 5
    for i, (stat, label) in enumerate(findings):
        bx = MARGIN + i * block_w
        c.setFont(F_BOLD, 40)
        c.setFillColor(C_PRIMARY)
        c.drawCentredString(bx + block_w/2, r2_y + r2_h*0.52, stat)

        c.setFont(F_LIGHT, 17)
        c.setFillColor(HexColor("#404040"))
        c.drawCentredString(bx + block_w/2, r2_y + r2_h*0.18, label)

        if i < 4:
            c.setStrokeColor(C_BORDER)
            c.setLineWidth(1)
            c.line(bx + block_w, r2_y + 4*mm, bx + block_w, r2_y + r2_h - 4*mm)

    # -------------------------------------------------------------------------
    # ROW 3: MAIN BODY (3 Side-by-Side Columns)
    # Column 1: 38 cm (380mm), Column 2: 38 cm (380mm), Column 3: 39.9 cm (399mm)
    # -------------------------------------------------------------------------
    r3_top = r2_y - 6*mm # ~732 mm
    r3_bot = MARGIN + 72*mm # ~87 mm
    r3_h = r3_top - r3_bot # ~645 mm

    col1_x = MARGIN
    col1_w = 380 * mm
    col2_x = MARGIN + 380*mm + 10*mm # 405 mm
    col2_w = 380 * mm
    col3_x = col2_x + 380*mm + 10*mm # 795 mm
    col3_w = right_x - col3_x        # 379 mm

    # Helpers
    def draw_par(text, x, y, w, font_name, size, leading, col):
        st = ParagraphStyle('PS', fontName=font_name, fontSize=size, leading=leading, textColor=col)
        p = Paragraph(text, st)
        pw, ph = p.wrap(w, 1000*mm)
        p.drawOn(c, x, y - ph)
        return ph

    def draw_fig(path, x, y, w, h, caption=None):
        if not os.path.exists(path):
            c.setFillColor(HexColor("#FFF0F0"))
            c.rect(x, y, w, h, fill=1, stroke=0)
            c.setFont(F_BOLD, 18)
            c.setFillColor(HexColor("#C00000"))
            c.drawCentredString(x + w/2, y + h/2, f"MISSING: {os.path.basename(path)}")
            return
        # Maintain aspect ratio strictly
        im = Image.open(path)
        iw, ih = im.size
        target_h = w * (ih / iw)
        if target_h > h:
            target_h = h
            target_w = h * (iw / ih)
            x_offset = (w - target_w) / 2
            c.drawImage(path, x + x_offset, y, width=target_w, height=target_h, preserveAspectRatio=True)
        else:
            y_offset = (h - target_h) / 2
            c.drawImage(path, x, y + y_offset, width=w, height=target_h, preserveAspectRatio=True)

        if caption:
            c.setFont(F_ITALIC, 15)
            c.setFillColor(C_MUTED)
            c.drawCentredString(x + w/2, y - 4.5*mm, caption)

    # -------------------------------------------------------------------------
    # LEFT COLUMN (Poco Product Content)
    # -------------------------------------------------------------------------
    cy = r3_top

    # Block 1: Problem Statement
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cy - 10*mm, "The Problem")
    cy -= 13*mm
    h = draw_par("Every day, people paste contracts, medical notes, and CVs into ChatGPT. Once they do, names, addresses, and financial details are outside their control. Poco makes that safe.",
                 col1_x, cy, col1_w, F_LIGHT, 22, 26, C_TEXT)
    cy -= (h + 8*mm)

    # Block 2: How It Works
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cy - 10*mm, "How Poco Works")
    cy -= 13*mm
    h = draw_par("Poco detects personal information, replaces each value with a reversible token like [PERSON_1] or [EMAIL_1], and stores the mapping in an encrypted session vault. The redacted text is sent to any LLM, and the response is restored to its original form when it returns.",
                 col1_x, cy, col1_w, F_LIGHT, 22, 26, C_TEXT)
    cy -= (h + 5*mm)

    # Flow Diagram: 3 stages [Paste text] → [Tokenise] → [Restore response]
    flow_h = 32 * mm
    fw = 112 * mm
    arr_w = 12 * mm
    
    # Col 1: Paste text
    c.setFillColor(C_SECONDARY)
    c.roundRect(col1_x, cy - flow_h, fw, flow_h, 2*mm, fill=1, stroke=0)
    c.setFont(F_BOLD, 20)
    c.setFillColor(HexColor("#FFFFFF"))
    c.drawCentredString(col1_x + fw/2, cy - 13*mm, "Paste text")
    c.setFont(F_ITALIC, 14)
    c.drawCentredString(col1_x + fw/2, cy - 23*mm, "User input document")

    # Arrow 1
    c.setFont(F_BOLD, 28)
    c.setFillColor(C_PRIMARY)
    c.drawCentredString(col1_x + fw + arr_w/2, cy - 18*mm, "→")

    # Col 2: Tokenise
    x2 = col1_x + fw + arr_w
    c.setFillColor(C_PRIMARY)
    c.roundRect(x2, cy - flow_h, fw, flow_h, 2*mm, fill=1, stroke=0)
    c.setFont(F_BOLD, 20)
    c.setFillColor(HexColor("#FFFFFF"))
    c.drawCentredString(x2 + fw/2, cy - 13*mm, "Tokenise")
    c.setFont(F_ITALIC, 14)
    c.drawCentredString(x2 + fw/2, cy - 23*mm, "Reversible vault mapping")

    # Arrow 2
    c.setFont(F_BOLD, 28)
    c.setFillColor(C_PRIMARY)
    c.drawCentredString(x2 + fw + arr_w/2, cy - 18*mm, "→")

    # Col 3: Restore response
    x3 = x2 + fw + arr_w
    c.setFillColor(C_SECONDARY)
    c.roundRect(x3, cy - flow_h, fw, flow_h, 2*mm, fill=1, stroke=0)
    c.setFont(F_BOLD, 20)
    c.setFillColor(HexColor("#FFFFFF"))
    c.drawCentredString(x3 + fw/2, cy - 13*mm, "Restore response")
    c.setFont(F_ITALIC, 14)
    c.drawCentredString(x3 + fw/2, cy - 23*mm, "LLM response restored")
    cy -= (flow_h + 10*mm)

    # Block 3: Architecture
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cy - 10*mm, "Architecture")
    cy -= 14*mm

    # Nested architecture stack
    arch_h = 100 * mm
    draw_fig(os.path.join(ASSETS_DIR, "poco_architecture.png"), col1_x, cy - arch_h, col1_w, arch_h,
             caption="Figure 1. Two-pass hybrid PII detection engine.")
    cy -= (arch_h + 14*mm)

    # Block 4: DevOps Pipeline (Heading ONCE only!)
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cy - 10*mm, "DevOps Pipeline")
    cy -= 13*mm
    h = draw_par("Every code change flows through GitHub Actions, which builds the Rust backend inside the Cargo Lambda container, runs unit, integration, and browser acceptance tests, and deploys to four isolated AWS environments. Failed tests block promotion.",
                 col1_x, cy, col1_w, F_LIGHT, 22, 26, C_TEXT)
    cy -= (h + 5*mm)

    # 5-stage pipeline diagram: [Commit] → [Build] → [Test] → [Deploy] → [Monitor]
    pip_h = 30 * mm
    pw = 68 * mm
    parr_w = 9.5 * mm
    p_stages = [
        ("Commit", "GitHub Actions", C_PRIMARY),
        ("Build", "Cargo Lambda", C_SECONDARY),
        ("Test", "Unit & Playwright", C_PRIMARY),
        ("Deploy", "Dev · Staging · Prod", C_SECONDARY),
        ("Monitor", "CloudWatch", C_PRIMARY)
    ]
    for pi, (st_name, st_sub, st_bg) in enumerate(p_stages):
        px = col1_x + pi * (pw + parr_w)
        c.setFillColor(st_bg)
        c.roundRect(px, cy - pip_h, pw, pip_h, 2*mm, fill=1, stroke=0)
        c.setFont(F_BOLD, 17)
        c.setFillColor(HexColor("#FFFFFF"))
        c.drawCentredString(px + pw/2, cy - 12*mm, st_name)
        c.setFont(F_LIGHT, 11.5)
        c.drawCentredString(px + pw/2, cy - 22*mm, st_sub)

        if pi < 4:
            c.setFont(F_BOLD, 22)
            c.setFillColor(C_PRIMARY)
            c.drawCentredString(px + pw + parr_w/2, cy - 16*mm, "→")
    cy -= (pip_h + 10*mm)

    # Block 5: Live Demo
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x, cy - 10*mm, "Live Demo")
    cy -= 13*mm

    demo_qr_sz = 38 * mm
    c.drawImage(os.path.join(ASSETS_DIR, "qrcode_demo.png"), col1_x, cy - demo_qr_sz, width=demo_qr_sz, height=demo_qr_sz)
    c.setFont(F_BOLD, 26)
    c.setFillColor(C_PRIMARY)
    c.drawString(col1_x + demo_qr_sz + 8*mm, cy - 14*mm, "littlepoco.me")
    c.setFont(F_LIGHT, 18)
    c.setFillColor(C_SECONDARY)
    c.drawString(col1_x + demo_qr_sz + 8*mm, cy - 25*mm, "Scan to test confidentiality vault")
    cy -= (demo_qr_sz + 6*mm)

    ui_h = 100 * mm
    draw_fig(os.path.join(ASSETS_DIR, "poco_screenshot.png"), col1_x, cy - ui_h, col1_w, ui_h,
             caption="Figure 2. Poco encode view with coloured token highlighting.")

    # -------------------------------------------------------------------------
    # CENTRE COLUMN (EDA Figures 1–10)
    # -------------------------------------------------------------------------
    cy = r3_top

    # Sub-heading 1: Dataset Overview
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cy - 9*mm, "Dataset Overview")
    cy -= 12*mm
    h = draw_par("Analysis of 1,636,375 multilingual documents across 30 languages, 11.9 million PII annotations, and 43 discovered PII entity classes.",
                 col2_x, cy, col2_w, F_LIGHT, 21, 25, C_TEXT)
    cy -= (h + 4*mm)

    # Metrics strip: 4 cols x 2 rows
    m_w = (col2_w - 9*mm) / 4
    m_h = 32 * mm
    metrics = [("1,636,375", "Examples"), ("11,887,370", "Annotations"), ("43", "PII classes"), ("30", "Languages")]
    for mi, (num, lbl) in enumerate(metrics):
        mx = col2_x + mi * (m_w + 3*mm)
        c.setFillColor(C_PANEL)
        c.setStrokeColor(C_BORDER)
        c.roundRect(mx, cy - m_h, m_w, m_h, 2*mm, fill=1, stroke=1)
        c.setFont(F_BOLD, 26)
        c.setFillColor(C_PRIMARY)
        c.drawCentredString(mx + m_w/2, cy - 13*mm, num)
        c.setFont(F_LIGHT, 16)
        c.setFillColor(HexColor("#404040"))
        c.drawCentredString(mx + m_w/2, cy - 24*mm, lbl)
    cy -= (m_h + 8*mm)

    # Sub-heading 2: Label Distribution (Fig 1 & Fig 2 side by side)
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cy - 9*mm, "Label Distribution")
    cy -= 12*mm
    half_cw = (col2_w - 6*mm) / 2
    f_h2 = 82 * mm
    draw_fig(os.path.join(EDA_DIR, "fig1_label_distribution.png"), col2_x, cy - f_h2, half_cw, f_h2,
             caption="Figure 3. Top 25 labels by viability tier.")
    draw_fig(os.path.join(EDA_DIR, "fig2_label_log.png"), col2_x + half_cw + 6*mm, cy - f_h2, half_cw, f_h2,
             caption="Figure 4. 43-label taxonomy (log scale).")
    cy -= (f_h2 + 12*mm)

    # Sub-heading 3: Class Viability
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cy - 9*mm, "Class Viability")
    cy -= 12*mm
    h = draw_par("Only 20 of 43 discovered labels are viable for supervised training. 4 are marginal; 19 are unviable (<100 corpus annotations, down to single occurrences). The unviable labels are handled by deterministic regex in Poco.",
                 col2_x, cy, col2_w, F_LIGHT, 21, 25, C_TEXT)
    cy -= (h + 6*mm)

    # Sub-heading 4: Language Coverage (Fig 3 & Fig 4 side by side)
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cy - 9*mm, "Language Coverage")
    cy -= 12*mm
    f_h4 = 82 * mm
    draw_fig(os.path.join(EDA_DIR, "fig3_languages.png"), col2_x, cy - f_h4, half_cw, f_h4,
             caption="Figure 5. Language representation (30 langs).")
    draw_fig(os.path.join(EDA_DIR, "fig4_region_lang.png"), col2_x + half_cw + 6*mm, cy - f_h4, half_cw, f_h4,
             caption="Figure 6. Region × language coverage map.")
    cy -= (f_h4 + 12*mm)

    # Sub-heading 5: Document Lengths (Fig 5 & Fig 7 side by side)
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cy - 9*mm, "Document Lengths")
    cy -= 12*mm
    f_h5 = 75 * mm
    draw_fig(os.path.join(EDA_DIR, "fig5_entities_per_example.png"), col2_x, cy - f_h5, half_cw, f_h5,
             caption="Figure 7. Entities per document distribution.")
    draw_fig(os.path.join(EDA_DIR, "fig7_token_lengths.png"), col2_x + half_cw + 6*mm, cy - f_h5, half_cw, f_h5,
             caption="Figure 8. mBERT token lengths (512 cap).")
    cy -= (f_h5 + 12*mm)

    # Sub-heading 6: Entity Characteristics (Fig 8 & Fig 6 side by side)
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col2_x, cy - 9*mm, "Entity Characteristics")
    cy -= 12*mm
    f_h6 = 82 * mm
    draw_fig(os.path.join(EDA_DIR, "fig8_span_lengths.png"), col2_x, cy - f_h6, half_cw, f_h6,
             caption="Figure 9. Average word span length by class.")
    draw_fig(os.path.join(EDA_DIR, "fig6_cooccurrence.png"), col2_x + half_cw + 6*mm, cy - f_h6, half_cw, f_h6,
             caption="Figure 10. Entity co-occurrence matrix.")
    cy -= (f_h6 + 10*mm)

    # -------------------------------------------------------------------------
    # RIGHT COLUMN (EDA Figures 11–22 + Findings Summary)
    # -------------------------------------------------------------------------
    cy = r3_top

    # Sub-heading 7: Per-Language Composition
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cy - 9*mm, "Per-Language Composition")
    cy -= 12*mm
    f_h9 = 70 * mm
    draw_fig(os.path.join(EDA_DIR, "fig9_language_entity_composition.png"), col3_x, cy - f_h9, col3_w, f_h9,
             caption="Figure 11. Per-language composition across 8 Asia-Pacific languages.")
    cy -= (f_h9 + 9*mm)
    h = draw_par("Chi-square p < 10⁻³⁰⁰, but Cramér's V = 0.017 shows the effect is negligible — the generator produces uniform proportions.",
                 col3_x, cy, col3_w, F_LIGHT, 19, 23, C_TEXT)
    cy -= (h + 5*mm)

    # Sub-heading 8: Data Quality (4 boxplots/histograms in 2x2 grid)
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cy - 9*mm, "Data Quality")
    cy -= 12*mm
    half_r3w = (col3_w - 6*mm) / 2
    f_dq = 48 * mm
    draw_fig(os.path.join(EDA_DIR, "fig10_precleaning_boxplots.png"), col3_x, cy - f_dq, half_r3w, f_dq,
             caption="Figure 12. Pre-cleaning boxplots.")
    draw_fig(os.path.join(EDA_DIR, "fig11_precleaning_histograms.png"), col3_x + half_r3w + 6*mm, cy - f_dq, half_r3w, f_dq,
             caption="Figure 13. Pre-cleaning histograms.")
    cy -= (f_dq + 10*mm)

    draw_fig(os.path.join(EDA_DIR, "fig12_cleaned_boxplots.png"), col3_x, cy - f_dq, half_r3w, f_dq,
             caption="Figure 14. Winsorised boxplots (P99).")
    draw_fig(os.path.join(EDA_DIR, "fig13_cleaned_histograms.png"), col3_x + half_r3w + 6*mm, cy - f_dq, half_r3w, f_dq,
             caption="Figure 15. Cleaned histograms.")
    cy -= (f_dq + 10*mm)

    # Sub-heading 9 & 10: Normalisation & Correlation Structure (Fig 14 & Fig 15 side by side)
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cy - 9*mm, "Normalisation & Correlation")
    cy -= 12*mm
    f_nc = 65 * mm
    draw_fig(os.path.join(EDA_DIR, "fig14_normalisation_comparison.png"), col3_x, cy - f_nc, half_r3w, f_nc,
             caption="Figure 16. Raw vs MinMax vs Z-score vs Log1p.")
    draw_fig(os.path.join(EDA_DIR, "fig15_correlation_heatmap.png"), col3_x + half_r3w + 6*mm, cy - f_nc, half_r3w, f_nc,
             caption="Figure 17. Pearson correlation matrix.")
    cy -= (f_nc + 10*mm)

    # Sub-heading 10 & 11: Pair Plots & Stratified Count (Fig 16 & Fig 17 side by side)
    draw_fig(os.path.join(EDA_DIR, "fig16_pairplots.png"), col3_x, cy - f_nc, half_r3w, f_nc,
             caption="Figure 18. Bivariate pair plot (100k subsample).")
    draw_fig(os.path.join(EDA_DIR, "fig17_target_vs_predictors_boxplots.png"), col3_x + half_r3w + 6*mm, cy - f_nc, half_r3w, f_nc,
             caption="Figure 19. Entity count by capacity quintile.")
    cy -= (f_nc + 10*mm)

    # Sub-heading 12 & 13: Tokenizer Expansion & Split Parity (Fig 18, Fig 19, Fig 20 in 3-col strip)
    c.setFont(F_BOLD, 34)
    c.setFillColor(C_PRIMARY)
    c.drawString(col3_x, cy - 9*mm, "Tokenizer Expansion & Split Parity")
    cy -= 12*mm
    h = draw_par("Full-corpus census confirmed that all 20 viable classes follow the 80.05% / 19.95% train/val split with |Δ| < 0.08%.",
                 col3_x, cy, col3_w, F_LIGHT, 19, 23, C_TEXT)
    cy -= (h + 4*mm)

    third_w = (col3_w - 8*mm) / 3
    f_sp = 58 * mm
    draw_fig(os.path.join(EDA_DIR, "fig18_cjk_token_efficiency.png"), col3_x, cy - f_sp, third_w, f_sp,
             caption="Fig 20. CJK expansion (2.4×).")
    draw_fig(os.path.join(EDA_DIR, "fig19_train_val_split_parity.png"), col3_x + third_w + 4*mm, cy - f_sp, third_w, f_sp,
             caption="Fig 21. Split parity.")
    draw_fig(os.path.join(EDA_DIR, "fig20_rare_label_imbalance.png"), col3_x + 2*(third_w + 4*mm), cy - f_sp, third_w, f_sp,
             caption="Fig 22. Validation blindness.")
    cy -= (f_sp + 10*mm)

    # -------------------------------------------------------------------------
    # ROW 4: DEMO / QR STRIP (Merged 3 Columns: Repo QR, Live Demo QR, EDA QR)
    # -------------------------------------------------------------------------
    r4_top = MARGIN + 62*mm # ~77 mm
    r4_h = 36 * mm
    r4_y = r4_top - r4_h

    # Container panel
    c.setFillColor(C_PANEL)
    c.setStrokeColor(C_BORDER)
    c.setLineWidth(1)
    c.roundRect(MARGIN, r4_y, usable_w, r4_h, 3*mm, fill=1, stroke=1)

    qr_col_w = usable_w / 3
    qr_img_sz = 30 * mm

    # Left cell: Repository QR
    q1_x = MARGIN + 10*mm
    c.drawImage(os.path.join(ASSETS_DIR, "qrcode_repo.png"), q1_x, r4_y + (r4_h - qr_img_sz)/2, width=qr_img_sz, height=qr_img_sz)
    c.setFont(F_BOLD, 22)
    c.setFillColor(C_PRIMARY)
    c.drawString(q1_x + qr_img_sz + 8*mm, r4_y + r4_h*0.58, "Repository")
    c.setFont(F_LIGHT, 17)
    c.setFillColor(C_MUTED)
    c.drawString(q1_x + qr_img_sz + 8*mm, r4_y + r4_h*0.25, "github.com/Schnitze1/Poco")

    # Centre cell: Live Demo QR
    q2_x = MARGIN + qr_col_w + 10*mm
    c.drawImage(os.path.join(ASSETS_DIR, "qrcode_demo.png"), q2_x, r4_y + (r4_h - qr_img_sz)/2, width=qr_img_sz, height=qr_img_sz)
    c.setFont(F_BOLD, 22)
    c.setFillColor(C_PRIMARY)
    c.drawString(q2_x + qr_img_sz + 8*mm, r4_y + r4_h*0.58, "Live Demo")
    c.setFont(F_LIGHT, 17)
    c.setFillColor(C_MUTED)
    c.drawString(q2_x + qr_img_sz + 8*mm, r4_y + r4_h*0.25, "littlepoco.me")

    # Right cell: Full EDA Report QR
    q3_x = MARGIN + 2*qr_col_w + 10*mm
    c.drawImage(os.path.join(ASSETS_DIR, "qrcode_eda.png"), q3_x, r4_y + (r4_h - qr_img_sz)/2, width=qr_img_sz, height=qr_img_sz)
    c.setFont(F_BOLD, 22)
    c.setFillColor(C_PRIMARY)
    c.drawString(q3_x + qr_img_sz + 8*mm, r4_y + r4_h*0.58, "Full EDA Report")
    c.setFont(F_LIGHT, 17)
    c.setFillColor(C_MUTED)
    c.drawString(q3_x + qr_img_sz + 8*mm, r4_y + r4_h*0.25, "Scan for full-corpus analysis")

    # -------------------------------------------------------------------------
    # ROW 5: FOOTER STRIP (One centered line)
    # -------------------------------------------------------------------------
    r5_y = MARGIN + 4*mm
    c.setFont(F_LIGHT, 20)
    c.setFillColor(C_MUTED)
    c.drawCentredString(PAGE_W / 2, r5_y + 4*mm, "Poco — Preserve Originals, Conceal Only  |  October 2026")

    c.showPage()
    c.save()
    print("ReportLab Master A0 PDF generated successfully!")

if __name__ == "__main__":
    generate_master_pdf()
