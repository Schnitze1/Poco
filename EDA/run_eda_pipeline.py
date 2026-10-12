import os
import sys
import json
import time
import requests
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import MinMaxScaler, StandardScaler

# Set aesthetic styling
sns.set_theme(style="whitegrid", font="sans-serif")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

EDA_DIR = r"d:\Repos\Poco\EDA"
os.makedirs(EDA_DIR, exist_ok=True)

print("="*70)
print("STAGE 1: STREAMING 50,000 ROWS FROM HUGGING FACE")
print("="*70)

URL = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/train.jsonl"
t0 = time.time()

resp = requests.get(URL, stream=True, timeout=60)
resp.raise_for_status()

rows = []
label_counter = Counter()
co_counter = defaultdict(Counter)
span_lengths_words = defaultdict(list)
span_lengths_chars = defaultdict(list)

N = 50_000
count = 0

for line in resp.iter_lines():
    if not line:
        continue
    data = json.loads(line)
    
    src_text = data.get("source_text", "")
    msk_text = data.get("masked_text", "")
    privacy_mask = data.get("privacy_mask", [])
    mbert_tokens = data.get("mbert_tokens", [])
    mbert_classes = data.get("mbert_token_classes", [])
    
    # Feature extraction per row
    char_len = len(src_text)
    word_len = len(src_text.split())
    token_len = len(mbert_tokens)
    entity_cnt = len(privacy_mask)
    
    # PII token count (non-'O')
    pii_token_cnt = sum(1 for c in mbert_classes if c != 'O')
    pii_token_ratio = (pii_token_cnt / token_len) if token_len > 0 else 0.0
    
    # PII character coverage
    pii_char_len = sum(len(s.get("value", "")) for s in privacy_mask)
    pii_char_ratio = (pii_char_len / char_len) if char_len > 0 else 0.0
    
    # Entity level metrics
    if entity_cnt > 0:
        ent_char_lens = [len(s.get("value", "")) for s in privacy_mask]
        avg_ent_char_len = float(np.mean(ent_char_lens))
        max_ent_char_len = float(np.max(ent_char_lens))
        labels_in_ex = [s.get("label", "UNKNOWN") for s in privacy_mask]
        uniq_ent_types = len(set(labels_in_ex))
    else:
        avg_ent_char_len = 0.0
        max_ent_char_len = 0.0
        labels_in_ex = []
        uniq_ent_types = 0
        
    for s in privacy_mask:
        lbl = s.get("label", "UNKNOWN")
        val = s.get("value", "")
        label_counter[lbl] += 1
        span_lengths_words[lbl].append(len(val.split()))
        span_lengths_chars[lbl].append(len(val))
        
    # Co-occurrence
    for l1 in labels_in_ex:
        for l2 in labels_in_ex:
            if l1 != l2:
                co_counter[l1][l2] += 1

    rows.append({
        "uid": str(data.get("uid", "")),
        "language": data.get("language", ""),
        "region": data.get("region", ""),
        "script": data.get("script", ""),
        "source_dataset": data.get("source_dataset", ""),
        "char_length": char_len,
        "word_count": word_len,
        "token_count": token_len,
        "entity_count": entity_cnt,
        "pii_token_count": pii_token_cnt,
        "pii_token_ratio": pii_token_ratio,
        "pii_char_length": pii_char_len,
        "pii_char_ratio": pii_char_ratio,
        "avg_entity_char_len": avg_ent_char_len,
        "max_entity_char_len": max_ent_char_len,
        "unique_entity_types": uniq_ent_types,
        "tokens_per_char": (token_len / char_len) if char_len > 0 else 0.0,
        "chars_per_word": (char_len / word_len) if word_len > 0 else 0.0,
        "has_pii": 1 if entity_cnt > 0 else 0
    })
    
    count += 1
    if count % 10000 == 0:
        print(f"Processed {count} rows in {time.time() - t0:.2f}s...")
    if count >= N:
        break

t1 = time.time()
print(f"Dataset streaming complete! Extracted {len(rows)} rows in {t1 - t0:.2f} seconds.")

df = pd.DataFrame(rows)
df.to_csv(os.path.join(EDA_DIR, "eda_sample_50k.csv"), index=False)
print("Saved eda_sample_50k.csv! Shape:", df.shape)

