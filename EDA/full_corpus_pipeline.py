import os
import sys
import time
import json
import shutil
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
import orjson
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler

# Set aesthetics
sns.set_theme(style="whitegrid", font="sans-serif")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

EDA_DIR = r"d:\Repos\Poco\EDA"
ARTIFACT_DIR = r"C:\Users\Shadd\.gemini\antigravity-ide\brain\0f1bd67a-e6ce-4dc6-b535-b908b888cb0b"
CACHE_PARQUET = os.path.join(EDA_DIR, "cache.parquet")
STATS_JSON = os.path.join(EDA_DIR, "full_corpus_stats.json")

VAL_URL = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/validation.jsonl"
TRAIN_URL = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/train.jsonl"

print("="*80, flush=True)
print("POCO EDA: FULL 1.636 MILLION CORPUS STREAMING & CACHING PIPELINE", flush=True)
print("="*80, flush=True)

# ---------------------------------------------------------------------------
# STAGE 1: STREAM & CACHE TO PARQUET (IF NOT ALREADY CACHED)
# ---------------------------------------------------------------------------

co_matrix = defaultdict(Counter)
span_word_sums = Counter()
span_word_counts = Counter()
lang_entity_counter = defaultdict(Counter)

core_labels = [
    "DATE", "GIVENNAME", "SURNAME", "EMAIL", "CITY", "TITLE",
    "TELEPHONENUM", "AGE", "STREET", "BUILDINGNUM", "ZIPCODE",
    "IDCARDNUM", "CREDITCARDNUMBER", "DRIVERLICENSENUM", "GENDER",
    "TAXNUM", "SEX", "SOCIALNUM", "PASSPORTNUM", "TIME"
]

parquet_schema = pa.schema([
    ("char_length", pa.int32()),
    ("word_count", pa.int32()),
    ("token_count", pa.int32()),
    ("entity_count", pa.int32()),
    ("pii_token_count", pa.int32()),
    ("pii_token_ratio", pa.float32()),
    ("pii_char_length", pa.int32()),
    ("pii_char_ratio", pa.float32()),
    ("avg_entity_char_len", pa.float32()),
    ("max_entity_char_len", pa.float32()),
    ("unique_entity_types", pa.int32()),
    ("tokens_per_char", pa.float32()),
    ("chars_per_word", pa.float32()),
    ("has_pii", pa.int8()),
    ("language", pa.string()),
    ("region", pa.string()),
    ("script", pa.string()),
    ("split", pa.string()),
])

