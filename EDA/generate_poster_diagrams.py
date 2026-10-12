import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image

ASSETS_DIR = r"d:\Repos\Poco\EDA\poster_assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. FLOW DIAGRAM: [ Paste text ] → [ Tokenise ] → [ Restore response ]
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 2.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 2.5)
ax.axis("off")

steps = ["Paste text", "Tokenise", "Restore response"]
subtitles = ["User input document", "Reversible vault mapping", "LLM response restored"]
colors = ["#2E75B6", "#1F3864", "#2E75B6"]

box_w = 2.6
box_h = 1.6
gap = 0.8
start_x = 0.4

for i, (step, sub, col) in enumerate(zip(steps, subtitles, colors)):
    bx = start_x + i * (box_w + gap)
    by = 0.45
    rect = patches.FancyBboxPatch(
        (bx, by), box_w, box_h,
        boxstyle="round,pad=0.1,rounding_size=0.2",
        ec="#1F3864", fc=col, lw=2
    )
    ax.add_patch(rect)
    ax.text(bx + box_w/2, by + box_h*0.62, step, ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    ax.text(bx + box_w/2, by + box_h*0.28, sub, ha="center", va="center", color="#D9E1F2", fontsize=10, style="italic")

    if i < 2:
        arr_x = bx + box_w + 0.15
        arr_y = by + box_h/2
        ax.annotate(
            "", xy=(arr_x + 0.5, arr_y), xytext=(arr_x, arr_y),
            arrowprops=dict(arrowstyle="-|>", color="#1F3864", lw=3.5, mutation_scale=20)
        )

plt.tight_layout()
flow_path = os.path.join(ASSETS_DIR, "flow_diagram.png")
plt.savefig(flow_path, bbox_inches="tight", transparent=False, facecolor="white")
plt.close()
print("Saved flow_diagram.png")

# ---------------------------------------------------------------------------
# 2. POCO ARCHITECTURE: Two-pass hybrid PII detection engine
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)
ax.set_xlim(0, 9)
ax.set_ylim(0, 6.5)
ax.axis("off")

layers = [
    ("Input Document", "Raw text from user / prompt payload", "#2E75B6", "#FFFFFF"),
    ("Pass 1: Regex Engine (gaze-pii)", "Deterministic detection: Emails, phones, cards, IPs, IBAN", "#1F3864", "#FFFFFF"),
    ("Pass 2: NER Model (ONNX / ort)", "Contextual extraction: Names, addresses, locations (τ ≥ 0.85)", "#1F3864", "#FFFFFF"),
    ("Conflict Resolution & Session Vault", "Priority override + AES-GCM Encrypted Token Map", "#ED7D31", "#FFFFFF"),
    ("Vault::encode() → [Name_1], etc.", "Reversible redacted stream sent to LLM", "#2E75B6", "#FFFFFF")
]

bw = 7.0
bh = 0.82
bx = 1.0

for i, (title, desc, bg, fg) in enumerate(layers):
    by = 5.2 - i * 1.15
    rect = patches.FancyBboxPatch(
        (bx, by), bw, bh,
        boxstyle="round,pad=0.08,rounding_size=0.15",
        ec="#1F3864", fc=bg, lw=1.8
    )
    ax.add_patch(rect)
    ax.text(bx + bw/2, by + bh*0.62, title, ha="center", va="center", color=fg, fontsize=13, fontweight="bold")
    ax.text(bx + bw/2, by + bh*0.25, desc, ha="center", va="center", color="#F2F2F2", fontsize=10)

    if i < len(layers) - 1:
        ay = by
        ax.annotate(
            "", xy=(bx + bw/2, ay - 0.3), xytext=(bx + bw/2, ay),
            arrowprops=dict(arrowstyle="-|>", color="#1F3864", lw=2.5, mutation_scale=15)
        )

plt.tight_layout()
arch_path = os.path.join(ASSETS_DIR, "poco_architecture.png")
plt.savefig(arch_path, bbox_inches="tight", transparent=False, facecolor="white")
plt.close()
print("Saved poco_architecture.png")

# ---------------------------------------------------------------------------
# 3. DEVOPS PIPELINE: [ Commit ] → [ Build ] → [ Test ] → [ Deploy ] → [ Monitor ]
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 2.2), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 2.2)
ax.axis("off")

stages = ["Commit", "Build", "Test", "Deploy", "Monitor"]
subs = ["GitHub Actions", "Cargo Lambda", "Unit & Playwright", "Dev / Stg / Prod", "CloudWatch"]
colors = ["#1F3864", "#2E75B6", "#1F3864", "#2E75B6", "#1F3864"]

sw = 1.55
sh = 1.4
sgap = 0.4
sx = 0.2

for i, (stage, sub, col) in enumerate(zip(stages, subs, colors)):
    bx = sx + i * (sw + sgap)
    by = 0.4
    rect = patches.FancyBboxPatch(
        (bx, by), sw, sh,
        boxstyle="round,pad=0.08,rounding_size=0.18",
        ec="#1F3864", fc=col, lw=2
    )
    ax.add_patch(rect)
    ax.text(bx + sw/2, by + sh*0.62, stage, ha="center", va="center", color="white", fontsize=13, fontweight="bold")
    ax.text(bx + sw/2, by + sh*0.26, sub, ha="center", va="center", color="#D9E1F2", fontsize=8.5)

    if i < len(stages) - 1:
        ax.annotate(
            "", xy=(bx + sw + 0.3, by + sh/2), xytext=(bx + sw + 0.05, by + sh/2),
            arrowprops=dict(arrowstyle="-|>", color="#ED7D31", lw=3.0, mutation_scale=16)
        )