print("="*70)
print("STAGE 2: COMPUTING METRICS & SUMMARY STATISTICS")
print("="*70)

num_cols = [
    "char_length", "word_count", "token_count", "entity_count",
    "pii_token_count", "pii_token_ratio", "pii_char_length",
    "pii_char_ratio", "avg_entity_char_len", "unique_entity_types"
]

desc = df[num_cols].describe().T
desc["skew"] = df[num_cols].skew()
desc["kurtosis"] = df[num_cols].kurtosis()
print("\n--- Numerical Variables Summary (df.describe()) ---")
print(desc)

# Missing values
missing = df.isnull().sum()
missing_pct = (missing / len(df)) * 100
missing_df = pd.DataFrame({"Missing_Count": missing, "Missing_Percentage": missing_pct})
print("\n--- Missing Values Analysis ---")
print(missing_df)

# Duplicates
dup_uids = df["uid"].duplicated().sum()
dup_rows = df.duplicated().sum()
print(f"\nDuplicates by UID: {dup_uids}, Total duplicated rows: {dup_rows}")

# Outlier analysis via IQR
outliers_info = {}
for col in num_cols:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    lower_outliers = (df[col] < lower_bound).sum()
    upper_outliers = (df[col] > upper_bound).sum()
    outliers_info[col] = {
        "Q1": float(q1),
        "Q3": float(q3),
        "IQR": float(iqr),
        "Lower_Bound": float(lower_bound),
        "Upper_Bound": float(upper_bound),
        "Lower_Outliers": int(lower_outliers),
        "Upper_Outliers": int(upper_outliers),
        "Total_Outliers": int(lower_outliers + upper_outliers),
        "Outlier_Pct": float(((lower_outliers + upper_outliers) / len(df)) * 100)
    }

outliers_df = pd.DataFrame(outliers_info).T
print("\n--- Outliers Detection (IQR Method) ---")
print(outliers_df)

# Label stats
label_df = pd.DataFrame(label_counter.items(), columns=["label", "count"]).sort_values("count", ascending=False)
label_df["percentage"] = (label_df["count"] / label_df["count"].sum()) * 100
print("\n--- PII Entity Label Counts (50k sample) ---")
print(label_df)

# Save stats JSON for report generation
stats_bundle = {
    "sample_shape": list(df.shape),
    "total_corpus_examples": 1636375,
    "train_examples": 1309912,
    "validation_examples": 326463,
    "num_labels": len(label_counter),
    "total_sample_annotations": int(label_df["count"].sum()),
    "summary_stats": desc.to_dict(),
    "missing_stats": missing_df.to_dict(),
    "outliers_stats": outliers_info,
    "label_distribution": label_df.to_dict(orient="records"),
    "top_languages": df["language"].value_counts().head(20).to_dict(),
    "top_regions": df["region"].value_counts().head(20).to_dict()
}
with open(os.path.join(EDA_DIR, "stats_summary.json"), "w", encoding="utf-8") as f:
    json.dump(stats_bundle, f, indent=2)

print("="*70)
print("STAGE 3: GENERATING HIGH-QUALITY VISUALIZATIONS")
print("="*70)

# Fig 1: Label distribution (linear)
plt.figure(figsize=(11, 6))
ax = sns.barplot(data=label_df, x="count", y="label", palette="viridis")
plt.title("Fig 1: PII Entity Distribution — OpenPII 1.5M (50,000 Sample)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Annotation Count", fontsize=12)
plt.ylabel("PII Label", fontsize=12)
for p in ax.patches:
    width = p.get_width()
    ax.annotate(f"{int(width):,}", (width + max(label_df['count'])*0.01, p.get_y() + p.get_height() / 2.),
                va='center', fontsize=9, color="#222222")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig1_label_distribution.png"))
plt.close()
print("Saved fig1_label_distribution.png")