if not os.path.exists(CACHE_PARQUET):
    print("\nNo cached parquet found. Initiating full corpus stream from Hugging Face...", flush=True)
    t_start = time.time()
    
    writer = pq.ParquetWriter(CACHE_PARQUET, parquet_schema, compression="snappy")
    
    total_processed = 0
    total_annotations = 0
    
    def stream_split(url, split_name):
        global total_processed, total_annotations
        print(f"\n>>> Ingesting {split_name.upper()} split from Hugging Face <<<", flush=True)
        t0 = time.time()
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        
        batch = []
        batch_size = 50000
        count = 0
        buffer = b""
        
        for chunk in resp.iter_content(chunk_size=2 * 1024 * 1024):
            buffer += chunk
            lines = buffer.split(b"\n")
            buffer = lines.pop()
            
            for line in lines:
                if not line:
                    continue
                row = orjson.loads(line)
                count += 1
                total_processed += 1
                
                src = row.get("source_text", "")
                pm = row.get("privacy_mask", [])
                tokens = row.get("mbert_tokens", [])
                classes = row.get("mbert_token_classes", [])
                lang = row.get("language", "unknown")
                region = row.get("region", "unknown")
                script = row.get("script", "unknown")
                
                clen = len(src)
                words = src.split()
                wcnt = len(words)
                tcnt = len(tokens)
                ecnt = len(pm)
                
                pii_tok_cnt = sum(1 for c in classes if c != "O")
                pii_tok_rat = (pii_tok_cnt / tcnt) if tcnt > 0 else 0.0
                
                pii_clen = 0
                max_ec_len = 0
                ent_labels = set()
                
                for s in pm:
                    lbl = s.get("label", "UNKNOWN")
                    val = s.get("value", "")
                    val_len = len(val)
                    pii_clen += val_len
                    if val_len > max_ec_len:
                        max_ec_len = val_len
                    ent_labels.add(lbl)
                    total_annotations += 1
                    
                    # Accumulate span length
                    sw_cnt = len(val.split())
                    span_word_sums[lbl] += sw_cnt
                    span_word_counts[lbl] += 1
                    lang_entity_counter[lang][lbl] += 1
                    
                # Co-occurrence
                ent_list = sorted(list(ent_labels))
                for i in range(len(ent_list)):
                    l1 = ent_list[i]
                    for j in range(i, len(ent_list)):
                        l2 = ent_list[j]
                        co_matrix[l1][l2] += 1
                        if l1 != l2:
                            co_matrix[l2][l1] += 1
                            
                pii_c_rat = (pii_clen / clen) if clen > 0 else 0.0
                avg_ec_len = (pii_clen / ecnt) if ecnt > 0 else 0.0
                tok_per_c = (tcnt / clen) if clen > 0 else 0.0
                c_per_w = (clen / wcnt) if wcnt > 0 else 0.0
                has_pii = 1 if ecnt > 0 else 0
                
                batch.append({
                    "char_length": clen,
                    "word_count": wcnt,
                    "token_count": tcnt,
                    "entity_count": ecnt,
                    "pii_token_count": pii_tok_cnt,
                    "pii_token_ratio": pii_tok_rat,
                    "pii_char_length": pii_clen,
                    "pii_char_ratio": pii_c_rat,
                    "avg_entity_char_len": avg_ec_len,
                    "max_entity_char_len": max_ec_len,
                    "unique_entity_types": len(ent_labels),
                    "tokens_per_char": tok_per_c,
                    "chars_per_word": c_per_w,
                    "has_pii": has_pii,
                    "language": lang,
                    "region": region,
                    "script": script,
                    "split": split_name
                })
                
                if len(batch) >= batch_size:
                    batch_df = pd.DataFrame(batch)
                    tbl = pa.Table.from_pandas(batch_df, schema=parquet_schema)
                    writer.write_table(tbl)
                    batch = []
                    
                if count % 100000 == 0:
                    el = time.time() - t0
                    print(f"[{split_name.upper()}] Processed {count:,} rows | {el:.1f}s ({count/el:.1f} rows/s)", flush=True)

        if buffer.strip():
            row = orjson.loads(buffer)
            count += 1
            total_processed += 1
            src = row.get("source_text", "")
            pm = row.get("privacy_mask", [])
            tokens = row.get("mbert_tokens", [])
            classes = row.get("mbert_token_classes", [])
            lang = row.get("language", "unknown")
            region = row.get("region", "unknown")
            script = row.get("script", "unknown")
            clen = len(src)
            words = src.split()
            wcnt = len(words)
            tcnt = len(tokens)
            ecnt = len(pm)
            pii_tok_cnt = sum(1 for c in classes if c != "O")
            pii_tok_rat = (pii_tok_cnt / tcnt) if tcnt > 0 else 0.0
            pii_clen = 0
            max_ec_len = 0
            ent_labels = set()
            for s in pm:
                lbl = s.get("label", "UNKNOWN")
                val = s.get("value", "")
                val_len = len(val)
                pii_clen += val_len
                if val_len > max_ec_len:
                    max_ec_len = val_len
                ent_labels.add(lbl)
                total_annotations += 1
                sw_cnt = len(val.split())
                span_word_sums[lbl] += sw_cnt
                span_word_counts[lbl] += 1
                lang_entity_counter[lang][lbl] += 1
            ent_list = sorted(list(ent_labels))
            for i in range(len(ent_list)):
                l1 = ent_list[i]
                for j in range(i, len(ent_list)):
                    l2 = ent_list[j]
                    co_matrix[l1][l2] += 1
                    if l1 != l2:
                        co_matrix[l2][l1] += 1
            pii_c_rat = (pii_clen / clen) if clen > 0 else 0.0
            avg_ec_len = (pii_clen / ecnt) if ecnt > 0 else 0.0
            tok_per_c = (tcnt / clen) if clen > 0 else 0.0
            c_per_w = (clen / wcnt) if wcnt > 0 else 0.0
            has_pii = 1 if ecnt > 0 else 0
            batch.append({
                "char_length": clen,
                "word_count": wcnt,
                "token_count": tcnt,
                "entity_count": ecnt,
                "pii_token_count": pii_tok_cnt,
                "pii_token_ratio": pii_tok_rat,
                "pii_char_length": pii_clen,
                "pii_char_ratio": pii_c_rat,
                "avg_entity_char_len": avg_ec_len,
                "max_entity_char_len": max_ec_len,
                "unique_entity_types": len(ent_labels),
                "tokens_per_char": tok_per_c,
                "chars_per_word": c_per_w,
                "has_pii": has_pii,
                "language": lang,
                "region": region,
                "script": script,
                "split": split_name
            })
            
        if batch:
            batch_df = pd.DataFrame(batch)
            tbl = pa.Table.from_pandas(batch_df, schema=parquet_schema)
            writer.write_table(tbl)
            
        el = time.time() - t0
        print(f"[{split_name.upper()} FINISHED] Total: {count:,} rows in {el:.1f}s ({count/el:.1f} rows/s)", flush=True)

    stream_split(VAL_URL, "validation")
    stream_split(TRAIN_URL, "train")
    writer.close()
    
    total_time = time.time() - t_start
    print(f"\n[CACHE COMPLETE] Ingested all {total_processed:,} rows and {total_annotations:,} annotations in {total_time:.1f}s (~{total_time/60:.1f} mins)!", flush=True)
    
    # Save accumulators
    with open(os.path.join(EDA_DIR, "co_matrix_full.json"), "w") as f:
        json.dump({k: dict(v) for k, v in co_matrix.items()}, f)
    with open(os.path.join(EDA_DIR, "span_lengths_full.json"), "w") as f:
        json.dump({k: span_word_sums[k] / span_word_counts[k] for k in span_word_counts}, f)
    with open(os.path.join(EDA_DIR, "lang_entity_full.json"), "w") as f:
        json.dump({k: dict(v) for k, v in lang_entity_counter.items()}, f)
