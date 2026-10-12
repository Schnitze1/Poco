import os
import docx
from docx.shared import Mm, Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

EDA_DIR = r"d:\Repos\Poco\EDA"
ASSETS_DIR = os.path.join(EDA_DIR, "poster_assets")
POSTER_DIR = r"d:\Repos\Poco\Poster"
DOCX_OUT = os.path.join(POSTER_DIR, "POCO_A0_Poster_CL01_G01.docx")

def set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def remove_table_borders(table):
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

def add_heading(cell, text, pt_size=36, space_before=6, space_after=2):
    p = cell.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(text)
    run.font.name = "Calibri Light"
    run.font.size = Pt(pt_size)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    return p

def add_body(cell, text, pt_size=22, space_before=0, space_after=4, color_rgb=(0x26, 0x26, 0x26)):
    p = cell.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.name = "Calibri Light"
    run.font.size = Pt(pt_size)
    run.font.color.rgb = RGBColor(*color_rgb)
    return p

def add_caption(cell, text, pt_size=18, space_before=2, space_after=6):
    p = cell.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(text)
    run.font.name = "Calibri Light"
    run.font.size = Pt(pt_size)
    run.font.italic = True
    run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    return p

def add_image_locked(cell, image_path, width_mm, caption=None):
    if not os.path.exists(image_path):
        p = cell.add_paragraph()
        run = p.add_run(f"MISSING: {os.path.basename(image_path)}")
        run.font.name = "Calibri Light"
        run.font.size = Pt(22)
        run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
        return p

    p = cell.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(image_path, width=Mm(width_mm))
    if caption:
        add_caption(cell, caption)
    return p

