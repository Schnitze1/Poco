import os
import re

EDA_DIR = r"d:\Repos\Poco\EDA"
ARTIFACT_DIR = r"C:\Users\Shadd\.gemini\antigravity-ide\brain\0f1bd67a-e6ce-4dc6-b535-b908b888cb0b"

# Load EDA_REPORT.md
report_path = os.path.join(EDA_DIR, "EDA_REPORT.md")
with open(report_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Executive Summary annotation count fix
text = text.replace(
    "accounting for 11,886,097 annotations, or 99.989% of the corpus",
    "accounting for 11,885,819 annotations, or 99.99% of the corpus"
)

# 2. Section 6.1 denominator and rounding fix
old_sec61 = "OpenPII 1.5M confirms that **21.9%** of all PII annotations are `GIVENNAME` and `SURNAME` ((1,396,075 + 1,200,212) / 11,885,821 = 21.84%)"
new_sec61 = "OpenPII 1.5M confirms that **~21.8%** of all PII annotations are `GIVENNAME` and `SURNAME` ((1,396,075 + 1,200,212) / 11,887,370 = 21.84%)"
if old_sec61 in text:
    text = text.replace(old_sec61, new_sec61)
else:
    # also handle any variant
    text = re.sub(
        r"OpenPII 1\.5M confirms that \*\*.*?\*\* of all PII annotations are `GIVENNAME` and `SURNAME`.*?\)",
        new_sec61,
        text
    )

# 3. Section 3.4 script table update to include Cyrl and Grek
old_script_table = """| Script Family | Language Group | Corpus Count ($N$) | Mean Tokens/Char | Std Dev | Expansion Factor vs. Latin |
|:---|:---|---:|---:|---:|---:|
| **Hans (Chinese)** | Simplified Han (`zh`) | 26,272 | **0.757** | 0.078 | **2.43x** |
| **Jpan (Japanese)** | Kana / Kanji (`ja`) | 25,902 | **0.693** | 0.105 | **2.22x** |
| **Hang (Korean)** | Hangul (`ko`) | 26,498 | **0.601** | 0.069 | **1.93x** |
| **Latn (Latin)** | English, Malay, Vietnamese, etc. | 1,465,724 | **0.312** | 0.047 | **1.00x Baseline** |"""

new_script_table = """| Script Family | Language Group | Corpus Count ($N$) | Mean Tokens/Char | Std Dev | Expansion Factor vs. Latin |
|:---|:---|---:|---:|---:|---:|
| **Hans (Chinese)** | Simplified Han (`zh`) | 26,272 | **0.757** | 0.078 | **2.43x** |
| **Jpan (Japanese)** | Kana / Kanji (`ja`) | 25,902 | **0.693** | 0.105 | **2.22x** |
| **Hang (Korean)** | Hangul (`ko`) | 26,498 | **0.601** | 0.069 | **1.93x** |
| **Grek (Greek)** | Greek (`el`) | 45,178 | **0.419** | 0.056 | **1.34x** |
| **Cyrl (Cyrillic)** | Bulgarian, Serbian (`bg`, `sr`) | 46,801 | **0.364** | 0.040 | **1.17x** |
| **Latn (Latin)** | English, Malay, Vietnamese, etc. | 1,465,724 | **0.312** | 0.047 | **1.00x Baseline** |

> [!NOTE]
> Cyrillic and Greek scripts (combined $N = 91,979$) exhibit modest subword expansion (1.17x–1.34x) relative to Latin, well below the 1.9x–2.4x expansion ceiling observed in East Asian (CJK) scripts."""

if old_script_table in text:
    text = text.replace(old_script_table, new_script_table)

# 4. Fig 8 caption update
text = text.replace(
    "*Figure 8: Average word span length by PII entity class across the full 1,636,375-example corpus (note: ORGANISATION has N < 1,000 corpus annotations and is included for structural comparison).* ",
    "*Figure 8: Average word span length across the 20 viable PII entity classes (Full Corpus: 1,636,375 Examples).*"
)
text = text.replace(
    "*Figure 8: Average word span length by PII entity class across the full 1,636,375-example corpus (note: ORGANISATION has N < 1,000 corpus annotations and is included for structural comparison).*",
    "*Figure 8: Average word span length across the 20 viable PII entity classes (Full Corpus: 1,636,375 Examples).*"
)

# 5. Fig 20 caption update
text = text.replace(
    "*Figure 20: Train vs. Validation allocation across all 23 non-viable long-tail labels on a symlog scale, visually highlighting 8 zero-in-validation classes and 1 zero-in-training class (`HEIGHT`).*",
    "*Figure 20: Train vs. Validation allocation across all 23 non-viable long-tail labels on a log scale, visually highlighting 8 zero-in-validation classes and 1 zero-in-training class (`HEIGHT`).*"
)

# 6. Ensure ALL image paths are strictly relative ./figX.png
text = re.sub(r'!\[(.*?)\]\([^\)]*?(fig\d+_[a-z0-9_]+\.png)\)', r'![\1](./\2)', text)

# Write updated text back to EDA_REPORT.md
with open(report_path, "w", encoding="utf-8") as f:
    f.write(text)

# Also write IDENTICAL text to eda_openpii_report.md (ensuring relative paths ./figX.png in artifact too!)
artifact_path = os.path.join(ARTIFACT_DIR, "eda_openpii_report.md")
with open(artifact_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Successfully polished both EDA_REPORT.md and eda_openpii_report.md!")