# Fig 2: Label distribution (log scale)
plt.figure(figsize=(11, 6))
ax = sns.barplot(data=label_df, x="count", y="label", palette="magma")
ax.set_xscale("log")
plt.title("Fig 2: PII Entity Distribution (Log Scale — Long-Tail Analysis)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Annotation Count (Log Scale)", fontsize=12)
plt.ylabel("PII Label", fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig2_label_log.png"))
plt.close()
print("Saved fig2_label_log.png")

# Fig 3: Language distribution
lang_counts = df["language"].value_counts()
plt.figure(figsize=(11, 6))
ax = lang_counts.head(20).plot(kind="barh", color="#2b5c8f", edgecolor="#1a3654")
plt.title("Fig 3: Top 20 Languages Representation — OpenPII 1.5M", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Example Count", fontsize=12)
plt.ylabel("Language Code", fontsize=12)
ax.invert_yaxis()
for p in ax.patches:
    width = p.get_width()
    ax.annotate(f"{int(width):,}", (width + max(lang_counts)*0.01, p.get_y() + p.get_height() / 2.),
                va='center', fontsize=9, color="#222222")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig3_languages.png"))
plt.close()
print("Saved fig3_languages.png")

# Fig 4: Region x Language heatmap
top_langs = df["language"].value_counts().head(12).index
top_regions = df["region"].value_counts().head(16).index
sub_df = df[df["language"].isin(top_langs) & df["region"].isin(top_regions)]
pivot = sub_df.groupby(["region", "language"]).size().unstack(fill_value=0)

plt.figure(figsize=(13, 8))
sns.heatmap(pivot, cmap="YlGnBu", annot=True, fmt="d", cbar_kws={'label': 'Example Count'}, linewidths=0.5)
plt.title("Fig 4: Cross-Tabulation Coverage Map: Region × Language", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Language", fontsize=12)
plt.ylabel("Region", fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig4_region_lang.png"))
plt.close()
print("Saved fig4_region_lang.png")

# Fig 5: Entities per example distribution
plt.figure(figsize=(10, 5))
ax = sns.histplot(df["entity_count"], bins=25, kde=True, color="#2e7d32", discrete=True)
median_ent = df["entity_count"].median()
mean_ent = df["entity_count"].mean()
ax.axvline(median_ent, color="red", linestyle="--", linewidth=1.8, label=f"Median = {median_ent:.1f}")
ax.axvline(mean_ent, color="blue", linestyle=":", linewidth=1.8, label=f"Mean = {mean_ent:.1f}")
plt.title("Fig 5: Distribution of PII Entities per Document (PII Density)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Number of PII Entities in Document", fontsize=12)
plt.ylabel("Document Count", fontsize=12)
plt.legend(fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig5_entities_per_example.png"))
plt.close()
print("Saved fig5_entities_per_example.png")

# Fig 6: Co-occurrence heatmap
all_labels = sorted(label_counter.keys())
co_matrix = pd.DataFrame(0, index=all_labels, columns=all_labels)
for l1, neighbours in co_counter.items():
    for l2, cnt in neighbours.items():
        if l1 in all_labels and l2 in all_labels:
            co_matrix.loc[l1, l2] = cnt

plt.figure(figsize=(13, 11))
sns.heatmap(co_matrix, cmap="rocket_r", cbar_kws={'label': 'Co-occurrence Frequency'}, linewidths=0.3)
plt.title("Fig 6: PII Entity Co-occurrence Matrix (Structural Coupling)", fontsize=14, fontweight="bold", pad=12)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig6_cooccurrence.png"))
plt.close()
print("Saved fig6_cooccurrence.png")

# Fig 7: Token length distribution
plt.figure(figsize=(10, 5))
ax = sns.histplot(df["token_count"], bins=50, color="#1976d2", kde=True)
med_tokens = df["token_count"].median()
plt.axvline(med_tokens, color="red", linestyle="--", linewidth=2, label=f"Median = {med_tokens:.0f} tokens")
plt.axvline(512, color="orange", linestyle="-.", linewidth=2, label="BERT 512-Token Window")
plt.title("Fig 7: mBERT Subword Token Count Distribution per Document", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("mBERT Tokens per Document", fontsize=12)
plt.ylabel("Document Frequency", fontsize=12)
plt.legend(fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig7_token_lengths.png"))
plt.close()
print("Saved fig7_token_lengths.png")

# Fig 8: Span length by entity type
avg_span = {k: np.mean(v) for k, v in span_lengths_words.items()}
avg_span_df = pd.DataFrame(avg_span.items(), columns=["label", "avg_words"]).sort_values("avg_words", ascending=False)
plt.figure(figsize=(11, 6))
ax = sns.barplot(data=avg_span_df, x="avg_words", y="label", palette="coolwarm")
plt.title("Fig 8: Average Word Span Length by PII Entity Type", fontsize=14, fontweight="bold", pad=12)
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

# Fig 9: Missing values heatmap
plt.figure(figsize=(10, 4))
sample_null = df[num_cols].isnull()
sns.heatmap(sample_null.iloc[:1000], cbar=False, cmap=["#2e7d32", "#c62828"])
plt.title("Fig 9: Missing Values Heatmap (1,000 Row Subsample — 0% Missingness)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Features", fontsize=12)
plt.ylabel("Sample Index", fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig9_missing_values_heatmap.png"))
plt.close()
print("Saved fig9_missing_values_heatmap.png")

# Fig 10: Pre-cleaning Boxplots
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
features_to_plot = ["char_length", "word_count", "token_count", "entity_count", "avg_entity_char_len", "pii_token_ratio"]
titles = ["Character Length", "Word Count", "mBERT Token Count", "PII Entity Count", "Avg Entity Char Length", "PII Token Ratio"]
colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

for idx, (feat, t, col) in enumerate(zip(features_to_plot, titles, colors)):
    r, c = divmod(idx, 3)
    sns.boxplot(y=df[feat], ax=axes[r, c], color=col, flierprops=dict(marker='o', markersize=3, alpha=0.3))
    axes[r, c].set_title(f"Pre-Cleaning: {t}", fontsize=12, fontweight="bold")
    axes[r, c].set_ylabel(feat, fontsize=10)
plt.suptitle("Fig 10: Pre-Cleaning Boxplots Showing Raw Outliers", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig10_precleaning_boxplots.png"))
plt.close()
print("Saved fig10_precleaning_boxplots.png")

# Fig 11: Pre-cleaning Histograms
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for idx, (feat, t, col) in enumerate(zip(features_to_plot, titles, colors)):
    r, c = divmod(idx, 3)
    sns.histplot(df[feat], ax=axes[r, c], color=col, kde=True, bins=35)
    axes[r, c].set_title(f"Pre-Cleaning: {t} Distribution", fontsize=12, fontweight="bold")
    axes[r, c].set_xlabel(feat, fontsize=10)
plt.suptitle("Fig 11: Pre-Cleaning Histograms with Heavy Right-Skew", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig11_precleaning_histograms.png"))
plt.close()
print("Saved fig11_precleaning_histograms.png")

# Cleaned data: Winsorize upper 99th percentile for text length / tokens / entity counts
df_cleaned = df.copy()
for col in ["char_length", "word_count", "token_count", "entity_count", "avg_entity_char_len"]:
    p99 = df_cleaned[col].quantile(0.99)
    df_cleaned[col] = np.clip(df_cleaned[col], a_min=None, a_max=p99)

# Fig 12: Cleaned Boxplots
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for idx, (feat, t, col) in enumerate(zip(features_to_plot, titles, colors)):
    r, c = divmod(idx, 3)
    sns.boxplot(y=df_cleaned[feat], ax=axes[r, c], color=col, flierprops=dict(marker='.', markersize=2, alpha=0.2))
    axes[r, c].set_title(f"Cleaned: {t}", fontsize=12, fontweight="bold")
    axes[r, c].set_ylabel(feat, fontsize=10)
plt.suptitle("Fig 12: Cleaned Boxplots (Capped at 99th Percentile)", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig12_cleaned_boxplots.png"))
plt.close()
print("Saved fig12_cleaned_boxplots.png")

# Fig 13: Cleaned Histograms
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for idx, (feat, t, col) in enumerate(zip(features_to_plot, titles, colors)):
    r, c = divmod(idx, 3)
    sns.histplot(df_cleaned[feat], ax=axes[r, c], color=col, kde=True, bins=35)
    axes[r, c].set_title(f"Cleaned: {t} Distribution", fontsize=12, fontweight="bold")
    axes[r, c].set_xlabel(feat, fontsize=10)
plt.suptitle("Fig 13: Cleaned Histograms with Stabilized Boundaries", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig13_cleaned_histograms.png"))
plt.close()
print("Saved fig13_cleaned_histograms.png")

# Fig 14: Data distribution comparison before vs after normalisation
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

plt.suptitle("Fig 14: Distribution Comparison Before vs After Normalisation", fontsize=16, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig14_normalisation_comparison.png"))
plt.close()
print("Saved fig14_normalisation_comparison.png")

# Fig 15: Correlation Heatmap
corr_features = [
    "char_length", "word_count", "token_count", "entity_count",
    "pii_token_ratio", "pii_char_ratio", "avg_entity_char_len", "unique_entity_types"
]
corr_matrix = df[corr_features].corr(method="pearson")

plt.figure(figsize=(10, 8))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1,
            linewidths=0.5, cbar_kws={'label': 'Pearson Correlation (r)'})
plt.title("Fig 15: Multivariate Correlation Heatmap (Predictors & Target)", fontsize=14, fontweight="bold", pad=12)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig15_correlation_heatmap.png"))
plt.close()
print("Saved fig15_correlation_heatmap.png")

# Fig 16: Pair Plots
pair_sample = df[corr_features].sample(n=2000, random_state=42)
g = sns.pairplot(pair_sample[["char_length", "token_count", "entity_count", "pii_token_ratio"]],
                 diag_kind="kde", plot_kws={'alpha': 0.4, 's': 15, 'color': '#1f77b4'},
                 diag_kws={'color': '#1f77b4'})
g.fig.suptitle("Fig 16: Multi-Variable Pair Plot (Key Predictors & Target)", y=1.02, fontsize=15, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig16_pairplots.png"))
plt.close()
print("Saved fig16_pairplots.png")

# Fig 17: Target vs Predictor boxplots
df["token_length_bin"] = pd.qcut(df["token_count"], q=4, labels=["Short [Q1]", "Medium [Q2]", "Long [Q3]", "Very Long [Q4]"])
top_5_langs = df["language"].value_counts().head(5).index
df_top_langs = df[df["language"].isin(top_5_langs)]

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
sns.boxplot(data=df, x="token_length_bin", y="entity_count", ax=axes[0], palette="Blues")
axes[0].set_title("Target (Entity Count) vs Predictor (Document Token Length Bins)", fontsize=12, fontweight="bold")
axes[0].set_xlabel("Token Length Quartiles", fontsize=11)
axes[0].set_ylabel("PII Entity Count", fontsize=11)

sns.boxplot(data=df_top_langs, x="language", y="pii_token_ratio", ax=axes[1], palette="Set2")
axes[1].set_title("Target (PII Token Density) vs Predictor (Language)", fontsize=12, fontweight="bold")
axes[1].set_xlabel("Language Code", fontsize=11)
axes[1].set_ylabel("PII Token Ratio (Density)", fontsize=11)

plt.suptitle("Fig 17: Target vs Predictors Stratified Boxplots", fontsize=15, fontweight="bold", y=0.99)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig17_target_vs_predictors_boxplots.png"))
plt.close()
print("Saved fig17_target_vs_predictors_boxplots.png")

# Fig 18: CJK Subword Token Efficiency across Scripts
plt.figure(figsize=(11, 5))
script_eff = df.groupby("script")["tokens_per_char"].mean().sort_values(ascending=False)
ax = script_eff.plot(kind="bar", color="#e65100", edgecolor="#bf360c")
plt.title("Fig 18: Subword Tokenizer Expansion (Tokens per Char) Across Scripts", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Script Family", fontsize=12)
plt.ylabel("Mean mBERT Tokens per Character", fontsize=12)
plt.xticks(rotation=0)
for p in ax.patches:
    h = p.get_height()
    ax.annotate(f"{h:.3f}", (p.get_x() + p.get_width() / 2., h + 0.005),
                ha='center', va='bottom', fontsize=10, color="#222222")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig18_cjk_token_efficiency.png"))
plt.close()
print("Saved fig18_cjk_token_efficiency.png")

print("="*70)
print("ALL FIGURES AND ANALYSES COMPLETED SUCCESSFULLY!")
print("="*70)