plt.tight_layout()
pipe_path = os.path.join(ASSETS_DIR, "devops_pipeline.png")
plt.savefig(pipe_path, bbox_inches="tight", transparent=False, facecolor="white")
plt.close()
print("Saved devops_pipeline.png")

# ---------------------------------------------------------------------------
# 4. POCO ENCODE VIEW UI MOCKUP: UI view with coloured token highlighting
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.5)
ax.axis("off")

# Window Chrome
win = patches.FancyBboxPatch((0.2, 0.2), 9.6, 6.1, boxstyle="round,pad=0.1,rounding_size=0.2", ec="#B0BEC5", fc="#F8F9FA", lw=1.5)
ax.add_patch(win)

# Title Bar
tbar = patches.Rectangle((0.2, 5.7), 9.6, 0.6, fc="#1F3864", ec="none")
ax.add_patch(tbar)
for i, c in enumerate(["#FF5F56", "#FFBD2E", "#27C93F"]):
    ax.add_patch(patches.Circle((0.55 + i*0.25, 6.0), 0.08, fc=c, ec="none"))
ax.text(5.0, 6.0, "Poco Web Application — Confidential Session Vault (littlepoco.me)", ha="center", va="center", color="white", fontsize=11, fontweight="bold")

# Left Pane: Input Text
lp = patches.FancyBboxPatch((0.5, 2.4), 4.3, 3.0, boxstyle="round,pad=0.05,rounding_size=0.1", ec="#CFD8DC", fc="white", lw=1)
ax.add_patch(lp)
ax.text(0.7, 5.15, "INPUT TEXT (CLIENT-SIDE):", color="#1F3864", fontsize=10, fontweight="bold")

input_sample = """Doctor Alice Wong reviewed patient John Doe
(DOB: 1985-04-12) at Royal Melbourne Hospital.
Contact email: alice.wong@rmh.org.au
Telephone: +61 412 345 678
Prescribed medication for chronic allergies."""
ax.text(0.7, 4.0, input_sample, color="#37474F", fontsize=9.5, va="center", linespacing=1.4)

# Right Pane: Tokenised Output
rp = patches.FancyBboxPatch((5.2, 2.4), 4.3, 3.0, boxstyle="round,pad=0.05,rounding_size=0.1", ec="#CFD8DC", fc="white", lw=1)
ax.add_patch(rp)
ax.text(5.4, 5.15, "REVERSIBLE REDACTED TEXT (SENT TO LLM):", color="#2E75B6", fontsize=10, fontweight="bold")

output_sample = """Doctor [GIVENNAME_1] [SURNAME_1] reviewed patient
[GIVENNAME_2] [SURNAME_2] (DOB: [DATE_1]) at
[ORGANISATION_1].
Contact email: [EMAIL_1]
Telephone: [TELEPHONENUM_1]
Prescribed medication for chronic allergies."""
ax.text(5.4, 4.0, output_sample, color="#263238", fontsize=9.5, va="center", linespacing=1.4)

# Bottom Pane: In-Memory Session Vault Table
vp = patches.FancyBboxPatch((0.5, 0.4), 9.0, 1.8, boxstyle="round,pad=0.05,rounding_size=0.1", ec="#90CAF9", fc="#E3F2FD", lw=1)
ax.add_patch(vp)
ax.text(0.7, 1.95, "SESSION VAULT MAPPING (IN-MEMORY AES-GCM ENCRYPTED):", color="#1565C0", fontsize=9.5, fontweight="bold")

headers = ["Token Identifier", "Original Entity Value", "Detection Pass", "Confidence"]
cols_x = [0.8, 3.2, 5.8, 8.0]
for h, x in zip(headers, cols_x):
    ax.text(x, 1.68, h, color="#0D47A1", fontsize=8.5, fontweight="bold")

rows = [
    ("[GIVENNAME_1]", "Alice", "Pass 2: NER (ONNX)", "0.984"),
    ("[SURNAME_1]", "Wong", "Pass 2: NER (ONNX)", "0.991"),
    ("[EMAIL_1]", "alice.wong@rmh.org.au", "Pass 1: Regex (gaze-pii)", "1.000"),
    ("[TELEPHONENUM_1]", "+61 412 345 678", "Pass 1: Regex (gaze-pii)", "1.000"),
]

for r_idx, row in enumerate(rows):
    ry = 1.4 - r_idx * 0.25
    for val, x in zip(row, cols_x):
        ax.text(x, ry, val, color="#263238", fontsize=8)

plt.tight_layout()
ui_path = os.path.join(ASSETS_DIR, "poco_encode_view.png")
plt.savefig(ui_path, bbox_inches="tight", transparent=False, facecolor="white")
plt.close()
print("Saved poco_encode_view.png")

print("All poster diagrams successfully generated!")