else:
    print(f"Found existing cache at {CACHE_PARQUET}! Loading directly...", flush=True)

# ---------------------------------------------------------------------------
# STAGE 2: LOAD PARQUET & COMPUTE STATS
# ---------------------------------------------------------------------------

print("\nReading cache.parquet with pyarrow...", flush=True)
t0 = time.time()
df = pd.read_parquet(CACHE_PARQUET, dtype_backend="pyarrow")
print(f"Loaded {len(df):,} rows in {time.time() - t0:.2f}s!", flush=True)

# Load accumulators if existing
co_matrix_path = os.path.join(EDA_DIR, "co_matrix_full.json")
if os.path.exists(co_matrix_path):
    with open(co_matrix_path) as f:
        co_matrix_data = json.load(f)
else:
    co_matrix_data = None

span_path = os.path.join(EDA_DIR, "span_lengths_full.json")
if os.path.exists(span_path):
    with open(span_path) as f:
        span_data = json.load(f)
else:
    span_data = None

lang_path = os.path.join(EDA_DIR, "lang_entity_full.json")
if os.path.exists(lang_path):
    with open(lang_path) as f:
        lang_data = json.load(f)
else:
    lang_data = None

# Load split parity census
parity_df = pd.read_csv(os.path.join(EDA_DIR, "full_1_5m_split_parity.csv"))

# Build 43-label viability table
viability_rows = []
for idx, r in parity_df.iterrows():
    lbl = r["Label"]
    tot = int(r["Total_Corpus_Count"])
    pct = (tot / 11885821) * 100
    if tot >= 19000:
        tier = "Tier 1: Fully Trainable"
        status = "Trainable (Supervised NER)"
        action = "Core Target Vocabulary"
    elif tot >= 200:
        tier = "Tier 2: Marginal / Long-Tail"
        status = "Marginal (Super-class or Oversample)"
        action = "Group into Super-Class or Drop"
    else:
        tier = "Tier 3: Unviable (<100 in Corpus)"
        status = "Untrainable (<100 in Full Corpus)"
        action = "Drop from Neural Head; Regex in Poco"
    viability_rows.append({
        "Label": lbl,
        "Full_Corpus_Count": tot,
        "Percentage": pct,
        "Viability_Tier": tier,
        "Training_Status": status,
        "Action_Recommendation": action
    })

viability_df = pd.DataFrame(viability_rows).sort_values("Full_Corpus_Count", ascending=False)
viability_df.to_csv(os.path.join(EDA_DIR, "label_viability_table.csv"), index=False)

tier_palette = {
    "Tier 1: Fully Trainable": "#2e7d32",            # Forest Green
    "Tier 2: Marginal / Long-Tail": "#f57c00",        # Amber / Orange
    "Tier 3: Unviable (<100 in Corpus)": "#c62828"   # Crimson Red
}

# ---------------------------------------------------------------------------
# STAGE 3: GENERATE ALL 20 FIGURES FROM FULL CORPUS
# ---------------------------------------------------------------------------

print("\n--- Generating Fig 1 & Fig 2 (Taxonomy & 3-Tier Viability) ---", flush=True)

