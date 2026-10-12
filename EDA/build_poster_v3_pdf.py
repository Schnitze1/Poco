import os
import sys
from PIL import Image
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
PDF_OUT = os.path.join(POSTER_DIR, "POCO_A0_Poster_CL01_G01.pdf")
os.makedirs(POSTER_DIR, exist_ok=True)

# Register fonts
FONTS_DIR = r"C:\Windows\Fonts"
try:
    pdfmetrics.registerFont(TTFont("SegoeUI", os.path.join(FONTS_DIR, "segoeui.ttf")))
    pdfmetrics.registerFont(TTFont("SegoeUI-Bold", os.path.join(FONTS_DIR, "segoeuib.ttf")))
    pdfmetrics.registerFont(TTFont("SegoeUI-Light", os.path.join(FONTS_DIR, "segoeuil.ttf")))
    pdfmetrics.registerFont(TTFont("SegoeUI-Italic", os.path.join(FONTS_DIR, "segoeuii.ttf")))
    pdfmetrics.registerFont(TTFont("Arial-Bold", os.path.join(FONTS_DIR, "arialbd.ttf")))
    F_BODY = "SegoeUI"
    F_BOLD = "SegoeUI-Bold"
    F_LIGHT = "SegoeUI-Light"
    F_ITALIC = "SegoeUI-Italic"
    F_HERO = "Arial-Bold"
except Exception as e:
    print(f"Font loading error: {e}")
    F_BODY = "Helvetica"
    F_BOLD = "Helvetica-Bold"
    F_LIGHT = "Helvetica"
    F_ITALIC = "Helvetica-Oblique"
    F_HERO = "Helvetica-Bold"

# Exact Color Palette from Canva / Editorial Guide
C_PRIMARY_DARK = HexColor("#1F3864")  # Deep navy
C_PRIMARY_MID  = HexColor("#2E75B6")  # Medium blue
C_ACCENT       = HexColor("#ED7D31")  # Burnt orange
C_BG           = HexColor("#FAF9F5")  # Warm off-white
C_PANEL        = HexColor("#EAF1F8")  # Light blue tint
C_TEXT_DARK    = HexColor("#1A1A1A")  # Near-black
C_TEXT_MUTED   = HexColor("#6B6B6B")  # Medium grey
C_WHITE        = HexColor("#FFFFFF")

PAGE_W = 1189 * mm
PAGE_H = 841 * mm

def draw_paragraph(c, text, x, y, width, font_name, font_size, leading, color):
    style = ParagraphStyle(
        name='CustomStyle',
        fontName=font_name,
        fontSize=font_size,
        leading=leading,
        textColor=color
    )
    p = Paragraph(text, style)
    w, h = p.wrap(width, 1000 * mm)
    p.drawOn(c, x, y - h)
    return h

def draw_image_locked(c, img_path, x, y, w, h, caption=None, cap_size=12):
    if not os.path.exists(img_path):
        c.setFillColor(HexColor("#FFF0F0"))
        c.rect(x, y, w, h, fill=1, stroke=0)
        c.setFont(F_BOLD, 14)
        c.setFillColor(HexColor("#CC0000"))
        c.drawCentredString(x + w/2, y + h/2, f"MISSING: {os.path.basename(img_path)}")
        return
    
    # Compute locked aspect ratio
    im = Image.open(img_path)
    iw, ih = im.size
    aspect = iw / ih
    target_h = w / aspect
    if target_h > h:
        target_h = h
        target_w = h * aspect
        x_off = (w - target_w) / 2
        c.drawImage(img_path, x + x_off, y, width=target_w, height=target_h, preserveAspectRatio=True)
    else:
        y_off = (h - target_h) / 2
        c.drawImage(img_path, x, y + y_off, width=w, height=target_h, preserveAspectRatio=True)
    
    if caption:
        c.setFont(F_ITALIC, cap_size)
        c.setFillColor(C_TEXT_MUTED)
        c.drawCentredString(x + w/2, y - 4*mm, caption)

