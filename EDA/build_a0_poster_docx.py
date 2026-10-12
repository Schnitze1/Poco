import os
import docx
from docx.shared import Mm, Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

EDA_DIR = r"d:\Repos\Poco\EDA"
ASSETS_DIR = os.path.join(EDA_DIR, "poster_assets")
DOCX_OUT = os.path.join(EDA_DIR, "POCO_A0_Poster_CL01_G01.docx")

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner cell padding in twips."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_background(cell, hex_color):
    """Set cell background shading."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_table_borders(table, color="BFBFBF", sz="4", val="single"):
    """Set custom borders on table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="none"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def remove_table_borders(table):
    """Make table completely borderless."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="none"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def add_heading(cell_or_doc, text, level=1, pt_size=32, space_before=10, space_after=4):
    p = cell_or_doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(text)
    run.font.name = "Calibri Light"
    run.font.size = Pt(pt_size)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1F, 0x38, 0x64) # #1F3864 dark navy
    return p

def add_body(cell_or_doc, text, pt_size=24, bold=False, italic=False, color_rgb=(0x26, 0x26, 0x26), space_before=0, space_after=5):
    p = cell_or_doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.name = "Calibri Light"
    run.font.size = Pt(pt_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)
    return p

def add_caption(cell_or_doc, text, pt_size=18, space_before=2, space_after=8):
    p = cell_or_doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(text)
    run.font.name = "Calibri Light"
    run.font.size = Pt(pt_size)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x59, 0x59, 0x59) # #595959 medium grey
    return p

def add_image_safe(cell_or_doc, image_path, width_mm=None, height_mm=None, caption=None):
    if not os.path.exists(image_path):
        p = cell_or_doc.add_paragraph()
        run = p.add_run(f"Figure missing: {os.path.basename(image_path)}")
        run.font.name = "Calibri Light"
        run.font.size = Pt(24)
        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
        return p

    p = cell_or_doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    kwargs = {}
    if width_mm:
        kwargs['width'] = Mm(width_mm)
    if height_mm:
        kwargs['height'] = Mm(height_mm)
    run.add_picture(image_path, **kwargs)

    if caption:
        add_caption(cell_or_doc, caption)
    return p

def build_poster():
    print("Initializing A0 Landscape Word document...")
    doc = docx.Document()
    section = doc.sections[0]
    
    # 1. Exact A0 Landscape Dimensions
    section.page_width = Mm(1189)
    section.page_height = Mm(841)
    section.top_margin = Mm(15)
    section.bottom_margin = Mm(15)
    section.left_margin = Mm(15)
    section.right_margin = Mm(15)

    # Disable hyphenation
    settings = doc.settings._element
    settings.append(parse_xml(f'<w:doNotHyphenate {nsdecls("w")}/>'))

    # Set normal style font
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri Light'
    normal_style.font.size = Pt(24)
    normal_style.font.color.rgb = RGBColor(0x26, 0x26, 0x26)

    # -------------------------------------------------------------------------
    # TOP BAND (Full width: 1159 mm, ~60 mm tall)
    # -------------------------------------------------------------------------
    print("Building Top Band...")
    top_table = doc.add_table(rows=1, cols=2)
    top_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    top_table.autofit = False
    remove_table_borders(top_table)

    # Left cell 60% (~695 mm), Right cell 40% (~464 mm)
    top_table.columns[0].width = Mm(695)
    top_table.columns[1].width = Mm(464)
    top_table.rows[0].cells[0].width = Mm(695)
    top_table.rows[0].cells[1].width = Mm(464)

    c_top_l = top_table.rows[0].cells[0]
    c_top_r = top_table.rows[0].cells[1]
    set_cell_margins(c_top_l, top=40, bottom=40, left=40, right=40)
    set_cell_margins(c_top_r, top=40, bottom=40, left=40, right=40)
    c_top_l.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    c_top_r.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Left: Title & Subtitle
    p_title = c_top_l.paragraphs[0]
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run("Poco — Preserve Originals, Conceal Only")
    r_title.font.name = "Calibri Light"
    r_title.font.size = Pt(72)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    p_sub = c_top_l.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(2)
    p_sub.paragraph_format.space_after = Pt(0)
    r_sub = p_sub.add_run("Privacy-first PII anonymisation for LLM workflows, with a fully automated multi-environment DevOps pipeline")
    r_sub.font.name = "Calibri Light"
    r_sub.font.size = Pt(36)
    r_sub.font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    # Right: Unit, Group, Team
    p_r1 = c_top_r.paragraphs[0]
    p_r1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_r1.paragraph_format.space_before = Pt(0)
    p_r1.paragraph_format.space_after = Pt(2)
    r_r1 = p_r1.add_run("SWE40006 Software Deployment and Evolution")
    r_r1.font.name = "Calibri Light"
    r_r1.font.size = Pt(28)
    r_r1.font.bold = True
    r_r1.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    p_r2 = c_top_r.add_paragraph()
    p_r2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_r2.paragraph_format.space_before = Pt(2)
    p_r2.paragraph_format.space_after = Pt(2)
    r_r2 = p_r2.add_run("Group CL01_G01 | Tutorial: Wednesday 10:30")
    r_r2.font.name = "Calibri Light"
    r_r2.font.size = Pt(24)
    r_r2.font.color.rgb = RGBColor(0x26, 0x26, 0x26)

    p_r3 = c_top_r.add_paragraph()
    p_r3.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_r3.paragraph_format.space_before = Pt(2)
    p_r3.paragraph_format.space_after = Pt(0)
    r_r3 = p_r3.add_run("Jamie Soo (104559690) · Timothy Schabel (105334128) · Sahil (105295665)")
    r_r3.font.name = "Calibri Light"
    r_r3.font.size = Pt(24)
    r_r3.font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    # Divider line (2pt, #1F3864)
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(4)
    p_div.paragraph_format.space_after = Pt(6)
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="16" w:space="1" w:color="1F3864"/></w:pBdr>')
    p_div._p.get_or_add_pPr().append(pBdr)

    # -------------------------------------------------------------------------
    # MAIN BODY: 3 Columns (Left: 380mm, Centre: 380mm, Right: 349mm + gutters)
    # Total = 1159 mm
    # -------------------------------------------------------------------------
    print("Building Main Body (3 columns)...")
    main_table = doc.add_table(rows=1, cols=3)
    main_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    main_table.autofit = False
    remove_table_borders(main_table)

    col_w_left = Mm(385)
    col_w_centre = Mm(385)
    col_w_right = Mm(355)

    main_table.columns[0].width = col_w_left
    main_table.columns[1].width = col_w_centre
    main_table.columns[2].width = col_w_right

    cell_l = main_table.rows[0].cells[0]
    cell_c = main_table.rows[0].cells[1]
    cell_r = main_table.rows[0].cells[2]

    cell_l.width = col_w_left
    cell_c.width = col_w_centre
    cell_r.width = col_w_right

    set_cell_margins(cell_l, top=40, bottom=40, left=40, right=140)
    set_cell_margins(cell_c, top=40, bottom=40, left=90, right=90)
    set_cell_margins(cell_r, top=40, bottom=40, left=140, right=40)

    # =========================================================================
    # LEFT COLUMN (Sections 1 to 5)
    # =========================================================================
    print("  Populating Left Column...")
    # Section 1 — The Problem
    add_heading(cell_l, "The Problem", level=1, pt_size=40, space_before=0, space_after=4)
    add_body(cell_l, "Every day, people paste contracts, medical notes, and CVs into ChatGPT. Once they do, names, addresses, and financial details are outside their control. Poco makes that safe.", pt_size=24, space_after=10)

    # Section 2 — How Poco Works
    add_heading(cell_l, "How Poco Works", level=1, pt_size=40, space_before=8, space_after=4)
    add_body(cell_l, "Poco detects personal information, replaces each value with a reversible token like [PERSON_1] or [EMAIL_1], and stores the mapping in an encrypted session vault. The redacted text is sent to any LLM, and the response is restored to its original form when it returns.", pt_size=24, space_after=6)
    add_image_safe(cell_l, os.path.join(ASSETS_DIR, "flow_diagram.png"), width_mm=365)

    # Section 3 — Architecture
    add_heading(cell_l, "Architecture", level=1, pt_size=40, space_before=10, space_after=4)
    add_image_safe(cell_l, os.path.join(ASSETS_DIR, "poco_architecture.png"), width_mm=365,
                   caption="Figure 1. Two-pass hybrid PII detection engine.")

    # Section 4 — DevOps Pipeline
    add_heading(cell_l, "DevOps Pipeline", level=1, pt_size=40, space_before=8, space_after=4)
    add_body(cell_l, "Every code change flows through GitHub Actions, which builds the Rust backend inside the Cargo Lambda container, runs unit, integration, and browser acceptance tests, and deploys to four isolated AWS environments (Development, Testing, Staging, Production). Failed tests block promotion.", pt_size=24, space_after=6)
    add_image_safe(cell_l, os.path.join(ASSETS_DIR, "devops_pipeline.png"), width_mm=365)

    # Section 5 — Demo
    add_heading(cell_l, "Demo", level=1, pt_size=40, space_before=10, space_after=4)
    
    # Sub-table for QR code + Demo Text
    demo_tbl = cell_l.add_table(rows=1, cols=2)
    demo_tbl.autofit = False
    remove_table_borders(demo_tbl)
    demo_tbl.columns[0].width = Mm(70)
    demo_tbl.columns[1].width = Mm(295)
    demo_tbl.rows[0].cells[0].width = Mm(70)
    demo_tbl.rows[0].cells[1].width = Mm(295)
    
    qr_cell = demo_tbl.rows[0].cells[0]
    txt_cell = demo_tbl.rows[0].cells[1]
    set_cell_margins(qr_cell, 0, 0, 0, 100)
    set_cell_margins(txt_cell, 0, 0, 50, 0)
    qr_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    txt_cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    add_image_safe(qr_cell, os.path.join(ASSETS_DIR, "qr_demo.png"), width_mm=55)
    
    p_demo_txt = txt_cell.paragraphs[0]
    p_demo_txt.paragraph_format.space_before = Pt(0)
    p_demo_txt.paragraph_format.space_after = Pt(2)
    r_demo1 = p_demo_txt.add_run("Live demo:\n")
    r_demo1.font.name = "Calibri Light"
    r_demo1.font.size = Pt(24)
    r_demo1.font.bold = True
    r_demo1.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    
    r_demo2 = p_demo_txt.add_run("littlepoco.me")
    r_demo2.font.name = "Calibri Light"
    r_demo2.font.size = Pt(24)
    r_demo2.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    # Encode view screenshot
    add_image_safe(cell_l, os.path.join(ASSETS_DIR, "poco_encode_view.png"), width_mm=365,
                   caption="Figure 2. Poco encode view with coloured token highlighting.")

    # =========================================================================
    # CENTRE COLUMN (Sections 6 to 11)
    # =========================================================================
    print("  Populating Centre Column...")
    # Section 6 — Dataset: AI4Privacy OpenPII 1.5M
    add_heading(cell_c, "Dataset: AI4Privacy OpenPII 1.5M", level=1, pt_size=40, space_before=0, space_after=4)
    add_body(cell_c, "Analysis of 1,636,375 multilingual documents across 30 languages, 11.9 million PII annotations, and 43 discovered PII entity classes. Full-corpus census completed and cached to Parquet.", pt_size=24, space_after=6)

    # Key stats box: rounded/bordered panel, background #F2F2F2
    stats_tbl = cell_c.add_table(rows=1, cols=4)
    stats_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    stats_tbl.autofit = False
    set_table_borders(stats_tbl, color="BFBFBF", sz="4")
    
    col_stat_w = Mm(91)
    for i in range(4):
        stats_tbl.columns[i].width = col_stat_w
        stats_tbl.rows[0].cells[i].width = col_stat_w
        set_cell_background(stats_tbl.rows[0].cells[i], "F2F2F2")
        set_cell_margins(stats_tbl.rows[0].cells[i], top=120, bottom=120, left=50, right=50)

    stats_data = [
        ("1,636,375", "Total examples"),
        ("11,887,370", "Total annotations"),
        ("43", "PII entity classes"),
        ("30", "Languages")
    ]
    for i, (num, label) in enumerate(stats_data):
        sc = stats_tbl.rows[0].cells[i]
        p_num = sc.paragraphs[0]
        p_num.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_num.paragraph_format.space_before = Pt(0)
        p_num.paragraph_format.space_after = Pt(2)
        r_n = p_num.add_run(num)
        r_n.font.name = "Calibri Light"
        r_n.font.size = Pt(28)
        r_n.font.bold = True
        r_n.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

        p_lbl = sc.add_paragraph()
        p_lbl.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_lbl.paragraph_format.space_before = Pt(0)
        p_lbl.paragraph_format.space_after = Pt(0)
        r_l = p_lbl.add_run(label)
        r_l.font.name = "Calibri Light"
        r_l.font.size = Pt(20)
        r_l.font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    # Section 7 — Label Distribution (Figs 1 & 2 side by side)
    add_heading(cell_c, "Label Distribution", level=2, pt_size=32, space_before=8, space_after=4)
    s7_tbl = cell_c.add_table(rows=1, cols=2)
    s7_tbl.autofit = False
    remove_table_borders(s7_tbl)
    s7_tbl.columns[0].width = Mm(182)
    s7_tbl.columns[1].width = Mm(182)
    s7_tbl.rows[0].cells[0].width = Mm(182)
    s7_tbl.rows[0].cells[1].width = Mm(182)
    set_cell_margins(s7_tbl.rows[0].cells[0], 0, 0, 0, 50)
    set_cell_margins(s7_tbl.rows[0].cells[1], 0, 0, 50, 0)
    add_image_safe(s7_tbl.rows[0].cells[0], os.path.join(EDA_DIR, "fig1_label_distribution.png"), width_mm=178,
                   caption="Figure 3. Top 25 PII labels, colour-coded by training viability tier.")
    add_image_safe(s7_tbl.rows[0].cells[1], os.path.join(EDA_DIR, "fig2_label_log.png"), width_mm=178,
                   caption="Figure 4. Complete 43-label taxonomy on log scale.")

    # Section 8 — Class Viability
    add_heading(cell_c, "Class Viability", level=2, pt_size=32, space_before=8, space_after=4)
    add_body(cell_c, "Only 20 of the 43 discovered labels are viable for supervised training. 4 are marginal, and 19 are unviable (<100 corpus annotations, down to single occurrences). The unviable labels are handled by deterministic regex in Poco.", pt_size=22, space_after=6)

    # Section 9 — Language Coverage (Figs 3 & 4 side by side)
    add_heading(cell_c, "Language Coverage", level=2, pt_size=32, space_before=8, space_after=4)
    s9_tbl = cell_c.add_table(rows=1, cols=2)
    s9_tbl.autofit = False
    remove_table_borders(s9_tbl)
    s9_tbl.columns[0].width = Mm(182)
    s9_tbl.columns[1].width = Mm(182)
    s9_tbl.rows[0].cells[0].width = Mm(182)
    s9_tbl.rows[0].cells[1].width = Mm(182)
    set_cell_margins(s9_tbl.rows[0].cells[0], 0, 0, 0, 50)
    set_cell_margins(s9_tbl.rows[0].cells[1], 0, 0, 50, 0)
    add_image_safe(s9_tbl.rows[0].cells[0], os.path.join(EDA_DIR, "fig3_languages.png"), width_mm=178,
                   caption="Figure 5. Full-corpus language representation across 30 languages.")
    add_image_safe(s9_tbl.rows[0].cells[1], os.path.join(EDA_DIR, "fig4_region_lang.png"), width_mm=178,
                   caption="Figure 6. Region × language cross-tabulation.")

    # Section 10 — Document Lengths (Figs 5 & 7 side by side)
    add_heading(cell_c, "Document Lengths", level=2, pt_size=32, space_before=8, space_after=4)
    s10_tbl = cell_c.add_table(rows=1, cols=2)
    s10_tbl.autofit = False
    remove_table_borders(s10_tbl)
    s10_tbl.columns[0].width = Mm(182)
    s10_tbl.columns[1].width = Mm(182)
    s10_tbl.rows[0].cells[0].width = Mm(182)
    s10_tbl.rows[0].cells[1].width = Mm(182)
    set_cell_margins(s10_tbl.rows[0].cells[0], 0, 0, 0, 50)
    set_cell_margins(s10_tbl.rows[0].cells[1], 0, 0, 50, 0)
    add_image_safe(s10_tbl.rows[0].cells[0], os.path.join(EDA_DIR, "fig5_entities_per_example.png"), width_mm=178,
                   caption="Figure 7. PII entities per document distribution.")
    add_image_safe(s10_tbl.rows[0].cells[1], os.path.join(EDA_DIR, "fig7_token_lengths.png"), width_mm=178,
                   caption="Figure 8. mBERT token length distribution with 512-token ceiling.")

    # Section 11 — Entity Span Lengths & Co-occurrence (Figs 8 & 6 side by side)
    add_heading(cell_c, "Entity Span Lengths & Co-occurrence", level=2, pt_size=32, space_before=8, space_after=4)
    s11_tbl = cell_c.add_table(rows=1, cols=2)
    s11_tbl.autofit = False
    remove_table_borders(s11_tbl)
    s11_tbl.columns[0].width = Mm(182)
    s11_tbl.columns[1].width = Mm(182)
    s11_tbl.rows[0].cells[0].width = Mm(182)
    s11_tbl.rows[0].cells[1].width = Mm(182)
    set_cell_margins(s11_tbl.rows[0].cells[0], 0, 0, 0, 50)
    set_cell_margins(s11_tbl.rows[0].cells[1], 0, 0, 50, 0)
    add_image_safe(s11_tbl.rows[0].cells[0], os.path.join(EDA_DIR, "fig8_span_lengths.png"), width_mm=178,
                   caption="Figure 9. Average word span length by entity class.")
    add_image_safe(s11_tbl.rows[0].cells[1], os.path.join(EDA_DIR, "fig6_cooccurrence.png"), width_mm=178,
                   caption="Figure 9b. Multilingual PII entity co-occurrence matrix (full corpus).")

    # =========================================================================
    # RIGHT COLUMN (Sections 12 to 19)
    # =========================================================================
    print("  Populating Right Column...")
    # Section 12 — Per-Language Composition
    add_heading(cell_r, "Per-Language Composition", level=2, pt_size=32, space_before=0, space_after=4)
    add_image_safe(cell_r, os.path.join(EDA_DIR, "fig9_language_entity_composition.png"), width_mm=345,
                   caption="Figure 10. Per-language entity composition across 8 Asia-Pacific languages.")
    add_body(cell_r, "Chi-square p < 10⁻³⁰⁰, but Cramér's V = 0.017 shows the effect is negligible — the synthetic generator produces uniform proportions.", pt_size=20, space_after=6)

    # Section 13 — Data Quality (2x2 grid: Figs 10, 11, 12, 13)
    add_heading(cell_r, "Data Quality", level=2, pt_size=32, space_before=6, space_after=4)
    s13_tbl = cell_r.add_table(rows=2, cols=2)
    s13_tbl.autofit = False
    remove_table_borders(s13_tbl)
    s13_w = Mm(170)
    for row in s13_tbl.rows:
        row.cells[0].width = s13_w
        row.cells[1].width = s13_w
        set_cell_margins(row.cells[0], 0, 0, 0, 40)
        set_cell_margins(row.cells[1], 0, 0, 40, 0)
    
    add_image_safe(s13_tbl.rows[0].cells[0], os.path.join(EDA_DIR, "fig10_precleaning_boxplots.png"), width_mm=166,
                   caption="Figure 11. Diagnostic boxplots.")
    add_image_safe(s13_tbl.rows[0].cells[1], os.path.join(EDA_DIR, "fig11_precleaning_histograms.png"), width_mm=166,
                   caption="Figure 12. Distribution histograms.")
    add_image_safe(s13_tbl.rows[1].cells[0], os.path.join(EDA_DIR, "fig12_cleaned_boxplots.png"), width_mm=166,
                   caption="Figure 13. Winsorised boxplots at P99.")
    add_image_safe(s13_tbl.rows[1].cells[1], os.path.join(EDA_DIR, "fig13_cleaned_histograms.png"), width_mm=166,
                   caption="Figure 14. Cleaned histograms.")

    # Section 14 & 15 — Normalisation & Correlation Matrix
    add_heading(cell_r, "Normalisation & Correlation", level=2, pt_size=32, space_before=6, space_after=4)
    s14_tbl = cell_r.add_table(rows=1, cols=2)
    s14_tbl.autofit = False
    remove_table_borders(s14_tbl)
    s14_tbl.columns[0].width = Mm(170)
    s14_tbl.columns[1].width = Mm(170)
    s14_tbl.rows[0].cells[0].width = Mm(170)
    s14_tbl.rows[0].cells[1].width = Mm(170)
    set_cell_margins(s14_tbl.rows[0].cells[0], 0, 0, 0, 40)
    set_cell_margins(s14_tbl.rows[0].cells[1], 0, 0, 40, 0)
    add_image_safe(s14_tbl.rows[0].cells[0], os.path.join(EDA_DIR, "fig14_normalisation_comparison.png"), width_mm=166,
                   caption="Figure 15. Raw vs MinMax vs Z-score vs Log1p.")
    add_image_safe(s14_tbl.rows[0].cells[1], os.path.join(EDA_DIR, "fig15_correlation_heatmap.png"), width_mm=166,
                   caption="Figure 16. Multivariate Pearson matrix.")

    # Section 15 & 16 — Bivariate Pairplots & Target Stratification
    s15_tbl = cell_r.add_table(rows=1, cols=2)
    s15_tbl.autofit = False
    remove_table_borders(s15_tbl)
    s15_tbl.columns[0].width = Mm(170)
    s15_tbl.columns[1].width = Mm(170)
    s15_tbl.rows[0].cells[0].width = Mm(170)
    s15_tbl.rows[0].cells[1].width = Mm(170)
    set_cell_margins(s15_tbl.rows[0].cells[0], 0, 0, 0, 40)
    set_cell_margins(s15_tbl.rows[0].cells[1], 0, 0, 40, 0)
    add_image_safe(s15_tbl.rows[0].cells[0], os.path.join(EDA_DIR, "fig16_pairplots.png"), width_mm=166,
                   caption="Figure 17. Bivariate relationships.")
    add_image_safe(s15_tbl.rows[0].cells[1], os.path.join(EDA_DIR, "fig17_target_vs_predictors_boxplots.png"), width_mm=166,
                   caption="Figure 18. Entity count by quintile.")

    # Section 17 & 18 — Tokenizer Expansion & Split Parity Audit
    add_heading(cell_r, "Tokenizer Expansion & Split Parity", level=2, pt_size=32, space_before=6, space_after=4)
    add_body(cell_r, "Full-corpus census confirmed that all 20 viable classes follow the 80.05% / 19.95% train/val split with |Δ| < 0.08%.", pt_size=20, space_after=4)

    s17_tbl = cell_r.add_table(rows=1, cols=3)
    s17_tbl.autofit = False
    remove_table_borders(s17_tbl)
    w_t3 = Mm(113)
    for i in range(3):
        s17_tbl.columns[i].width = w_t3
        s17_tbl.rows[0].cells[i].width = w_t3
        set_cell_margins(s17_tbl.rows[0].cells[i], 0, 0, 20, 20)
    
    add_image_safe(s17_tbl.rows[0].cells[0], os.path.join(EDA_DIR, "fig18_cjk_token_efficiency.png"), width_mm=110,
                   caption="Figure 19. CJK expansion (2.4×).")
    add_image_safe(s17_tbl.rows[0].cells[1], os.path.join(EDA_DIR, "fig19_train_val_split_parity.png"), width_mm=110,
                   caption="Figure 20. Split parity.")
    add_image_safe(s17_tbl.rows[0].cells[2], os.path.join(EDA_DIR, "fig20_rare_label_imbalance.png"), width_mm=110,
                   caption="Figure 21. Validation blindness.")

    # Section 19 — Key Findings
    add_heading(cell_r, "Key Findings", level=1, pt_size=40, space_before=8, space_after=4)
    findings = [
        "1. 20 of 43 discovered labels are viable for supervised training",
        "2. 8 labels have zero validation instances — Vault manual mapping is not optional, it's required",
        "3. Chinese text consumes 2.4× more tokens per character than Latin",
        "4. Class imbalance is 73:1 between GIVENNAME and TIME",
        "5. Perfect 80/20 train/val parity on all viable labels"
    ]
    for find in findings:
        add_body(cell_r, find, pt_size=22, bold=True, color_rgb=(0x1F, 0x38, 0x64), space_before=1, space_after=2)

    # -------------------------------------------------------------------------
    # BOTTOM BAND (Full width: 1159 mm, ~50 mm tall)
    # -------------------------------------------------------------------------
    print("Building Bottom Band...")
    # Divider above bottom band
    p_bdiv = doc.add_paragraph()
    p_bdiv.paragraph_format.space_before = Pt(4)
    p_bdiv.paragraph_format.space_after = Pt(4)
    pBdr_b = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="1" w:color="1F3864"/></w:pBdr>')
    p_bdiv._p.get_or_add_pPr().append(pBdr_b)

    bot_table = doc.add_table(rows=1, cols=3)
    bot_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    bot_table.autofit = False
    remove_table_borders(bot_table)

    col_w_bot = Mm(386)
    for i in range(3):
        bot_table.columns[i].width = col_w_bot
        bot_table.rows[0].cells[i].width = col_w_bot
        set_cell_margins(bot_table.rows[0].cells[i], top=40, bottom=40, left=40, right=40)
        bot_table.rows[0].cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    c_bot_l = bot_table.rows[0].cells[0]
    c_bot_c = bot_table.rows[0].cells[1]
    c_bot_r = bot_table.rows[0].cells[2]

    # Left third: Repo QR (40mm) + text
    tbl_qr1 = c_bot_l.add_table(rows=1, cols=2)
    tbl_qr1.autofit = False
    remove_table_borders(tbl_qr1)
    tbl_qr1.columns[0].width = Mm(50)
    tbl_qr1.columns[1].width = Mm(320)
    tbl_qr1.rows[0].cells[0].width = Mm(50)
    tbl_qr1.rows[0].cells[1].width = Mm(320)
    tbl_qr1.rows[0].cells[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    tbl_qr1.rows[0].cells[1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    add_image_safe(tbl_qr1.rows[0].cells[0], os.path.join(ASSETS_DIR, "qr_repo.png"), width_mm=42)
    p_qr1_t = tbl_qr1.rows[0].cells[1].paragraphs[0]
    p_qr1_t.paragraph_format.space_before = Pt(0)
    p_qr1_t.paragraph_format.space_after = Pt(0)
    r1 = p_qr1_t.add_run("Repository:\n")
    r1.font.name = "Calibri Light"
    r1.font.size = Pt(22)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    r2 = p_qr1_t.add_run("github.com/Schnitze1/SWE40006-Group-Project")
    r2.font.name = "Calibri Light"
    r2.font.size = Pt(20)
    r2.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    # Centre third: EDA PDF QR (40mm) + text
    tbl_qr2 = c_bot_c.add_table(rows=1, cols=2)
    tbl_qr2.autofit = False
    remove_table_borders(tbl_qr2)
    tbl_qr2.columns[0].width = Mm(50)
    tbl_qr2.columns[1].width = Mm(320)
    tbl_qr2.rows[0].cells[0].width = Mm(50)
    tbl_qr2.rows[0].cells[1].width = Mm(320)
    tbl_qr2.rows[0].cells[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    tbl_qr2.rows[0].cells[1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    add_image_safe(tbl_qr2.rows[0].cells[0], os.path.join(ASSETS_DIR, "qr_eda.png"), width_mm=42)
    p_qr2_t = tbl_qr2.rows[0].cells[1].paragraphs[0]
    p_qr2_t.paragraph_format.space_before = Pt(0)
    p_qr2_t.paragraph_format.space_after = Pt(0)
    r3 = p_qr2_t.add_run("Full EDA Report:\n")
    r3.font.name = "Calibri Light"
    r3.font.size = Pt(22)
    r3.font.bold = True
    r3.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    r4 = p_qr2_t.add_run("huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m")
    r4.font.name = "Calibri Light"
    r4.font.size = Pt(20)
    r4.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    # Right third: Poco credits
    p_bot_r = c_bot_r.paragraphs[0]
    p_bot_r.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_bot_r.paragraph_format.space_before = Pt(0)
    p_bot_r.paragraph_format.space_after = Pt(2)
    rr1 = p_bot_r.add_run("Poco — Preserve Originals, Conceal Only\n")
    rr1.font.name = "Calibri Light"
    rr1.font.size = Pt(22)
    rr1.font.bold = True
    rr1.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    rr2 = p_bot_r.add_run("SWE40006 | CL01_G01 | October 2026")
    rr2.font.name = "Calibri Light"
    rr2.font.size = Pt(20)
    rr2.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    # Save docx
    print(f"Saving {DOCX_OUT}...")
    doc.save(DOCX_OUT)
    print("Document successfully created!")

if __name__ == "__main__":
    build_poster()