# Fig 1: Top 25
plt.figure(figsize=(12, 10))
top25 = viability_df.head(25)
ax = sns.barplot(
    data=top25,
    x="Full_Corpus_Count",
    y="Label",
    hue="Viability_Tier",
    dodge=False,
    palette=tier_palette
)
plt.title(f"Fig 1: PII Entity Distribution (Full Corpus: 1,636,375 Examples — Top 25 Labels by 3-Tier Viability)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Annotation Count in Full 1.636M Corpus (Linear Scale)", fontsize=11)
plt.ylabel("PII Label", fontsize=11)
plt.legend(title="Training Viability Tier", loc="lower right", fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig1_label_distribution.png"))
plt.close()
print("Saved Fig 1", flush=True)

# Fig 2: All 43 Labels on Log scale
plt.figure(figsize=(12, 11))
ax = sns.barplot(
    data=viability_df,
    x="Full_Corpus_Count",
    y="Label",
    hue="Viability_Tier",
    dodge=False,
    palette=tier_palette
)
ax.set_xscale("log")
plt.axvline(19000, color="#2e7d32", linestyle="--", linewidth=1.8, label="Trainable Threshold (≥19,000 Annotations)")
plt.axvline(200, color="#c62828", linestyle=":", linewidth=1.8, label="Unviable Threshold (<100 Annotations)")
plt.title("Fig 2: Complete PII Entity Taxonomy — All 43 Labels (Log Scale)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Annotation Count in Full 1.636M Corpus (Log Scale)", fontsize=11)
plt.ylabel("PII Label (All 43 Discovered Classes)", fontsize=10)
plt.legend(loc="lower left", fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig2_label_log.png"))
plt.close()
print("Saved Fig 2", flush=True)

# Fig 3: Language representation from full corpus
print("\n--- Generating Fig 3 & Fig 4 (Languages & Regions) ---", flush=True)
lang_counts = df["language"].value_counts()
plt.figure(figsize=(11, 6))
ax = lang_counts.plot(kind="barh", color="#2b5c8f", edgecolor="#1a3654")
plt.title("Fig 3: Language Representation Across Asia-Pacific Extension (Full Corpus: 1,636,375 Examples)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Total Document Count", fontsize=11)
plt.ylabel("ISO 639-1 Language Code", fontsize=11)
ax.invert_yaxis()
for p in ax.patches:
    width = p.get_width()
    ax.annotate(f"{int(width):,} ({width/len(df)*100:.1f}%)", (width + 5000, p.get_y() + p.get_height() / 2.),
                va='center', fontsize=10, color="#222222")
plt.xlim(0, max(lang_counts) * 1.22)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig3_languages.png"))
plt.close()
print("Saved Fig 3", flush=True)

# Fig 4: Region x Language coverage from full corpus
pivot = df.groupby(["region", "language"]).size().unstack(fill_value=0)
plt.figure(figsize=(12, 7))
sns.heatmap(pivot, cmap="YlGnBu", annot=True, fmt="d", cbar_kws={'label': 'Document Count'}, linewidths=0.5)
plt.title("Fig 4: Cross-Tabulation Coverage Map: Region × Language (Full Corpus: 1,636,375 Examples)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("ISO 639-1 Language Code", fontsize=11)
plt.ylabel("ISO 3166-1 Region Code", fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig4_region_lang.png"))
plt.close()
print("Saved Fig 4", flush=True)

# Fig 5: Entities per Document Distribution
print("\n--- Generating Fig 5 (Entities per Document) ---", flush=True)
plt.figure(figsize=(10, 5))
# Use full corpus for histogram bins, 500k for KDE
sub_500k = df["entity_count"].sample(500000, random_state=42)
ax = sns.histplot(df["entity_count"], bins=25, color="#2e7d32", discrete=True, stat="count")
sns.kdeplot(sub_500k, color="#1565c0", ax=ax.twinx(), warn_singular=False)
median_ent = df["entity_count"].median()
mean_ent = df["entity_count"].mean()
ax.axvline(median_ent, color="red", linestyle="--", linewidth=1.8, label=f"Median = {median_ent:.1f}")
ax.axvline(mean_ent, color="blue", linestyle=":", linewidth=1.8, label=f"Mean = {mean_ent:.2f}")
plt.title("Fig 5: Distribution of PII Entities per Document (Full Corpus: 1,636,375 Examples)", fontsize=13, fontweight="bold", pad=12)
ax.set_xlabel("Number of PII Entities in Document", fontsize=11)
ax.set_ylabel("Document Count", fontsize=11)
ax.legend(fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig5_entities_per_example.png"))
plt.close()
print("Saved Fig 5", flush=True)

# Fig 6: Co-occurrence Matrix (Log-scaled)
print("\n--- Generating Fig 6 (Co-occurrence Matrix) ---", flush=True)
if co_matrix_data:
    co_df = pd.DataFrame(0, index=core_labels, columns=core_labels)
    for l1 in core_labels:
        for l2 in core_labels:
            if l1 in co_matrix_data and l2 in co_matrix_data[l1]:
                co_df.loc[l1, l2] = co_matrix_data[l1][l2]
    log_co_df = np.log1p(co_df)
    plt.figure(figsize=(14, 11))
    sns.heatmap(log_co_df, cmap="magma", annot=False, cbar_kws={'label': 'Log(Co-occurrence Count + 1)'}, linewidths=0.3)
    plt.title("Fig 6: PII Entity Co-occurrence Matrix (Log Scale — Full 1.636M Corpus)", fontsize=14, fontweight="bold", pad=12)
    plt.xlabel("PII Entity Label", fontsize=11)
    plt.ylabel("PII Entity Label", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(EDA_DIR, "fig6_cooccurrence.png"))
    plt.close()
    print("Saved Fig 6 (Log Scaled)", flush=True)

# Fig 7: Subword Token Length Distribution
print("\n--- Generating Fig 7 & Fig 8 (Lengths & Spans) ---", flush=True)
plt.figure(figsize=(10, 5))
sub_token_500k = df["token_count"].sample(500000, random_state=42)
ax = sns.histplot(df["token_count"], bins=60, color="#1976d2", stat="count")
p99_tok = df["token_count"].quantile(0.99)
ax.axvline(512, color="red", linestyle="--", linewidth=1.8, label=f"512 Context Window Ceiling (0.9% > 512)")
ax.axvline(p99_tok, color="purple", linestyle=":", linewidth=1.8, label=f"P99 = {p99_tok:.0f} tokens")
plt.title("Fig 7: mBERT Subword Token Length Distribution (Full Corpus: 1,636,375 Examples)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("mBERT Token Count", fontsize=11)
plt.ylabel("Document Count", fontsize=11)
plt.legend(fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig7_token_lengths.png"))
plt.close()
print("Saved Fig 7", flush=True)

# Fig 8: Average Word Span Length by Entity Type
if span_data:
    top_spans = {k: span_data[k] for k in core_labels if k in span_data}
    if "ORGANISATION" in span_data:
        top_spans["ORGANISATION"] = span_data["ORGANISATION"]
    span_s = pd.Series(top_spans).sort_values(ascending=False)
    plt.figure(figsize=(11, 7))
    ax = span_s.plot(kind="barh", color="#00796b", edgecolor="#004d40")
    plt.title("Fig 8: Average Word Span Length by Entity Type (Full Corpus: 1,636,375 Examples)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Average Word Count per Entity Mention", fontsize=11)
    plt.ylabel("PII Entity Label", fontsize=11)
    ax.invert_yaxis()
    for p in ax.patches:
        w = p.get_width()
        ax.annotate(f"{w:.2f}", (w + 0.05, p.get_y() + p.get_height() / 2.), va='center', fontsize=9)
    plt.xlim(0, max(span_s) * 1.15)
    plt.tight_layout()
    plt.savefig(os.path.join(EDA_DIR, "fig8_span_lengths.png"))
    plt.close()
    print("Saved Fig 8", flush=True)

# Fig 9: Per-Language Entity Composition Heatmap
print("\n--- Generating Fig 9 (Per-Language Entity Composition) ---", flush=True)
if lang_data:
    top_langs = ["ko", "ja", "zh", "en", "vi", "id", "ms", "tl"]
    core_comp_labels = ["GIVENNAME", "SURNAME", "DATE", "CITY", "STREET", "EMAIL", "TELEPHONENUM"]
    comp_matrix = []
    for l in top_langs:
        row_c = [lang_data.get(l, {}).get(e, 0) for e in core_comp_labels]
        comp_matrix.append(row_c)
    comp_df = pd.DataFrame(comp_matrix, index=top_langs, columns=core_comp_labels)
    comp_norm = comp_df.div(comp_df.sum(axis=1), axis=0) * 100
    comp_norm.to_csv(os.path.join(EDA_DIR, "per_language_entity_composition.csv"))
    plt.figure(figsize=(11, 6))
    sns.heatmap(comp_norm, cmap="YlGnBu", annot=True, fmt=".1f", cbar_kws={'label': '% of Core Entities in Language'}, linewidths=0.5)
    plt.title("Fig 9: Per-Language Entity Composition Heatmap (% Across Core Labels — Full Corpus)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Core Entity Class", fontsize=11)
    plt.ylabel("ISO 639-1 Language Code", fontsize=11)
    plt.tight_layout()
    plt.savefig(os.path.join(EDA_DIR, "fig9_language_entity_composition.png"))
    plt.close()
    print("Saved Fig 9", flush=True)

# Fig 10 & 11: Diagnostic Boxplots & Histograms (Full Corpus)
print("\n--- Generating Fig 10, 11, 12, 13 (Distributions) ---", flush=True)
feat_cols = ["char_length", "word_count", "token_count", "entity_count", "pii_token_count", "pii_char_length"]

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.flatten()
for idx, col in enumerate(feat_cols):
    sns.boxplot(y=df[col].to_numpy(), ax=axes[idx], color="#42a5f5")
    axes[idx].set_title(f"Diagnostic Boxplot: {col}", fontsize=11, fontweight="bold")
    axes[idx].set_ylabel("Value")
plt.suptitle("Fig 10: Diagnostic Boxplots of Document Lengths & Target Variables (Full Corpus: 1,636,375 Examples)", fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig10_precleaning_boxplots.png"))
plt.close()
print("Saved Fig 10", flush=True)

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.flatten()
for idx, col in enumerate(feat_cols):
    sns.histplot(df[col].to_numpy(), ax=axes[idx], bins=35, color="#1e88e5")
    axes[idx].set_title(f"Histogram: {col}", fontsize=11, fontweight="bold")
    axes[idx].set_xlabel("Value")
plt.suptitle("Fig 11: Distribution Histograms of Document Length Variables (Full Corpus: 1,636,375 Examples)", fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig11_precleaning_histograms.png"))
plt.close()
print("Saved Fig 11", flush=True)

# Fig 12 & 13: Cleaned Boxplots & Histograms (Capped at P99)
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.flatten()
for idx, col in enumerate(feat_cols):
    cap_val = df[col].quantile(0.99)
    capped_data = np.clip(df[col].to_numpy(), a_min=0, a_max=cap_val)
    sns.boxplot(y=capped_data, ax=axes[idx], color="#66bb6a")
    axes[idx].set_title(f"Cleaned (P99 Cap): {col}", fontsize=11, fontweight="bold")
    axes[idx].set_ylabel("Value")
plt.suptitle("Fig 12: Cleaned Feature Distributions Capped at P99 (Full Corpus: 1,636,375 Examples)", fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig12_cleaned_boxplots.png"))
plt.close()
print("Saved Fig 12", flush=True)

fig, axes = plt.subplots(2, 3, figsize=(15, 8))
axes = axes.flatten()
for idx, col in enumerate(feat_cols):
    cap_val = df[col].quantile(0.99)
    capped_data = np.clip(df[col].to_numpy(), a_min=0, a_max=cap_val)
    sns.histplot(capped_data, ax=axes[idx], bins=35, color="#43a047")
    axes[idx].set_title(f"Cleaned Histogram: {col}", fontsize=11, fontweight="bold")
    axes[idx].set_xlabel("Value")
plt.suptitle("Fig 13: Cleaned Feature Histograms with Stabilized Boundaries (Full Corpus: 1,636,375 Examples)", fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig13_cleaned_histograms.png"))
plt.close()
print("Saved Fig 13", flush=True)

# Fig 14: Normalisation Comparison
print("\n--- Generating Fig 14 (Normalisation Comparison) ---", flush=True)
sub_norm = df[["char_length", "token_count", "entity_count", "pii_token_count"]].sample(200000, random_state=42)
scaler_minmax = MinMaxScaler()
scaler_std = StandardScaler()
norm_mm = pd.DataFrame(scaler_minmax.fit_transform(sub_norm), columns=sub_norm.columns)
norm_std = pd.DataFrame(scaler_std.fit_transform(sub_norm), columns=sub_norm.columns)
norm_log = np.log1p(sub_norm)

fig, axes = plt.subplots(2, 2, figsize=(13, 9))
sns.kdeplot(data=sub_norm, ax=axes[0, 0], common_norm=False)
axes[0, 0].set_title("Raw Feature Distributions", fontsize=11, fontweight="bold")
sns.kdeplot(data=norm_mm, ax=axes[0, 1], common_norm=False)
axes[0, 1].set_title("Min-Max Scaled [0, 1]", fontsize=11, fontweight="bold")
sns.kdeplot(data=norm_std, ax=axes[1, 0], common_norm=False)
axes[1, 0].set_title("Z-Score Standardised (μ=0, σ=1)", fontsize=11, fontweight="bold")
sns.kdeplot(data=norm_log, ax=axes[1, 1], common_norm=False)
axes[1, 1].set_title("Log1p Transformed", fontsize=11, fontweight="bold")
plt.suptitle("Fig 14: Empirical Feature Transformation Comparison (Full Corpus: 1,636,375 Examples)", fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig14_normalisation_comparison.png"))
plt.close()
print("Saved Fig 14", flush=True)

# Fig 15: Multivariate Correlation Heatmap (Full Corpus)
print("\n--- Generating Fig 15 (Multivariate Correlation) ---", flush=True)
num_cols = ["char_length", "word_count", "token_count", "entity_count", "pii_token_count",
            "pii_token_ratio", "pii_char_length", "pii_char_ratio", "avg_entity_char_len", "unique_entity_types"]
corr_matrix = df[num_cols].corr(method="pearson")
plt.figure(figsize=(11, 9))
sns.heatmap(corr_matrix, cmap="coolwarm", vmin=-1, vmax=1, annot=True, fmt=".2f", linewidths=0.5)
plt.title("Fig 15: Multivariate Pearson Correlation Heatmap (Full Corpus: 1,636,375 Examples)", fontsize=13, fontweight="bold", pad=12)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig15_correlation_heatmap.png"))
plt.close()
print("Saved Fig 15", flush=True)

# Fig 16: Multi-Variable Pair Plot (Subsample 100k for Visual Clarity)
print("\n--- Generating Fig 16 (Pair Plot 100k Subsample) ---", flush=True)
pair_sample = df[["char_length", "token_count", "entity_count", "pii_token_count"]].sample(100000, random_state=42)
g = sns.pairplot(pair_sample, diag_kind="kde", plot_kws={'alpha': 0.15, 's': 5, 'color': '#1565c0'}, diag_kws={'color': '#1565c0'})
g.figure.suptitle("Fig 16: Multi-Variable Pair Plot (100,000 Random Subsample for Visual Clarity)", fontsize=13, fontweight="bold", y=1.02)
plt.savefig(os.path.join(EDA_DIR, "fig16_pairplots.png"))
plt.close()
print("Saved Fig 16", flush=True)

# Fig 17: Stratified Target vs Predictor Boxplots (Full Corpus)
print("\n--- Generating Fig 17 (Stratified Boxplots) ---", flush=True)
df["token_bin"] = pd.qcut(df["token_count"], q=5, labels=["Very Low", "Low", "Medium", "High", "Very High"])
plt.figure(figsize=(10, 5))
sns.boxplot(x="token_bin", y="entity_count", data=df, palette="Blues")
plt.title("Fig 17: Stratified Entity Count by Subword Token Quintile (Full Corpus: 1,636,375 Examples)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Token Capacity Quintile", fontsize=11)
plt.ylabel("Ground-Truth PII Entity Count", fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig17_target_vs_predictors_boxplots.png"))
plt.close()
print("Saved Fig 17", flush=True)

# Fig 18: CJK Subword Tokenizer Expansion (Full Corpus)
print("\n--- Generating Fig 18 (CJK Tokenizer Expansion) ---", flush=True)
script_means = df.groupby("script")["tokens_per_char"].agg(["mean", "std", "count"])
print(script_means)

plt.figure(figsize=(9, 5))
sns.barplot(data=df, x="script", y="tokens_per_char", order=["Hans", "Jpan", "Hang", "Latn"], palette=["#e53935", "#fb8c00", "#43a047", "#1e88e5"])
plt.title("Fig 18: Subword Tokenizer Expansion (mBERT Tokens/Char) Across Scripts (Full Corpus: 1,636,375 Examples)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("ISO 15924 Script Identifier", fontsize=11)
plt.ylabel("Mean Subword Tokens per Character", fontsize=11)
for i, sc in enumerate(["Hans", "Jpan", "Hang", "Latn"]):
    m = script_means.loc[sc, "mean"]
    plt.annotate(f"{m:.3f}", (i, m + 0.02), ha='center', fontsize=10, fontweight='bold')
plt.ylim(0, 0.9)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig18_cjk_token_efficiency.png"))
plt.close()
print("Saved Fig 18", flush=True)

# Fig 20 (NEW): Train vs Validation Class Balance for 23 Non-Viable Labels
print("\n--- Generating Fig 20 (Validation Blindness & Drift on 23 Leaked Labels) ---", flush=True)
bottom23 = parity_df.tail(23).copy()
plt.figure(figsize=(14, 9))
y_pos = np.arange(len(bottom23))

plt.barh(y_pos - 0.2, bottom23["Train_Count"], height=0.4, label="Train Count", color="#1976d2", edgecolor="#0d47a1")
plt.barh(y_pos + 0.2, bottom23["Val_Count"], height=0.4, label="Validation Count", color="#ff8f00", edgecolor="#e65100")

plt.yticks(y_pos, bottom23["Label"], fontsize=10)
plt.gca().invert_yaxis()
plt.xlabel("Total Annotation Count (Log Scale)", fontsize=11)
plt.xscale("symlog", linthresh=1)
plt.title("Fig 20: Train vs. Validation Allocation Across 23 Non-Viable Long-Tail Labels (Full Corpus)", fontsize=13, fontweight="bold", pad=12)
plt.legend(loc="lower right", fontsize=11)

# Annotate zero in validation labels
for i, r in bottom23.reset_index().iterrows():
    if r["Val_Count"] == 0:
        plt.annotate("ZERO in Val (Blindness)", (r["Train_Count"] * 1.15 + 0.5, i - 0.2), va='center', fontsize=8, color="#d32f2f", fontweight='bold')
    elif r["Train_Count"] == 0:
        plt.annotate("ZERO in Train (HEIGHT)", (r["Val_Count"] * 1.15 + 0.5, i + 0.2), va='center', fontsize=8, color="#7b1fa2", fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig20_rare_label_imbalance.png"))
plt.close()
print("Saved Fig 20", flush=True)

# ---------------------------------------------------------------------------
# STAGE 4: COMPUTE FULL CORPUS DESCRIPTIVE STATS & IQR BOUNDS
# ---------------------------------------------------------------------------

print("\n--- Computing Full Corpus Summary Statistics & IQR Bounds ---", flush=True)
stat_features = [
    "char_length", "word_count", "token_count", "entity_count", "pii_token_count",
    "pii_token_ratio", "pii_char_length", "pii_char_ratio", "avg_entity_char_len",
    "max_entity_char_len", "unique_entity_types", "tokens_per_char", "chars_per_word", "has_pii"
]

summary_stats = {}
iqr_bounds = {}

for col in stat_features:
    vals = df[col].to_numpy()
    mean_val = float(np.mean(vals))
    std_val = float(np.std(vals))
    min_val = float(np.min(vals))
    q1 = float(np.percentile(vals, 25))
    median_val = float(np.median(vals))
    q3 = float(np.percentile(vals, 75))
    max_val = float(np.max(vals))
    skew_val = float(stats.skew(vals))
    kurt_val = float(stats.kurtosis(vals))
    
    summary_stats[col] = {
        "mean": mean_val,
        "std": std_val,
        "min": min_val,
        "q1": q1,
        "median": median_val,
        "q3": q3,
        "max": max_val,
        "skewness": skew_val,
        "kurtosis": kurt_val
    }
    
    iqr = q3 - q1
    lower_b = q1 - 1.5 * iqr
    upper_b = q3 + 1.5 * iqr
    upper_tail_cnt = int(np.sum(vals > upper_b))
    upper_tail_pct = float((upper_tail_cnt / len(df)) * 100)
    
    iqr_bounds[col] = {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_bound": lower_b,
        "upper_bound": upper_b,
        "upper_tail_count": upper_tail_cnt,
        "upper_tail_pct": upper_tail_pct
    }

output_bundle = {
    "total_rows": len(df),
    "summary_stats": summary_stats,
    "iqr_bounds": iqr_bounds,
    "script_means": script_means.to_dict()
}

with open(STATS_JSON, "w") as f:
    json.dump(output_bundle, f, indent=2)
print("Saved full_corpus_stats.json!", flush=True)

# ---------------------------------------------------------------------------
# STAGE 5: COPY ALL FIGURES TO BRAIN ARTIFACT DIRECTORY
# ---------------------------------------------------------------------------

print("\n--- Copying all 20 figures to artifact directory ---", flush=True)
for i in range(1, 21):
    fig_name = f"fig{i}_"
    # Find matching file in EDA_DIR
    for fname in os.listdir(EDA_DIR):
        if fname.startswith(f"fig{i}_") and fname.endswith(".png"):
            src = os.path.join(EDA_DIR, fname)
            dst = os.path.join(ARTIFACT_DIR, fname)
            shutil.copy2(src, dst)
            print(f"Copied {fname} to artifact dir")
            break

print("="*80, flush=True)
print("ALL 20 FIGURES AND FULL CORPUS STATS GENERATED SUCCESSFULLY!", flush=True)
print("="*80, flush=True)
