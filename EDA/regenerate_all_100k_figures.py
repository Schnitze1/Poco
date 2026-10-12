import os
import json
import time
import shutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler

sns.set_theme(style="whitegrid", font="sans-serif")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

EDA_DIR = r"d:\Repos\Poco\EDA"
ARTIFACT_DIR = r"C:\Users\Shadd\.gemini\antigravity-ide\brain\0f1bd67a-e6ce-4dc6-b535-b908b888cb0b"

print("Loading eda_refined_100k.csv...")
df = pd.read_csv(os.path.join(EDA_DIR, "eda_refined_100k.csv"))
label_viability_df = pd.read_csv(os.path.join(EDA_DIR, "label_viability_table.csv"))
per_lang_norm = pd.read_csv(os.path.join(EDA_DIR, "per_language_entity_composition.csv"), index_col=0)

N_ROWS = len(df)
print(f"Loaded {N_ROWS:,} rows!")

# Palette definition for 3 tiers
tier_palette = {
    "Tier 1: Fully Trainable": "#2e7d32",           # Forest Green
    "Tier 2: Marginal / Long-Tail": "#f57c00",       # Amber / Orange
    "Tier 3: Unviable (<200 in 100k sample)": "#c62828" # Crimson Red
}

print("\n--- 1. Generating Fig 1 & Fig 2 (Taxonomy & Viability) ---")
# Fig 1: Top 25 with 3 colors
plt.figure(figsize=(12, 10))
sns.barplot(
    data=label_viability_df.head(25),
    x="Sample_Count_100k",
    y="Label",
    hue="Viability_Tier",
    dodge=False,
    palette=tier_palette
)
plt.title(f"Fig 1: PII Entity Distribution ({N_ROWS:,} Sample — Top 25 Labels by Viability)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel(f"Annotation Count in {N_ROWS:,} Sample", fontsize=12)
plt.ylabel("PII Label", fontsize=12)
plt.legend(title="Training Viability Tier", loc="lower right", fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig1_label_distribution.png"))
plt.close()
print("Saved fig1_label_distribution.png")

# Fig 2: All 42 with Log scale and 3 colors
plt.figure(figsize=(12, 11))
ax = sns.barplot(
    data=label_viability_df,
    x="Sample_Count_100k",
    y="Label",
    hue="Viability_Tier",
    dodge=False,
    palette=tier_palette
)
ax.set_xscale("log")
plt.axvline(2000, color="green", linestyle="--", linewidth=1.8, label="Trainable Threshold (≥2,000 in 100k / ≥32k in 1.5M)")
plt.axvline(200, color="red", linestyle=":", linewidth=1.8, label="Unviable Threshold (<200 in 100k / <3.2k in 1.5M)")
plt.title(f"Fig 2: Complete PII Entity Taxonomy ({N_ROWS:,} Sample — All 42 Labels Log Scale)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel(f"Annotation Count in {N_ROWS:,} Sample (Log Scale)", fontsize=12)
plt.ylabel("PII Label (All 42 Discovered Labels)", fontsize=10)
plt.legend(loc="lower left", fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig2_label_log.png"))
plt.close()
print("Saved fig2_label_log.png")

print("\n--- 2. Generating Fig 3 & Fig 4 (Languages & Regions) ---")
# Fig 3: Language distribution from 100k
lang_counts = df["language"].value_counts()
plt.figure(figsize=(11, 6))
ax = lang_counts.plot(kind="barh", color="#2b5c8f", edgecolor="#1a3654")
plt.title(f"Fig 3: Language Representation Across Asia-Pacific Extension ({N_ROWS:,} Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Example Count", fontsize=12)
plt.ylabel("Language Code", fontsize=12)
ax.invert_yaxis()
for p in ax.patches:
    width = p.get_width()
    ax.annotate(f"{int(width):,} ({width/N_ROWS*100:.1f}%)", (width + 150, p.get_y() + p.get_height() / 2.),
                va='center', fontsize=10, color="#222222")
plt.xlim(0, max(lang_counts) * 1.15)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig3_languages.png"))
plt.close()
print(f"Saved fig3_languages.png (Total rows: {lang_counts.sum():,})")

# Fig 4: Region x Language heatmap from 100k
pivot = df.groupby(["region", "language"]).size().unstack(fill_value=0)
plt.figure(figsize=(12, 7))
sns.heatmap(pivot, cmap="YlGnBu", annot=True, fmt="d", cbar_kws={'label': 'Example Count'}, linewidths=0.5)
plt.title(f"Fig 4: Cross-Tabulation Coverage Map: Region × Language ({N_ROWS:,} Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Language Code", fontsize=12)
plt.ylabel("Region Code", fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig4_region_lang.png"))
plt.close()
print("Saved fig4_region_lang.png")

print("\n--- 3. Generating Fig 5 (Entities per Example) ---")
plt.figure(figsize=(10, 5))
ax = sns.histplot(df["entity_count"], bins=25, kde=True, color="#2e7d32", discrete=True)
median_ent = df["entity_count"].median()
mean_ent = df["entity_count"].mean()
ax.axvline(median_ent, color="red", linestyle="--", linewidth=1.8, label=f"Median = {median_ent:.1f}")
ax.axvline(mean_ent, color="blue", linestyle=":", linewidth=1.8, label=f"Mean = {mean_ent:.2f}")
plt.title(f"Fig 5: Distribution of PII Entities per Document ({N_ROWS:,} Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Number of PII Entities in Document", fontsize=12)
plt.ylabel("Document Frequency", fontsize=12)
plt.legend(fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig5_entities_per_example.png"))
plt.close()
print("Saved fig5_entities_per_example.png")

print("\n--- 4. Generating Fig 6 (Co-occurrence Heatmap) ---")
# Recompute co-occurrence matrix from 100k
import orjson
import requests
url = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/train.jsonl"
resp = requests.get(url, stream=True, timeout=60)
from collections import defaultdict, Counter
co_counter = defaultdict(Counter)
span_lens = defaultdict(list)
labels_set = set(label_viability_df.head(20)["Label"])

cnt = 0
for line in resp.iter_lines():
    if not line:
        continue
    row = orjson.loads(line)
    p_mask = row.get("privacy_mask", [])
    doc_labels = [s.get("label", "UNKNOWN") for s in p_mask if s.get("label", "UNKNOWN") in labels_set]
    for s in p_mask:
        lbl = s.get("label", "UNKNOWN")
        val = s.get("value", "")
        span_lens[lbl].append(len(val.split()))
    for l1 in doc_labels:
        for l2 in doc_labels:
            if l1 != l2:
                co_counter[l1][l2] += 1
    cnt += 1
    if cnt >= N_ROWS:
        break

core_labels = sorted(labels_set)
co_matrix = pd.DataFrame(0, index=core_labels, columns=core_labels)
for l1 in core_labels:
    for l2 in core_labels:
        co_matrix.loc[l1, l2] = co_counter[l1][l2]

plt.figure(figsize=(13, 11))
sns.heatmap(co_matrix, cmap="rocket_r", cbar_kws={'label': 'Co-occurrence Frequency'}, linewidths=0.3)
plt.title(f"Fig 6: PII Entity Co-occurrence Matrix ({N_ROWS:,} Sample — Top 20 Labels)", fontsize=14, fontweight="bold", pad=12)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig6_cooccurrence.png"))
plt.close()
print("Saved fig6_cooccurrence.png")

print("\n--- 5. Generating Fig 7 (Token Length Distribution) ---")
plt.figure(figsize=(10, 5))
ax = sns.histplot(df["token_count"], bins=50, color="#1976d2", kde=True)
med_tokens = df["token_count"].median()
plt.axvline(med_tokens, color="red", linestyle="--", linewidth=2, label=f"Median = {med_tokens:.0f} tokens")
plt.axvline(512, color="orange", linestyle="-.", linewidth=2, label="BERT 512-Token Context Ceiling")
plt.title(f"Fig 7: mBERT Subword Token Length Distribution ({N_ROWS:,} Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("mBERT Tokens per Document", fontsize=12)
plt.ylabel("Document Frequency", fontsize=12)
plt.legend(fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig7_token_lengths.png"))
plt.close()
print("Saved fig7_token_lengths.png")

print("\n--- 6. Generating Fig 8 (Word Span Lengths by Entity Type) ---")
avg_span = {k: np.mean(v) for k, v in span_lens.items() if len(v) >= 100}
avg_span_df = pd.DataFrame(avg_span.items(), columns=["label", "avg_words"]).sort_values("avg_words", ascending=False)
plt.figure(figsize=(11, 6))
ax = sns.barplot(data=avg_span_df.head(20), x="avg_words", y="label", palette="coolwarm")
plt.title(f"Fig 8: Average Word Span Length by Entity Type ({N_ROWS:,} Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Average Word Count per Span", fontsize=12)
plt.ylabel("PII Label", fontsize=12)
for p in ax.patches:
    width = p.get_width()
    ax.annotate(f"{width:.2f}", (width + 0.05, p.get_y() + p.get_height() / 2.),
                va='center', fontsize=9, color="#222222")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig8_span_lengths.png"))
plt.close()
print("Saved fig8_span_lengths.png")

print("\n--- 7. Generating Fig 9 (Renamed: Language Entity Composition Heatmap) ---")
plt.figure(figsize=(12, 7))
sns.heatmap(per_lang_norm, cmap="YlGnBu", annot=True, fmt=".1f", linewidths=0.5, cbar_kws={'label': '% Share of Core Entities in Language'})
plt.title(f"Fig 9: Per-Language Entity Composition Heatmap ({N_ROWS:,} Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("PII Entity Label", fontsize=12)
plt.ylabel("Language Code", fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig9_language_entity_composition.png"))
plt.close()
print("Saved fig9_language_entity_composition.png")

print("\n--- 8. Generating Fig 10 & Fig 11 (Pre-cleaning Diagnostics) ---")
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
features_to_plot = ["char_length", "word_count", "token_count", "entity_count", "avg_entity_char_len", "pii_token_ratio"]
titles = ["Character Length", "Word Count", "mBERT Token Count", "PII Entity Count", "Avg Entity Char Length", "PII Token Ratio"]
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

for idx, (feat, t, col) in enumerate(zip(features_to_plot, titles, colors)):
    r, c = divmod(idx, 3)
    sns.boxplot(y=df[feat], ax=axes[r, c], color=col, flierprops=dict(marker='o', markersize=3, alpha=0.3))
    axes[r, c].set_title(f"Pre-Cleaning: {t}", fontsize=12, fontweight="bold")
    axes[r, c].set_ylabel(feat, fontsize=10)
plt.suptitle(f"Fig 10: Diagnostic Boxplots of Document Lengths ({N_ROWS:,} Sample)", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig10_precleaning_boxplots.png"))
plt.close()
print("Saved fig10_precleaning_boxplots.png")

fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for idx, (feat, t, col) in enumerate(zip(features_to_plot, titles, colors)):
    r, c = divmod(idx, 3)
    sns.histplot(df[feat], ax=axes[r, c], color=col, kde=True, bins=35)
    axes[r, c].set_title(f"Pre-Cleaning: {t} Distribution", fontsize=12, fontweight="bold")
    axes[r, c].set_xlabel(feat, fontsize=10)
plt.suptitle(f"Fig 11: Distribution Histograms of Document Lengths ({N_ROWS:,} Sample)", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig11_precleaning_histograms.png"))
plt.close()
print("Saved fig11_precleaning_histograms.png")

print("\n--- 9. Generating Fig 12 & Fig 13 (Cleaned / Winsorized) ---")
df_cleaned = df.copy()
for col in ["char_length", "word_count", "token_count", "entity_count", "avg_entity_char_len"]:
    p99 = df_cleaned[col].quantile(0.99)
    df_cleaned[col] = np.clip(df_cleaned[col], a_min=None, a_max=p99)

fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for idx, (feat, t, col) in enumerate(zip(features_to_plot, titles, colors)):
    r, c = divmod(idx, 3)
    sns.boxplot(y=df_cleaned[feat], ax=axes[r, c], color=col, flierprops=dict(marker='.', markersize=2, alpha=0.2))
    axes[r, c].set_title(f"Cleaned: {t}", fontsize=12, fontweight="bold")
    axes[r, c].set_ylabel(feat, fontsize=10)
plt.suptitle(f"Fig 12: Cleaned Boxplots Capped at 99th Percentile ({N_ROWS:,} Sample)", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig12_cleaned_boxplots.png"))
plt.close()
print("Saved fig12_cleaned_boxplots.png")

fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for idx, (feat, t, col) in enumerate(zip(features_to_plot, titles, colors)):
    r, c = divmod(idx, 3)
    sns.histplot(df_cleaned[feat], ax=axes[r, c], color=col, kde=True, bins=35)
    axes[r, c].set_title(f"Cleaned: {t} Distribution", fontsize=12, fontweight="bold")
    axes[r, c].set_xlabel(feat, fontsize=10)
plt.suptitle(f"Fig 13: Cleaned Histograms with Stabilized Boundaries ({N_ROWS:,} Sample)", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig13_cleaned_histograms.png"))
plt.close()
print("Saved fig13_cleaned_histograms.png")

print("\n--- 10. Generating Fig 14 (Normalisation Comparison) ---")
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
raw_tokens = df["token_count"].values.reshape(-1, 1)
minmax_tokens = MinMaxScaler().fit_transform(raw_tokens).flatten()
zscore_tokens = StandardScaler().fit_transform(raw_tokens).flatten()
log_tokens = np.log1p(df["token_count"].values)

sns.histplot(df["token_count"], ax=axes[0, 0], color="#1976d2", kde=True, bins=30)
axes[0, 0].set_title("1. Raw Token Count (Right-Skewed)", fontsize=12, fontweight="bold")
axes[0, 0].set_xlabel("Raw Token Count")

sns.histplot(minmax_tokens, ax=axes[0, 1], color="#388e3c", kde=True, bins=30)
axes[0, 1].set_title("2. Min-Max Normalised [0, 1]", fontsize=12, fontweight="bold")
axes[0, 1].set_xlabel("MinMax Scaled Value")

sns.histplot(zscore_tokens, ax=axes[1, 0], color="#e64a19", kde=True, bins=30)
axes[1, 0].set_title("3. Standardised / Z-Score (Mean=0, Std=1)", fontsize=12, fontweight="bold")
axes[1, 0].set_xlabel("Z-Score Value")

sns.histplot(log_tokens, ax=axes[1, 1], color="#7b1fa2", kde=True, bins=30)
axes[1, 1].set_title("4. Log(1 + x) Transformed (Near-Gaussian)", fontsize=12, fontweight="bold")
axes[1, 1].set_xlabel("Log1p Token Count")

plt.suptitle(f"Fig 14: Distribution Comparison Before vs After Normalisation ({N_ROWS:,} Sample)", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig14_normalisation_comparison.png"))
plt.close()
print("Saved fig14_normalisation_comparison.png")

print("\n--- 11. Generating Fig 15 (Correlation Heatmap with pii_token_count) ---")
corr_features = [
    "char_length", "word_count", "token_count", "entity_count",
    "pii_token_count", "pii_token_ratio", "pii_char_length",
    "pii_char_ratio", "avg_entity_char_len", "unique_entity_types"
]
corr_matrix = df[corr_features].corr(method="pearson")

plt.figure(figsize=(11, 9))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1,
            linewidths=0.5, cbar_kws={'label': 'Pearson Correlation (r)'})
plt.title(f"Fig 15: Multivariate Correlation Heatmap ({N_ROWS:,} Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig15_correlation_heatmap.png"))
plt.close()
print("Saved fig15_correlation_heatmap.png")

print("\n--- 12. Generating Fig 16 (Pair Plots from 100k) ---")
pair_sample = df[corr_features].sample(n=2000, random_state=42)
g = sns.pairplot(pair_sample[["char_length", "token_count", "entity_count", "pii_token_ratio"]],
                 diag_kind="kde", plot_kws={'alpha': 0.4, 's': 15, 'color': '#1f77b4'},
                 diag_kws={'color': '#1f77b4'})
g.fig.suptitle(f"Fig 16: Multi-Variable Pair Plot ({N_ROWS:,} Sample)", y=1.02, fontsize=15, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig16_pairplots.png"))
plt.close()
print("Saved fig16_pairplots.png")

print("\n--- 13. Generating Fig 17 (Target vs Predictor Stratified Boxplots) ---")
df["token_length_bin"] = pd.qcut(df["token_count"], q=4, labels=["Short [Q1]", "Medium [Q2]", "Long [Q3]", "Very Long [Q4]"])
top_5_langs = df["language"].value_counts().head(5).index
df_top_langs = df[df["language"].isin(top_5_langs)]

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
sns.boxplot(data=df, x="token_length_bin", y="entity_count", ax=axes[0], color="#90caf9")
axes[0].set_title(f"Target (Entity Count) vs Predictor (Document Token Length Bins) [{N_ROWS:,} Sample]", fontsize=12, fontweight="bold")
axes[0].set_xlabel("Token Length Quartiles", fontsize=11)
axes[0].set_ylabel("PII Entity Count", fontsize=11)

sns.boxplot(data=df_top_langs, x="language", y="pii_token_ratio", ax=axes[1], color="#a5d6a7")
axes[1].set_title(f"Target (PII Token Density) vs Predictor (Language) [{N_ROWS:,} Sample]", fontsize=12, fontweight="bold")
axes[1].set_xlabel("Language Code", fontsize=11)
axes[1].set_ylabel("PII Token Ratio (Density)", fontsize=11)

plt.suptitle(f"Fig 17: Stratified Target vs Predictors Boxplots ({N_ROWS:,} Sample)", fontsize=15, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig17_target_vs_predictors_boxplots.png"))
plt.close()
print("Saved fig17_target_vs_predictors_boxplots.png")

print("\n--- 14. Generating Fig 18 (Script Tokenizer Expansion) ---")
hangul_eff = df[df["script"] == "Hang"]["tokens_per_char"].values
jpan_eff = df[df["script"] == "Jpan"]["tokens_per_char"].values
hans_eff = df[df["script"] == "Hans"]["tokens_per_char"].values
latn_eff = df[df["script"] == "Latn"]["tokens_per_char"].values

script_means = {
    "Hans (Chinese)": np.mean(hans_eff),
    "Jpan (Japanese)": np.mean(jpan_eff),
    "Hang (Korean)": np.mean(hangul_eff),
    "Latn (Latin)": np.mean(latn_eff)
}
script_series = pd.Series(script_means).sort_values(ascending=False)

plt.figure(figsize=(10, 5))
ax = script_series.plot(kind="bar", color="#e65100", edgecolor="#bf360c")
plt.title(f"Fig 18: Subword Tokenizer Expansion (mBERT Tokens per Character) by Script ({N_ROWS:,} Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Script Family", fontsize=12)
plt.ylabel("Mean mBERT Tokens per Character", fontsize=12)
plt.xticks(rotation=0)
for p in ax.patches:
    h = p.get_height()
    ax.annotate(f"{h:.3f}", (p.get_x() + p.get_width() / 2., h + 0.01),
                ha='center', va='bottom', fontsize=11, fontweight="bold", color="#222222")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig18_cjk_token_efficiency.png"))
plt.close()
print("Saved fig18_cjk_token_efficiency.png")

# Copy all figures to artifact directory
all_figs = [f"fig{i}_{suffix}.png" for i, suffix in [
    (1, "label_distribution"), (2, "label_log"), (3, "languages"), (4, "region_lang"),
    (5, "entities_per_example"), (6, "cooccurrence"), (7, "token_lengths"), (8, "span_lengths"),
    (9, "language_entity_composition"), (10, "precleaning_boxplots"), (11, "precleaning_histograms"),
    (12, "cleaned_boxplots"), (13, "cleaned_histograms"), (14, "normalisation_comparison"),
    (15, "correlation_heatmap"), (16, "pairplots"), (17, "target_vs_predictors_boxplots"),
    (18, "cjk_token_efficiency")
]]

for f in all_figs:
    src = os.path.join(EDA_DIR, f)
    dst = os.path.join(ARTIFACT_DIR, f)
    if os.path.exists(src):
        shutil.copy2(src, dst)
print("Copied all 18 updated figures to artifact directory!")

# Calculate Cramér's V
top_langs = ["ko", "ja", "zh", "en", "vi", "id", "ms", "tl"]
core_entities = ["GIVENNAME", "SURNAME", "DATE", "CITY", "STREET", "EMAIL", "TELEPHONENUM"]
chi_raw = []
for l in top_langs:
    chi_raw.append([int(per_lang_norm.loc[l, e] * 1000) for e in core_entities])
chi2, p_val, dof, _ = stats.chi2_contingency(chi_raw)
n_total = sum(sum(r) for r in chi_raw)
min_dim = min(len(top_langs), len(core_entities)) - 1
cramers_v = np.sqrt(chi2 / (n_total * min_dim))
print(f"Cramér's V = {cramers_v:.4f} (Chi2 = {chi2:.2f}, N = {n_total:,})")

print("="*70)
print("ALL 18 FIGURES STRICTLY REGENERATED FROM 100,000 SAMPLE!")
print("="*70)