def generate_poster():
    print(f"Creating High-Distinction A0 Landscape poster: {PDF_OUT}")
    c = canvas.Canvas(PDF_OUT, pagesize=(PAGE_W, PAGE_H))

    # STEP 2 — Set the Background: Warm off-white #FAF9F5
    c.setFillColor(C_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # -------------------------------------------------------------------------
    # STEP 3 — Build the Top Band (Solid Deep Navy #1F3864, Full Width)
    # -------------------------------------------------------------------------
    top_band_h = 140 * mm
    top_band_y = PAGE_H - top_band_h # 701 mm
    c.setFillColor(C_PRIMARY_DARK)
    c.rect(0, top_band_y, PAGE_W, top_band_h, fill=1, stroke=0)

    # Title: POCO (large bold white)
    c.setFont(F_HERO, 175)
    c.setFillColor(C_WHITE)
    c.drawString(40 * mm, top_band_y + 42 * mm, "POCO")

    # Subtitle: Preserve Originals, Conceal Only (Burnt Orange #ED7D31)
    c.setFont(F_BOLD, 46)
    c.setFillColor(C_ACCENT)
    c.drawString(45 * mm, top_band_y + 14 * mm, "Preserve Originals, Conceal Only")

    # One-line pitch (white)
    pitch_text = "Reversible PII anonymisation for LLM workflows, with a fully automated multi-environment DevOps pipeline"
    draw_paragraph(c, pitch_text, 540 * mm, top_band_y + 75 * mm, 610 * mm, F_BODY, 25, 32, C_WHITE)

    # -------------------------------------------------------------------------
    # STEP 8 — Build the Bottom Band (Solid Burnt Orange #ED7D31, Full Width)
    # -------------------------------------------------------------------------
    bot_band_h = 61 * mm
    c.setFillColor(C_ACCENT)
    c.rect(0, 0, PAGE_W, bot_band_h, fill=1, stroke=0)

    # QR Codes
    qr_sz = 40 * mm
    qr_y = (bot_band_h - qr_sz) / 2 # 10.5 mm

    # QR 1: Repo
    q1_x = 50 * mm
    c.drawImage(os.path.join(ASSETS_DIR, "qrcode_repo.png"), q1_x, qr_y, width=qr_sz, height=qr_sz)
    c.setFont(F_BOLD, 18)
    c.setFillColor(C_WHITE)
    c.drawString(q1_x + qr_sz + 8*mm, qr_y + 24*mm, "Repository")
    c.setFont(F_BODY, 13)
    c.drawString(q1_x + qr_sz + 8*mm, qr_y + 10*mm, "github.com/Schnitze1/...")

    # QR 2: Live Demo
    q2_x = 240 * mm
    c.drawImage(os.path.join(ASSETS_DIR, "qrcode_demo.png"), q2_x, qr_y, width=qr_sz, height=qr_sz)
    c.setFont(F_BOLD, 18)
    c.setFillColor(C_WHITE)
    c.drawString(q2_x + qr_sz + 8*mm, qr_y + 24*mm, "Live Demo")
    c.setFont(F_BODY, 13)
    c.drawString(q2_x + qr_sz + 8*mm, qr_y + 10*mm, "littlepoco.me")

    # QR 3: Full EDA
    q3_x = 425 * mm
    c.drawImage(os.path.join(ASSETS_DIR, "qrcode_eda.png"), q3_x, qr_y, width=qr_sz, height=qr_sz)
    c.setFont(F_BOLD, 18)
    c.setFillColor(C_WHITE)
    c.drawString(q3_x + qr_sz + 8*mm, qr_y + 24*mm, "Full EDA Report")
    c.setFont(F_BODY, 13)
    c.drawString(q3_x + qr_sz + 8*mm, qr_y + 10*mm, "Scan for 1.63M analysis")

    # Big URL on Right: littlepoco.me
    c.setFont(F_HERO, 46)
    c.setFillColor(C_WHITE)
    c.drawRightString(PAGE_W - 50*mm, qr_y + 10*mm, "littlepoco.me")

    # -------------------------------------------------------------------------
    # STEP 5 — Left Column: Poco Product (Width: 360mm, Panel Fill: #EAF1F8)
    # -------------------------------------------------------------------------
    lp_x = 40 * mm
    lp_w = 360 * mm
    lp_y = bot_band_h + 10 * mm # 71 mm
    lp_h = top_band_y - lp_y - 10 * mm # 620 mm

    c.setFillColor(C_PANEL)
    c.roundRect(lp_x, lp_y, lp_w, lp_h, 8 * mm, fill=1, stroke=0)

    # Content inside left panel
    inner_x = lp_x + 18 * mm
    inner_w = lp_w - 36 * mm # 324 mm
    cy = lp_y + lp_h - 14 * mm

    # 1. The Problem
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawString(inner_x, cy - 10*mm, "The Problem")
    cy -= 14*mm
    h = draw_paragraph(c, "Every day, people paste contracts, medical notes, and CVs into ChatGPT. Once they do, names, addresses, and financial details are outside their control. Poco makes that safe.",
                       inner_x, cy, inner_w, F_BODY, 18, 22, C_TEXT_DARK)
    cy -= (h + 8*mm)

    # 2. How Poco Works
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawString(inner_x, cy - 10*mm, "How Poco Works")
    cy -= 14*mm
    h = draw_paragraph(c, "Poco detects personal information, replaces each value with a reversible token like [PERSON_1] or [EMAIL_1], and stores the mapping in an encrypted session vault. The redacted text is sent to any LLM, and the response is restored to its original form when it returns.",
                       inner_x, cy, inner_w, F_BODY, 18, 22, C_TEXT_DARK)
    cy -= (h + 6*mm)

    # Three-stage flow rectangles
    flow_h = 24 * mm
    rw = (inner_w - 18*mm) / 3 # ~102 mm
    
    # [Paste text]
    c.setFillColor(C_PRIMARY_MID)
    c.roundRect(inner_x, cy - flow_h, rw, flow_h, 3*mm, fill=1, stroke=0)
    c.setFont(F_BOLD, 16)
    c.setFillColor(C_WHITE)
    c.drawCentredString(inner_x + rw/2, cy - 11*mm, "Paste text")
    c.setFont(F_LIGHT, 10.5)
    c.drawCentredString(inner_x + rw/2, cy - 19*mm, "User input document")

    # Arrow 1
    c.setFont(F_BOLD, 20)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawCentredString(inner_x + rw + 4.5*mm, cy - 14*mm, "→")

    # [Tokenise]
    rx2 = inner_x + rw + 9*mm
    c.setFillColor(C_PRIMARY_DARK)
    c.roundRect(rx2, cy - flow_h, rw, flow_h, 3*mm, fill=1, stroke=0)
    c.setFont(F_BOLD, 16)
    c.setFillColor(C_WHITE)
    c.drawCentredString(rx2 + rw/2, cy - 11*mm, "Tokenise")
    c.setFont(F_LIGHT, 10.5)
    c.drawCentredString(rx2 + rw/2, cy - 19*mm, "Reversible vault mapping")

    # Arrow 2
    c.setFont(F_BOLD, 20)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawCentredString(rx2 + rw + 4.5*mm, cy - 14*mm, "→")

    # [Restore]
    rx3 = rx2 + rw + 9*mm
    c.setFillColor(C_PRIMARY_MID)
    c.roundRect(rx3, cy - flow_h, rw, flow_h, 3*mm, fill=1, stroke=0)
    c.setFont(F_BOLD, 16)
    c.setFillColor(C_WHITE)
    c.drawCentredString(rx3 + rw/2, cy - 11*mm, "Restore")
    c.setFont(F_LIGHT, 10.5)
    c.drawCentredString(rx3 + rw/2, cy - 19*mm, "LLM response restored")
    cy -= (flow_h + 9*mm)

    # 3. Architecture
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawString(inner_x, cy - 10*mm, "Architecture")
    cy -= 13*mm
    arch_h = 78 * mm
    draw_image_locked(c, os.path.join(ASSETS_DIR, "poco_architecture.png"), inner_x, cy - arch_h, inner_w, arch_h,
                      caption="Figure 1. Two-pass hybrid PII detection engine.", cap_size=12)
    cy -= (arch_h + 10*mm)

    # 4. DevOps Pipeline (Heading ONCE)
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawString(inner_x, cy - 10*mm, "DevOps Pipeline")
    cy -= 13*mm
    h = draw_paragraph(c, "Code flows through GitHub Actions, building Rust in Cargo Lambda, running unit & browser acceptance tests, deploying to four AWS environments. Failed tests block promotion.",
                       inner_x, cy, inner_w, F_BODY, 17, 21, C_TEXT_DARK)
    cy -= (h + 5*mm)

    # Pipeline stages: [Commit] -> [Build] -> [Test] -> [Deploy] -> [Monitor]
    pip_h = 22 * mm
    pw = (inner_w - 20*mm) / 5 # ~60 mm
    p_stages = [("Commit", C_PRIMARY_DARK), ("Build", C_PRIMARY_MID), ("Test", C_PRIMARY_DARK), ("Deploy", C_PRIMARY_MID), ("Monitor", C_PRIMARY_DARK)]
    for pi, (st_name, st_col) in enumerate(p_stages):
        px = inner_x + pi * (pw + 5*mm)
        c.setFillColor(st_col)
        c.roundRect(px, cy - pip_h, pw, pip_h, 2*mm, fill=1, stroke=0)
        c.setFont(F_BOLD, 13)
        c.setFillColor(C_WHITE)
        c.drawCentredString(px + pw/2, cy - 14*mm, st_name)
        if pi < 4:
            c.setFont(F_BOLD, 15)
            c.setFillColor(C_PRIMARY_DARK)
            c.drawCentredString(px + pw + 2.5*mm, cy - 14*mm, "→")
    cy -= (pip_h + 9*mm)

    # 5. Demo Screenshot
    c.setFont(F_BOLD, 36)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawString(inner_x, cy - 10*mm, "Live Demo")
    cy -= 13*mm
    demo_h = 105 * mm
    draw_image_locked(c, os.path.join(ASSETS_DIR, "poco_screenshot.png"), inner_x, cy - demo_h, inner_w, demo_h,
                      caption="Figure 2. Poco encode view with coloured token highlighting.", cap_size=12)

    # -------------------------------------------------------------------------
    # STEP 6 — Centre Column: Hero EDA Section (Width: 490mm, X: 425mm)
    # -------------------------------------------------------------------------
    col2_x = 425 * mm
    col2_w = 485 * mm
    c2_y = top_band_y - 12 * mm # ~689 mm

    # Section Heading: What the data showed
    c.setFont(F_BOLD, 54)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawString(col2_x, c2_y - 14*mm, "What the data showed")
    c2_y -= 19*mm

    h = draw_paragraph(c, "Full-corpus census of 1,636,375 multilingual documents across 30 languages, 11,887,370 PII annotations, and 43 discovered entity classes. Perfect 80/20 train/val split parity confirms supervised viability.",
                       col2_x, c2_y, col2_w, F_BODY, 19, 24, C_TEXT_DARK)
    c2_y -= (h + 8*mm)

    # Three Hero Figures at generous size (460mm wide each!)
    h_fig_w = 460 * mm
    h_fig_x = col2_x + 12 * mm

    # 1. Fig 19: Train/Val Split Parity
    f19_h = 150 * mm
    draw_image_locked(c, os.path.join(EDA_DIR, "fig19_train_val_split_parity.png"), h_fig_x, c2_y - f19_h, h_fig_w, f19_h,
                      caption="Figure 19. Train/validation split parity across viable labels (80.05% / 19.95%, |Δ| < 0.08%).", cap_size=13)
    c2_y -= (f19_h + 14*mm)

    # 2. Fig 20: Validation Blindness
    f20_h = 145 * mm
    draw_image_locked(c, os.path.join(EDA_DIR, "fig20_rare_label_imbalance.png"), h_fig_x, c2_y - f20_h, h_fig_w, f20_h,
                      caption="Figure 20. Validation blindness across 23 long-tail labels (0 validation instances in 8 classes).", cap_size=13)
    c2_y -= (f20_h + 14*mm)

    # 3. Fig 18: CJK Tokenizer Expansion
    f18_h = 110 * mm
    draw_image_locked(c, os.path.join(EDA_DIR, "fig18_cjk_token_efficiency.png"), h_fig_x, c2_y - f18_h, h_fig_w, f18_h,
                      caption="Figure 18. CJK vs Latin subword expansion (2.4× more tokens consumed per character for Chinese).", cap_size=13)

    # -------------------------------------------------------------------------
    # STEP 4 & 7 — Right Column: Hero Number + Supporting Figures (X: 935mm)
    # -------------------------------------------------------------------------
    col3_x = 935 * mm
    col3_w = 224 * mm
    c3_y = top_band_y - 10 * mm # ~691 mm

    # STEP 4 — The Hero Number: 73:1 (Burnt Orange #ED7D31, 320pt)
    c.setFont(F_HERO, 270)
    c.setFillColor(C_ACCENT)
    c.drawString(col3_x - 10*mm, c3_y - 68*mm, "73:1")

    c.setFont(F_BODY, 19)
    c.setFillColor(C_TEXT_MUTED)
    c.drawString(col3_x, c3_y - 84*mm, "class imbalance — GIVENNAME : TIME")
    c3_y -= 96*mm

    # Section Heading: Supporting analysis
    c.setFont(F_BOLD, 30)
    c.setFillColor(C_PRIMARY_DARK)
    c.drawString(col3_x, c3_y - 8*mm, "Supporting analysis")
    c3_y -= 13*mm

    # Compact 2-column x 4-row grid for Figs 1, 2, 3, 4, 5, 7, 6, 8
    gw = 106 * mm
    gap_x = 10 * mm
    grid_col1_x = col3_x
    grid_col2_x = col3_x + gw + gap_x

    # Row 1: Fig 1 & Fig 2
    gh1 = 56 * mm
    draw_image_locked(c, os.path.join(EDA_DIR, "fig1_label_distribution.png"), grid_col1_x, c3_y - gh1, gw, gh1,
                      caption="Top 25 labels by tier", cap_size=11)
    draw_image_locked(c, os.path.join(EDA_DIR, "fig2_label_log.png"), grid_col2_x, c3_y - gh1, gw, gh1,
                      caption="All 43 labels, log scale", cap_size=11)
    c3_y -= (gh1 + 10*mm)

    # Row 2: Fig 3 & Fig 4
    gh2 = 52 * mm
    draw_image_locked(c, os.path.join(EDA_DIR, "fig3_languages.png"), grid_col1_x, c3_y - gh2, gw, gh2,
                      caption="Language coverage", cap_size=11)
    draw_image_locked(c, os.path.join(EDA_DIR, "fig4_region_lang.png"), grid_col2_x, c3_y - gh2, gw, gh2,
                      caption="Region × language", cap_size=11)
    c3_y -= (gh2 + 10*mm)

    # Row 3: Fig 5 & Fig 7
    gh3 = 50 * mm
    draw_image_locked(c, os.path.join(EDA_DIR, "fig5_entities_per_example.png"), grid_col1_x, c3_y - gh3, gw, gh3,
                      caption="Entity density", cap_size=11)
    draw_image_locked(c, os.path.join(EDA_DIR, "fig7_token_lengths.png"), grid_col2_x, c3_y - gh3, gw, gh3,
                      caption="Token length (512 cap)", cap_size=11)
    c3_y -= (gh3 + 10*mm)

    # Row 4: Fig 6 & Fig 8
    gh4 = 52 * mm
    draw_image_locked(c, os.path.join(EDA_DIR, "fig6_cooccurrence.png"), grid_col1_x, c3_y - gh4, gw, gh4,
                      caption="Co-occurrence", cap_size=11)
    draw_image_locked(c, os.path.join(EDA_DIR, "fig8_span_lengths.png"), grid_col2_x, c3_y - gh4, gw, gh4,
                      caption="Span lengths", cap_size=11)
    c3_y -= (gh4 + 8*mm)

    # Note about remaining figures
    draw_paragraph(c, "<i>Note: Figures 9–17 (multivariate correlation, diagnostic boxplots & normalisation) are available in the full EDA report via QR code.</i>",
                   col3_x, c3_y, col3_w, F_ITALIC, 11, 14, C_TEXT_MUTED)

    # Finalize Page
    c.showPage()
    c.save()
    print("Poster generated successfully with 1 single page!")

if __name__ == "__main__":
    generate_poster()
