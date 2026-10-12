import os
import sys
import time
import orjson
import requests
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shutil

sns.set_theme(style="whitegrid", font="sans-serif")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

EDA_DIR = r"d:\Repos\Poco\EDA"
ARTIFACT_DIR = r"C:\Users\Shadd\.gemini\antigravity-ide\brain\0f1bd67a-e6ce-4dc6-b535-b908b888cb0b"

VAL_URL = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/validation.jsonl"
TRAIN_URL = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/train.jsonl"

print("="*75, flush=True)
print("STARTING FULL 1.636 MILLION DATASET TRAIN/VALIDATION SPLIT PARITY PIPELINE", flush=True)
print("="*75, flush=True)

train_labels = Counter()
val_labels = Counter()
train_langs = Counter()
val_langs = Counter()
train_scripts = Counter()
val_scripts = Counter()

def process_stream(url, split_name, label_counter, lang_counter, script_counter):
    print(f"\n--- Ingesting {split_name.upper()} split from Hugging Face ---", flush=True)
    t0 = time.time()
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    
    count = 0
    total_annotations = 0
    buffer = b""
    
    for chunk in resp.iter_content(chunk_size=2 * 1024 * 1024): # 2MB buffer chunks
        buffer += chunk
        lines = buffer.split(b"\n")
        buffer = lines.pop()
        
        for line in lines:
            if not line:
                continue
            row = orjson.loads(line)
            count += 1
            
            lang_counter[row.get("language", "unknown")] += 1
            script_counter[row.get("script", "unknown")] += 1
            
            for s in row.get("privacy_mask", []):
                lbl = s.get("label", "UNKNOWN")
                label_counter[lbl] += 1
                total_annotations += 1
                
            if count % 100000 == 0:
                elapsed = time.time() - t0
                rate = count / elapsed
                print(f"[{split_name.upper()}] Processed {count:,} rows | {total_annotations:,} annotations | {elapsed:.1f}s ({rate:.1f} rows/s)", flush=True)

    # Process remaining buffer
    if buffer.strip():
        row = orjson.loads(buffer)
        count += 1
        lang_counter[row.get("language", "unknown")] += 1
        script_counter[row.get("script", "unknown")] += 1
        for s in row.get("privacy_mask", []):
            label_counter[s.get("label", "UNKNOWN")] += 1
            total_annotations += 1

    t1 = time.time()
    print(f"[{split_name.upper()} COMPLETE] Total rows: {count:,} | Total annotations: {total_annotations:,} | Ingest time: {t1 - t0:.2f}s ({count/(t1-t0):.1f} rows/s)", flush=True)
    return count, total_annotations

# 1. Process Validation Split
val_rows, val_ann = process_stream(VAL_URL, "validation", val_labels, val_langs, val_scripts)

# 2. Process Train Split
train_rows, train_ann = process_stream(TRAIN_URL, "train", train_labels, train_langs, train_scripts)

total_rows = train_rows + val_rows
total_annotations = train_ann + val_ann

print("\n" + "="*75, flush=True)
print("STAGE 2: COMPUTING SPLIT PARITY ACROSS ALL LABELS", flush=True)
print("="*75, flush=True)

all_labels = set(train_labels.keys()).union(set(val_labels.keys()))
print(f"Discovered {len(all_labels)} total unique labels across the entire 1.636M corpus!", flush=True)

parity_records = []
ideal_train_pct = (train_rows / total_rows) * 100 # ~80.05%
ideal_val_pct = (val_rows / total_rows) * 100   # ~19.95%