def build_docx():
    print(f"Building master grid Word document: {DOCX_OUT}")
    doc = docx.Document()
    sec = doc.sections[0]
    
    # Target Page Setup: 118.9 cm x 84.1 cm Landscape, 1.5 cm margins
    sec.page_width = Mm(1189)
    sec.page_height = Mm(841)
    sec.top_margin = Mm(15)
    sec.bottom_margin = Mm(15)
    sec.left_margin = Mm(15)
    sec.right_margin = Mm(15)

    # Disable hyphenation
    settings = doc.settings._element
    settings.append(parse_xml(f'<w:doNotHyphenate {nsdecls("w")}/>'))

    # Insert Master Table (5 rows x 3 columns)
    master = doc.add_table(rows=5, cols=3)
    master.alignment = WD_TABLE_ALIGNMENT.CENTER
    master.autofit = False
    remove_table_borders(master)

    col1_w = Mm(380)
    col2_w = Mm(380)
    col3_w = Mm(399)
    total_w = Mm(1159)

    for r in master.rows:
        r.cells[0].width = col1_w
        r.cells[1].width = col2_w
        r.cells[2].width = col3_w

    # Merge Row 1 (Title Band)
    r1_cell = master.rows[0].cells[0]
    r1_cell.merge(master.rows[0].cells[1])
    r1_cell.merge(master.rows[0].cells[2])
    r1_cell.width = total_w

    # Merge Row 2 (Key Findings Strip)
    r2_cell = master.rows[1].cells[0]
    r2_cell.merge(master.rows[1].cells[1])
    r2_cell.merge(master.rows[1].cells[2])
    r2_cell.width = total_w

    # Row 3 remains 3 separate columns (Cell A: Left, Cell B: Centre, Cell C: Right)
    cell_a = master.rows[2].cells[0]
    cell_b = master.rows[2].cells[1]
    cell_c = master.rows[2].cells[2]
    cell_a.width = col1_w
    cell_b.width = col2_w
    cell_c.width = col3_w

    # Merge Row 4 (Demo + QR Strip)
    r4_cell = master.rows[3].cells[0]
    r4_cell.merge(master.rows[3].cells[1])
    r4_cell.merge(master.rows[3].cells[2])
    r4_cell.width = total_w

    # Merge Row 5 (Footer Strip)
    r5_cell = master.rows[4].cells[0]
    r5_cell.merge(master.rows[4].cells[1])
    r5_cell.merge(master.rows[4].cells[2])
    r5_cell.width = total_w

    # -------------------------------------------------------------------------
    # ROW 1: TITLE BAND
    # -------------------------------------------------------------------------
    print("Populating Row 1 (Title Band)...")
    set_cell_margins(r1_cell, top=100, bottom=100, left=100, right=100)
    p_t1 = r1_cell.paragraphs[0]
    p_t1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t1.paragraph_format.space_before = Pt(0)
    p_t1.paragraph_format.space_after = Pt(2)
    r = p_t1.add_run("Poco — Preserve Originals, Conceal Only")
    r.font.name = "Calibri Light"
    r.font.size = Pt(72)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    p_t2 = r1_cell.add_paragraph()
    p_t2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_t2.paragraph_format.space_before = Pt(2)
    p_t2.paragraph_format.space_after = Pt(2)
    r = p_t2.add_run("Privacy-first PII anonymisation for LLM workflows, with a fully automated multi-environment DevOps pipeline")
    r.font.name = "Calibri Light"
    r.font.size = Pt(32)
    r.font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    # -------------------------------------------------------------------------
    # ROW 2: KEY FINDINGS STRIP (5 Nested Finding Blocks)
    # -------------------------------------------------------------------------
    print("Populating Row 2 (Key Findings Strip)...")
    set_cell_background(r2_cell, "F2F2F2")
    set_cell_margins(r2_cell, top=100, bottom=100, left=100, right=100)
    
    t_find = r2_cell.add_table(rows=1, cols=5)
    t_find.autofit = False
    remove_table_borders(t_find)
    fw = Mm(230)
    for c_idx in range(5):
        t_find.columns[c_idx].width = fw
        t_find.rows[0].cells[c_idx].width = fw
        set_cell_margins(t_find.rows[0].cells[c_idx], top=60, bottom=60, left=40, right=40)

    findings = [
        ("20 / 43", "PII labels viable for training"),
        ("8", "labels with zero validation instances"),
        ("2.4×", "more tokens per character for Chinese"),
        ("73:1", "class imbalance (GIVENNAME : TIME)"),
        ("99.99%", "of annotations in viable labels")
    ]
    for i, (num, lbl) in enumerate(findings):
        fc = t_find.rows[0].cells[i]
        p_n = fc.paragraphs[0]
        p_n.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_n.paragraph_format.space_before = Pt(0)
        p_n.paragraph_format.space_after = Pt(2)
        r = p_n.add_run(num)
        r.font.name = "Calibri Light"
        r.font.size = Pt(48)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

        p_l = fc.add_paragraph()
        p_l.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_l.paragraph_format.space_before = Pt(0)
        p_l.paragraph_format.space_after = Pt(0)
        r = p_l.add_run(lbl)
        r.font.name = "Calibri Light"
        r.font.size = Pt(18)
        r.font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    # -------------------------------------------------------------------------
    # ROW 3, CELL A: LEFT COLUMN (Poco Product Content)
    # -------------------------------------------------------------------------
    print("Populating Row 3, Cell A (Left Column)...")
    set_cell_margins(cell_a, top=100, bottom=100, left=60, right=140)

    # Block 1 — Problem Statement
    add_heading(cell_a, "The Problem", pt_size=40, space_before=4)
    add_body(cell_a, "Every day, people paste contracts, medical notes, and CVs into ChatGPT. Once they do, names, addresses, and financial details are outside their control. Poco makes that safe.", pt_size=24)

    # Block 2 — How It Works
    add_heading(cell_a, "How Poco Works", pt_size=40, space_before=10)
    add_body(cell_a, "Poco detects personal information, replaces each value with a reversible token like [PERSON_1] or [EMAIL_1], and stores the mapping in an encrypted session vault. The redacted text is sent to any LLM, and the response is restored to its original form when it returns.", pt_size=24)

    # 3-stage flow nested table: 1-row x 5-col
    t_flow = cell_a.add_table(rows=1, cols=5)
    t_flow.autofit = False
    remove_table_borders(t_flow)
    t_flow.columns[0].width = Mm(115)
    t_flow.columns[1].width = Mm(12)
    t_flow.columns[2].width = Mm(115)
    t_flow.columns[3].width = Mm(12)
    t_flow.columns[4].width = Mm(115)
    for c_i, c_w in enumerate([115, 12, 115, 12, 115]):
        t_flow.rows[0].cells[c_i].width = Mm(c_w)
        set_cell_margins(t_flow.rows[0].cells[c_i], top=80, bottom=80, left=40, right=40)

    # Col 1: Paste text
    c1 = t_flow.rows[0].cells[0]
    set_cell_background(c1, "2E75B6")
    p = c1.paragraphs[0]
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Paste text\n")
    r.font.size = Pt(24); r.font.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    r2 = p.add_run("User input document")
    r2.font.size = Pt(16); r2.font.italic = True; r2.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Col 2: Arrow
    p = t_flow.rows[0].cells[1].paragraphs[0]
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("→")
    r.font.size = Pt(32); r.font.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    # Col 3: Tokenise
    c3 = t_flow.rows[0].cells[2]
    set_cell_background(c3, "1F3864")
    p = c3.paragraphs[0]
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Tokenise\n")
    r.font.size = Pt(24); r.font.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    r2 = p.add_run("Reversible vault mapping")
    r2.font.size = Pt(16); r2.font.italic = True; r2.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Col 4: Arrow
    p = t_flow.rows[0].cells[3].paragraphs[0]
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("→")
    r.font.size = Pt(32); r.font.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    # Col 5: Restore response
    c5 = t_flow.rows[0].cells[4]
    set_cell_background(c5, "2E75B6")
    p = c5.paragraphs[0]
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Restore response\n")
    r.font.size = Pt(24); r.font.bold = True; r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    r2 = p.add_run("LLM response restored")
    r2.font.size = Pt(16); r2.font.italic = True; r2.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Block 3 — Architecture
    add_heading(cell_a, "Architecture", pt_size=40, space_before=10)
    add_image_locked(cell_a, os.path.join(ASSETS_DIR, "poco_architecture.png"), width_mm=365,
                     caption="Figure 1. Two-pass hybrid PII detection engine.")

    # Block 4 — DevOps Pipeline (appears ONCE)
    add_heading(cell_a, "DevOps Pipeline", pt_size=40, space_before=10)
    add_body(cell_a, "Every code change flows through GitHub Actions, which builds the Rust backend inside the Cargo Lambda container, runs unit, integration, and browser acceptance tests, and deploys to four isolated AWS environments. Failed tests block promotion.", pt_size=24)

    # 5-stage pipeline nested table: 1-row x 9-col
    t_pipe = cell_a.add_table(rows=1, cols=9)
    t_pipe.autofit = False
    remove_table_borders(t_pipe)
    stages = [
        ("Commit", "GitHub Actions", "1F3864"),
        ("Build", "Cargo Lambda", "2E75B6"),
        ("Test", "Unit & Playwright", "1F3864"),
        ("Deploy", "Dev · Staging · Prod", "2E75B6"),
        ("Monitor", "CloudWatch", "1F3864")
    ]
    sw = Mm(67)
    aw = Mm(7)
    for si, (st_t, st_s, bg) in enumerate(stages):
        cell_idx = si * 2
        t_pipe.columns[cell_idx].width = sw
        c_st = t_pipe.rows[0].cells[cell_idx]
        c_st.width = sw
        set_cell_background(c_st, bg)
        set_cell_margins(c_st, top=60, bottom=60, left=30, right=30)
        p = c_st.paragraphs[0]
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p.add_run(st_t + "\n"); r1.font.size = Pt(17); r1.font.bold = True; r1.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        r2 = p.add_run(st_s); r2.font.size = Pt(11); r2.font.color.rgb = RGBColor(0xEA, 0xEE, 0xF7)

        if si < 4:
            arr_idx = cell_idx + 1
            t_pipe.columns[arr_idx].width = aw
            c_arr = t_pipe.rows[0].cells[arr_idx]
            c_arr.width = aw
            p = c_arr.paragraphs[0]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run("→"); r.font.size = Pt(20); r.font.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    # Block 5 — Demo
    add_heading(cell_a, "Live Demo", pt_size=40, space_before=10)
    
    t_demo = cell_a.add_table(rows=1, cols=2)
    t_demo.autofit = False
    remove_table_borders(t_demo)
    t_demo.columns[0].width = Mm(65)
    t_demo.columns[1].width = Mm(300)
    t_demo.rows[0].cells[0].width = Mm(65)
    t_demo.rows[0].cells[1].width = Mm(300)
    
    c_dqr = t_demo.rows[0].cells[0]
    c_dtx = t_demo.rows[0].cells[1]
    add_image_locked(c_dqr, os.path.join(ASSETS_DIR, "qrcode_demo.png"), width_mm=55)
    p = c_dtx.paragraphs[0]
    p.paragraph_format.space_before = Pt(8)
    r = p.add_run("littlepoco.me\n")
    r.font.size = Pt(28); r.font.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    r2 = p.add_run("Confidential session vault")
    r2.font.size = Pt(20); r2.font.color.rgb = RGBColor(0x2E, 0x75, 0xB6)

    add_image_locked(cell_a, os.path.join(ASSETS_DIR, "poco_screenshot.png"), width_mm=365,
                     caption="Figure 2. Poco encode view with coloured token highlighting.")

    # -------------------------------------------------------------------------
    # ROW 3, CELL B: CENTRE COLUMN (EDA Figures 1–10)
    # -------------------------------------------------------------------------
    print("Populating Row 3, Cell B (Centre Column)...")
    set_cell_margins(cell_b, top=100, bottom=100, left=100, right=100)

    # Sub-heading 1: Dataset Overview
    add_heading(cell_b, "Dataset Overview", pt_size=36, space_before=4)
    add_body(cell_b, "Analysis of 1,636,375 multilingual documents across 30 languages, 11.9 million PII annotations, and 43 discovered PII entity classes.", pt_size=22)

    t_met = cell_b.add_table(rows=2, cols=4)
    t_met.autofit = False
    remove_table_borders(t_met)
    mw = Mm(92)
    metrics = [("1,636,375", "Examples"), ("11,887,370", "Annotations"), ("43", "PII classes"), ("30", "Languages")]
    for mi, (num, lbl) in enumerate(metrics):
        t_met.columns[mi].width = mw
        c_top = t_met.rows[0].cells[mi]
        c_bot = t_met.rows[1].cells[mi]
        c_top.width = mw
        c_bot.width = mw
        set_cell_background(c_top, "F2F2F2")
        set_cell_background(c_bot, "F2F2F2")
        set_cell_margins(c_top, 40, 0, 20, 20)
        set_cell_margins(c_bot, 0, 40, 20, 20)
        
        p = c_top.paragraphs[0]
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(num); r.font.size = Pt(26); r.font.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
        
        p2 = c_bot.paragraphs[0]
        p2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(lbl); r2.font.size = Pt(16); r2.font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    # Sub-heading 2: Label Distribution (Fig 1 & Fig 2 side by side)
    add_heading(cell_b, "Label Distribution", pt_size=36, space_before=8)
    t_s2 = cell_b.add_table(rows=1, cols=2)
    t_s2.autofit = False; remove_table_borders(t_s2)
    hw = Mm(182)
    t_s2.columns[0].width = hw; t_s2.columns[1].width = hw
    t_s2.rows[0].cells[0].width = hw; t_s2.rows[0].cells[1].width = hw
    set_cell_margins(t_s2.rows[0].cells[0], 0, 0, 0, 40)
    set_cell_margins(t_s2.rows[0].cells[1], 0, 0, 40, 0)
    add_image_locked(t_s2.rows[0].cells[0], os.path.join(EDA_DIR, "fig1_label_distribution.png"), width_mm=178,
                     caption="Figure 3. PII entity distribution across top 25 labels, colour-coded by viability tier.")
    add_image_locked(t_s2.rows[0].cells[1], os.path.join(EDA_DIR, "fig2_label_log.png"), width_mm=178,
                     caption="Figure 4. Complete 43-label taxonomy (log scale).")

    # Sub-heading 3: Class Viability
    add_heading(cell_b, "Class Viability", pt_size=36, space_before=8)
    add_body(cell_b, "Only 20 of 43 discovered labels are viable for supervised training. 4 are marginal; 19 are unviable (<100 corpus annotations, down to single occurrences). The unviable labels are handled by deterministic regex in Poco.", pt_size=22)

    # Sub-heading 4: Language Coverage (Fig 3 & Fig 4 side by side)
    add_heading(cell_b, "Language Coverage", pt_size=36, space_before=8)
    t_s4 = cell_b.add_table(rows=1, cols=2)
    t_s4.autofit = False; remove_table_borders(t_s4)
    t_s4.columns[0].width = hw; t_s4.columns[1].width = hw
    t_s4.rows[0].cells[0].width = hw; t_s4.rows[0].cells[1].width = hw
    set_cell_margins(t_s4.rows[0].cells[0], 0, 0, 0, 40)
    set_cell_margins(t_s4.rows[0].cells[1], 0, 0, 40, 0)
    add_image_locked(t_s4.rows[0].cells[0], os.path.join(EDA_DIR, "fig3_languages.png"), width_mm=178,
                     caption="Figure 5. Full-corpus language representation across 30 languages.")
    add_image_locked(t_s4.rows[0].cells[1], os.path.join(EDA_DIR, "fig4_region_lang.png"), width_mm=178,
                     caption="Figure 6. Region × language coverage map.")

    # Sub-heading 5: Document Lengths (Fig 5 & Fig 7 side by side)
    add_heading(cell_b, "Document Lengths", pt_size=36, space_before=8)
    t_s5 = cell_b.add_table(rows=1, cols=2)
    t_s5.autofit = False; remove_table_borders(t_s5)
    t_s5.columns[0].width = hw; t_s5.columns[1].width = hw
    t_s5.rows[0].cells[0].width = hw; t_s5.rows[0].cells[1].width = hw
    set_cell_margins(t_s5.rows[0].cells[0], 0, 0, 0, 40)
    set_cell_margins(t_s5.rows[0].cells[1], 0, 0, 40, 0)
    add_image_locked(t_s5.rows[0].cells[0], os.path.join(EDA_DIR, "fig5_entities_per_example.png"), width_mm=178,
                     caption="Figure 7. PII entities per document distribution.")
    add_image_locked(t_s5.rows[0].cells[1], os.path.join(EDA_DIR, "fig7_token_lengths.png"), width_mm=178,
                     caption="Figure 8. mBERT token length distribution with 512-token ceiling.")

    # Sub-heading 6: Entity Characteristics (Fig 8 & Fig 6 side by side)
    add_heading(cell_b, "Entity Characteristics", pt_size=36, space_before=8)
    t_s6 = cell_b.add_table(rows=1, cols=2)
    t_s6.autofit = False; remove_table_borders(t_s6)
    t_s6.columns[0].width = hw; t_s6.columns[1].width = hw
    t_s6.rows[0].cells[0].width = hw; t_s6.rows[0].cells[1].width = hw
    set_cell_margins(t_s6.rows[0].cells[0], 0, 0, 0, 40)
    set_cell_margins(t_s6.rows[0].cells[1], 0, 0, 40, 0)
    add_image_locked(t_s6.rows[0].cells[0], os.path.join(EDA_DIR, "fig8_span_lengths.png"), width_mm=178,
                     caption="Figure 9. Average word span length by entity class.")
    add_image_locked(t_s6.rows[0].cells[1], os.path.join(EDA_DIR, "fig6_cooccurrence.png"), width_mm=178,
                     caption="Figure 10. Entity co-occurrence matrix (log scale).")

    # -------------------------------------------------------------------------
    # ROW 3, CELL C: RIGHT COLUMN (EDA Figures 11–22)
    # -------------------------------------------------------------------------
    print("Populating Row 3, Cell C (Right Column)...")
    set_cell_margins(cell_c, top=100, bottom=100, left=140, right=60)

    # Sub-heading 7: Per-Language Composition
    add_heading(cell_c, "Per-Language Composition", pt_size=36, space_before=4)
    add_image_locked(cell_c, os.path.join(EDA_DIR, "fig9_language_entity_composition.png"), width_mm=370,
                     caption="Figure 11. Per-language entity composition across 8 Asia-Pacific languages.")
    add_body(cell_c, "Chi-square p < 10⁻³⁰⁰, but Cramér's V = 0.017 shows the effect is negligible — the generator produces uniform proportions.", pt_size=20)

    # Sub-heading 8: Data Quality (4 figures in 2x2 grid)
    add_heading(cell_c, "Data Quality", pt_size=36, space_before=6)
    t_dq = cell_c.add_table(rows=2, cols=2)
    t_dq.autofit = False; remove_table_borders(t_dq)
    rw = Mm(182)
    for row in t_dq.rows:
        row.cells[0].width = rw; row.cells[1].width = rw
        set_cell_margins(row.cells[0], 0, 0, 0, 30)
        set_cell_margins(row.cells[1], 0, 0, 30, 0)
    add_image_locked(t_dq.rows[0].cells[0], os.path.join(EDA_DIR, "fig10_precleaning_boxplots.png"), width_mm=178,
                     caption="Figure 12. Diagnostic boxplots of document lengths.")
    add_image_locked(t_dq.rows[0].cells[1], os.path.join(EDA_DIR, "fig11_precleaning_histograms.png"), width_mm=178,
                     caption="Figure 13. Pre-cleaning distribution histograms.")
    add_image_locked(t_dq.rows[1].cells[0], os.path.join(EDA_DIR, "fig12_cleaned_boxplots.png"), width_mm=178,
                     caption="Figure 14. Winsorised boxplots at P99.")
    add_image_locked(t_dq.rows[1].cells[1], os.path.join(EDA_DIR, "fig13_cleaned_histograms.png"), width_mm=178,
                     caption="Figure 15. Cleaned distribution histograms.")

    # Sub-heading 9: Normalisation Comparison
    add_heading(cell_c, "Normalisation & Correlation", pt_size=36, space_before=6)
    t_nc = cell_c.add_table(rows=1, cols=2)
    t_nc.autofit = False; remove_table_borders(t_nc)
    t_nc.columns[0].width = rw; t_nc.columns[1].width = rw
    t_nc.rows[0].cells[0].width = rw; t_nc.rows[0].cells[1].width = rw
    set_cell_margins(t_nc.rows[0].cells[0], 0, 0, 0, 30)
    set_cell_margins(t_nc.rows[0].cells[1], 0, 0, 30, 0)
    add_image_locked(t_nc.rows[0].cells[0], os.path.join(EDA_DIR, "fig14_normalisation_comparison.png"), width_mm=178,
                     caption="Figure 16. Raw vs MinMax vs Z-score vs Log1p transform.")
    add_image_locked(t_nc.rows[0].cells[1], os.path.join(EDA_DIR, "fig15_correlation_heatmap.png"), width_mm=178,
                     caption="Figure 17. Multivariate Pearson correlation matrix.")

    # Bivariate Pair Plots & Stratified Count
    t_bp = cell_c.add_table(rows=1, cols=2)
    t_bp.autofit = False; remove_table_borders(t_bp)
    t_bp.columns[0].width = rw; t_bp.columns[1].width = rw
    t_bp.rows[0].cells[0].width = rw; t_bp.rows[0].cells[1].width = rw
    set_cell_margins(t_bp.rows[0].cells[0], 0, 0, 0, 30)
    set_cell_margins(t_bp.rows[0].cells[1], 0, 0, 30, 0)
    add_image_locked(t_bp.rows[0].cells[0], os.path.join(EDA_DIR, "fig16_pairplots.png"), width_mm=178,
                     caption="Figure 18. Bivariate pair plot (100k subsample).")
    add_image_locked(t_bp.rows[0].cells[1], os.path.join(EDA_DIR, "fig17_target_vs_predictors_boxplots.png"), width_mm=178,
                     caption="Figure 19. Entity count by token capacity quintile.")

    # Sub-heading 12 & 13: Tokenizer Expansion & Split Parity
    add_heading(cell_c, "Tokenizer Expansion & Split Parity", pt_size=36, space_before=6)
    add_body(cell_c, "Full-corpus census confirmed that all 20 viable classes follow the 80.05% / 19.95% train/val split with |Δ| < 0.08%.", pt_size=22)

    t_sp = cell_c.add_table(rows=1, cols=3)
    t_sp.autofit = False; remove_table_borders(t_sp)
    tw = Mm(122)
    for i in range(3):
        t_sp.columns[i].width = tw
        t_sp.rows[0].cells[i].width = tw
        set_cell_margins(t_sp.rows[0].cells[i], 0, 0, 15, 15)
    add_image_locked(t_sp.rows[0].cells[0], os.path.join(EDA_DIR, "fig18_cjk_token_efficiency.png"), width_mm=118,
                     caption="Figure 20. CJK vs Latin subword expansion (2.4× for Chinese).")
    add_image_locked(t_sp.rows[0].cells[1], os.path.join(EDA_DIR, "fig19_train_val_split_parity.png"), width_mm=118,
                     caption="Figure 21. Train/val split parity across viable labels.")
    add_image_locked(t_sp.rows[0].cells[2], os.path.join(EDA_DIR, "fig20_rare_label_imbalance.png"), width_mm=118,
                     caption="Figure 22. Validation blindness on 23 long-tail labels.")

    # -------------------------------------------------------------------------
    # ROW 4: DEMO / QR STRIP (3-col nested table)
    # -------------------------------------------------------------------------
    print("Populating Row 4 (Demo + QR Strip)...")
    set_cell_background(r4_cell, "F2F2F2")
    set_cell_margins(r4_cell, top=80, bottom=80, left=100, right=100)
    
    t_qrs = r4_cell.add_table(rows=1, cols=3)
    t_qrs.autofit = False; remove_table_borders(t_qrs)
    qw = Mm(380)
    for i in range(3):
        t_qrs.columns[i].width = qw
        t_qrs.rows[0].cells[i].width = qw
        set_cell_margins(t_qrs.rows[0].cells[i], 40, 40, 40, 40)

    # Left: Repository QR
    c_q1 = t_qrs.rows[0].cells[0]
    t_q1_sub = c_q1.add_table(rows=1, cols=2); t_q1_sub.autofit = False; remove_table_borders(t_q1_sub)
    t_q1_sub.columns[0].width = Mm(50); t_q1_sub.columns[1].width = Mm(320)
    add_image_locked(t_q1_sub.rows[0].cells[0], os.path.join(ASSETS_DIR, "qrcode_repo.png"), width_mm=45)
    p = t_q1_sub.rows[0].cells[1].paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    r = p.add_run("Repository\n"); r.font.size = Pt(22); r.font.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    r2 = p.add_run("github.com/Schnitze1/Poco"); r2.font.size = Pt(18); r2.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    # Centre: Live Demo QR
    c_q2 = t_qrs.rows[0].cells[1]
    t_q2_sub = c_q2.add_table(rows=1, cols=2); t_q2_sub.autofit = False; remove_table_borders(t_q2_sub)
    t_q2_sub.columns[0].width = Mm(50); t_q2_sub.columns[1].width = Mm(320)
    add_image_locked(t_q2_sub.rows[0].cells[0], os.path.join(ASSETS_DIR, "qrcode_demo.png"), width_mm=45)
    p = t_q2_sub.rows[0].cells[1].paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    r = p.add_run("Live Demo\n"); r.font.size = Pt(22); r.font.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    r2 = p.add_run("littlepoco.me"); r2.font.size = Pt(18); r2.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    # Right: Full EDA Report QR
    c_q3 = t_qrs.rows[0].cells[2]
    t_q3_sub = c_q3.add_table(rows=1, cols=2); t_q3_sub.autofit = False; remove_table_borders(t_q3_sub)
    t_q3_sub.columns[0].width = Mm(50); t_q3_sub.columns[1].width = Mm(320)
    add_image_locked(t_q3_sub.rows[0].cells[0], os.path.join(ASSETS_DIR, "qrcode_eda.png"), width_mm=45)
    p = t_q3_sub.rows[0].cells[1].paragraphs[0]
    p.paragraph_format.space_before = Pt(4)
    r = p.add_run("Full EDA Report\n"); r.font.size = Pt(22); r.font.bold = True; r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    r2 = p.add_run("Scan for full-corpus analysis"); r2.font.size = Pt(18); r2.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    # -------------------------------------------------------------------------
    # ROW 5: FOOTER STRIP
    # -------------------------------------------------------------------------
    print("Populating Row 5 (Footer Strip)...")
    set_cell_margins(r5_cell, top=60, bottom=60, left=100, right=100)
    p_foot = r5_cell.paragraphs[0]
    p_foot.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_foot.paragraph_format.space_before = Pt(2)
    p_foot.paragraph_format.space_after = Pt(2)
    r = p_foot.add_run("Poco — Preserve Originals, Conceal Only  |  October 2026")
    r.font.name = "Calibri Light"
    r.font.size = Pt(20)
    r.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    print(f"Saving Word document: {DOCX_OUT}...")
    doc.save(DOCX_OUT)
    print("Word document built successfully!")

if __name__ == "__main__":
    build_docx()