for lbl in sorted(all_labels):
    t_cnt = train_labels[lbl]
    v_cnt = val_labels[lbl]
    tot = t_cnt + v_cnt
    
    t_pct = (t_cnt / tot) * 100 if tot > 0 else 0.0
    v_pct = (v_cnt / tot) * 100 if tot > 0 else 0.0
    
    # Parity assessment
    if v_cnt == 0:
        status = "ZERO in Validation (Test Blindness)"
        parity_tier = "Severe Leakage / Single-Split"
    elif t_cnt == 0:
        status = "ZERO in Training (Zero-Shot Only)"
        parity_tier = "Severe Leakage / Single-Split"
    elif 78.0 <= t_pct <= 82.0:
        status = "Exact Parity (~80/20 Confirmed)"
        parity_tier = "Parity Confirmed"
    elif 70.0 <= t_pct <= 90.0:
        status = "Moderate Variance (Acceptable)"
        parity_tier = "Moderate Drift"
    else:
        status = f"Severe Imbalance ({t_pct:.1f}% Train / {v_pct:.1f}% Val)"
        parity_tier = "Severe Drift"
        
    parity_records.append({
        "Label": lbl,
        "Train_Count": t_cnt,
        "Val_Count": v_cnt,
        "Total_Corpus_Count": tot,
        "Train_Pct": t_pct,
        "Val_Pct": v_pct,
        "Train_Expected_Diff": t_pct - ideal_train_pct,
        "Parity_Status": status,
        "Parity_Tier": parity_tier
    })

parity_df = pd.DataFrame(parity_records).sort_values("Total_Corpus_Count", ascending=False)
parity_df.to_csv(os.path.join(EDA_DIR, "full_1_5m_split_parity.csv"), index=False)
print(parity_df.to_string(), flush=True)

# 3. Generate Fig 19: Train vs. Validation Split Parity
top_20_df = parity_df.head(20).copy()
fig, ax = plt.subplots(figsize=(14, 8))
y_positions = np.arange(len(top_20_df))

ax.barh(y_positions - 0.2, top_20_df["Train_Pct"], height=0.4, label=f"Train Split % (Ideal: {ideal_train_pct:.2f}%)", color="#1976d2", edgecolor="#0d47a1")
ax.barh(y_positions + 0.2, top_20_df["Val_Pct"], height=0.4, label=f"Validation Split % (Ideal: {ideal_val_pct:.2f}%)", color="#ff8f00", edgecolor="#e65100")

ax.axvline(ideal_train_pct, color="#1565c0", linestyle="--", linewidth=1.5, label=f"80.05% Train Benchmark")
ax.axvline(ideal_val_pct, color="#ef6c00", linestyle=":", linewidth=1.5, label=f"19.95% Val Benchmark")

ax.set_yticks(y_positions)
ax.set_yticklabels(top_20_df["Label"], fontsize=11)
ax.invert_yaxis()
ax.set_xlabel("Percentage Allocation (%)", fontsize=12)
ax.set_title("Fig 19: Train vs. Validation Split Parity Across Top 20 Viable Labels (Full 1.636M Corpus)", fontsize=14, fontweight="bold", pad=14)
ax.legend(loc="lower right", fontsize=11)

for i, row in top_20_df.reset_index().iterrows():
    ax.annotate(f"{row['Train_Pct']:.1f}%", (row['Train_Pct'] + 0.8, i - 0.2), va='center', fontsize=9, fontweight='bold', color="#1976d2")
    ax.annotate(f"{row['Val_Pct']:.1f}%", (row['Val_Pct'] + 0.8, i + 0.2), va='center', fontsize=9, fontweight='bold', color="#ff8f00")

plt.xlim(0, 100)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig19_train_val_split_parity.png"))
plt.close()
print("Saved fig19_train_val_split_parity.png", flush=True)

# Copy to artifact
shutil.copy2(os.path.join(EDA_DIR, "fig19_train_val_split_parity.png"), os.path.join(ARTIFACT_DIR, "fig19_train_val_split_parity.png"))

# Save summary json
summary_out = {
    "train_rows": train_rows,
    "val_rows": val_rows,
    "total_rows": total_rows,
    "train_annotations": train_ann,
    "val_annotations": val_ann,
    "total_annotations": total_annotations,
    "ideal_train_pct": ideal_train_pct,
    "ideal_val_pct": ideal_val_pct,
    "total_labels": len(all_labels),
    "parity_summary": parity_df.to_dict(orient="records")
}
import json
with open(os.path.join(EDA_DIR, "full_1_5m_split_parity.json"), "w", encoding="utf-8") as f:
    json.dump(summary_out, f, indent=2)

print("="*75, flush=True)
print("SUCCESSFULLY COMPLETED FULL CORPUS PARITY AUDIT!", flush=True)
print("="*75, flush=True)
