import os
import json
import time
import orjson
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter, defaultdict
from scipy import stats
import shutil

# Set aesthetic styling
sns.set_theme(style="whitegrid", font="sans-serif")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

EDA_DIR = r"d:\Repos\Poco\EDA"
ARTIFACT_DIR = r"C:\Users\Shadd\.gemini\antigravity-ide\brain\0f1bd67a-e6ce-4dc6-b535-b908b888cb0b"

print("Loading 100k extracted dataframe...")
df = pd.read_csv(os.path.join(EDA_DIR, "eda_refined_100k.csv"))

print("Loading label viability table...")
label_viability_df = pd.read_csv(os.path.join(EDA_DIR, "label_viability_table.csv"))

print("Computing script token efficiencies...")
script_eff = df.groupby("script")["tokens_per_char"]
hangul_eff = df[df["script"] == "Hang"]["tokens_per_char"].values
jpan_eff = df[df["script"] == "Jpan"]["tokens_per_char"].values
hans_eff = df[df["script"] == "Hans"]["tokens_per_char"].values
latn_eff = df[df["script"] == "Latn"]["tokens_per_char"].values

print(f"Hangul (Korean): Mean = {np.mean(hangul_eff):.4f}, Std = {np.std(hangul_eff):.4f}, N = {len(hangul_eff)}")
print(f"Japanese (Kana/Kanji): Mean = {np.mean(jpan_eff):.4f}, Std = {np.std(jpan_eff):.4f}, N = {len(jpan_eff)}")
print(f"Han (Chinese): Mean = {np.mean(hans_eff):.4f}, Std = {np.std(hans_eff):.4f}, N = {len(hans_eff)}")
print(f"Latin (English/SEA): Mean = {np.mean(latn_eff):.4f}, Std = {np.std(latn_eff):.4f}, N = {len(latn_eff)}")

# Statistical tests: Mann-Whitney U & Welch's t-test
t_hang, p_hang = stats.ttest_ind(hangul_eff, latn_eff, equal_var=False)
u_hang, p_hang_u = stats.mannwhitneyu(hangul_eff, latn_eff)

t_jp, p_jp = stats.ttest_ind(jpan_eff, latn_eff, equal_var=False)
u_jp, p_jp_u = stats.mannwhitneyu(jpan_eff, latn_eff)

t_zh, p_zh = stats.ttest_ind(hans_eff, latn_eff, equal_var=False)
u_zh, p_zh_u = stats.mannwhitneyu(hans_eff, latn_eff)

print("\n--- Script vs Latin Statistical Tests ---")
print(f"Hangul vs Latin: t = {t_hang:.2f}, p = {p_hang:.2e} | Mann-Whitney U = {u_hang:.2e}, p = {p_hang_u:.2e}")
print(f"Japanese vs Latin: t = {t_jp:.2f}, p = {p_jp:.2e} | Mann-Whitney U = {u_jp:.2e}, p = {p_jp_u:.2e}")
print(f"Chinese vs Latin: t = {t_zh:.2f}, p = {p_zh:.2e} | Mann-Whitney U = {u_zh:.2e}, p = {p_zh_u:.2e}")

# Build per-language entity table from data
print("\nRebuilding per-language entity distribution from stream...")
# We can stream lines again quickly or read privacy_mask counts
# Let's read from the jsonl stream for the top languages
import requests
url = "https://huggingface.co/datasets/woojin1069/pii-masking-openpii-1.5m/resolve/main/data/train.jsonl"
resp = requests.get(url, stream=True, timeout=60)
lang_entity_counter = defaultdict(Counter)

c = 0
for line in resp.iter_lines():
    if not line:
        continue
    row = orjson.loads(line)
    lang = row.get("language", "unknown")
    for s in row.get("privacy_mask", []):
        lang_entity_counter[lang][s.get("label", "UNKNOWN")] += 1
    c += 1
    if c >= 100_000:
        break

top_langs = ["ko", "ja", "zh", "en", "vi", "id", "ms", "tl"]
core_entities = ["GIVENNAME", "SURNAME", "DATE", "CITY", "STREET", "EMAIL", "TELEPHONENUM"]

chi_table = []
for l in top_langs:
    row_counts = [lang_entity_counter[l][e] for e in core_entities]
    chi_table.append(row_counts)

chi2_stat, p_val_chi2, dof, _ = stats.chi2_contingency(chi_table)
print(f"\nChi-Square Test of Independence (Language vs Entity Distribution):")
print(f"Chi2 = {chi2_stat:.2f}, dof = {dof}, p-value = {p_val_chi2:.2e}")

per_lang_df = pd.DataFrame(chi_table, index=top_langs, columns=core_entities)
per_lang_norm = per_lang_df.div(per_lang_df.sum(axis=1), axis=0) * 100
print("\n--- Per-Language Entity Composition (%) ---")
print(per_lang_norm.to_string())

per_lang_norm.to_csv(os.path.join(EDA_DIR, "per_language_entity_composition.csv"))

print("\n--- Generating Visualizations ---")

# Fig 1: Top 25 Labels with Viability Status
plt.figure(figsize=(12, 10))
sns.barplot(
    data=label_viability_df.head(25),
    x="Sample_Count_100k",
    y="Label",
    hue="Viability_Tier",
    dodge=False,
    palette={"Tier 1: Fully Trainable": "#2e7d32", "Tier 2: Marginal / Long-Tail": "#f57c00", "Tier 3: Unviable (<200 in 100k sample)": "#c62828"}
)
plt.title("Fig 1: PII Entity Distribution Across 100k Sample (Top 25 Labels by Viability)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Annotation Count (100k Sample)", fontsize=12)
plt.ylabel("PII Label", fontsize=12)
plt.legend(title="Training Viability", loc="lower right", fontsize=11)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig1_label_distribution.png"))
plt.close()
print("Saved fig1_label_distribution.png")

# Fig 2: All 42 Labels Log Scale with Decision Thresholds
plt.figure(figsize=(12, 11))
ax = sns.barplot(
    data=label_viability_df,
    x="Sample_Count_100k",
    y="Label",
    hue="Viability_Tier",
    dodge=False,
    palette={"Tier 1: Fully Trainable": "#2e7d32", "Tier 2: Marginal / Long-Tail": "#f57c00", "Tier 3: Unviable (<200 in 100k sample)": "#c62828"}
)
ax.set_xscale("log")
plt.axvline(2000, color="green", linestyle="--", linewidth=1.8, label="Trainable Threshold (≥2,000 in 100k / ≥32k in 1.5M)")
plt.axvline(200, color="red", linestyle=":", linewidth=1.8, label="Unviable Threshold (<200 in 100k / <3.2k in 1.5M)")
plt.title("Fig 2: Complete PII Entity Taxonomy (All 42 Labels — Log Scale Viability)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("Annotation Count in 100k Sample (Log Scale)", fontsize=12)
plt.ylabel("PII Label", fontsize=10)
plt.legend(loc="lower left", fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig2_label_log.png"))
plt.close()
print("Saved fig2_label_log.png")

# Fig 9: REPLACED with Per-Language Entity Composition Heatmap
plt.figure(figsize=(12, 7))
sns.heatmap(per_lang_norm, cmap="YlGnBu", annot=True, fmt=".1f", linewidths=0.5, cbar_kws={'label': '% Share of Core Entities in Language'})
plt.title("Fig 9: Per-Language Entity Composition Heatmap (% Distribution Across Core Entities)", fontsize=14, fontweight="bold", pad=12)
plt.xlabel("PII Entity Label", fontsize=12)
plt.ylabel("Language Code", fontsize=12)
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig9_missing_values_heatmap.png"))
plt.close()
print("Saved fig9_missing_values_heatmap.png (Per-Language Entity Distribution)")

# Fig 15: Multivariate Correlation Heatmap INCLUDING pii_token_count
corr_features = [
    "char_length", "word_count", "token_count", "entity_count",
    "pii_token_count", "pii_token_ratio", "pii_char_length",
    "pii_char_ratio", "avg_entity_char_len", "unique_entity_types"
]
corr_matrix = df[corr_features].corr(method="pearson")

plt.figure(figsize=(11, 9))
sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1,
            linewidths=0.5, cbar_kws={'label': 'Pearson Correlation (r)'})
plt.title("Fig 15: Multivariate Correlation Heatmap (Including pii_token_count)", fontsize=14, fontweight="bold", pad=12)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(EDA_DIR, "fig15_correlation_heatmap.png"))
plt.close()
print("Saved fig15_correlation_heatmap.png")

# Fig 18: Script Token Efficiency with exact means
script_means = {
    "Jpan (Japanese)": np.mean(jpan_eff),
    "Hang (Korean)": np.mean(hangul_eff),
    "Hans (Chinese)": np.mean(hans_eff),
    "Latn (Latin)": np.mean(latn_eff)
}
script_series = pd.Series(script_means).sort_values(ascending=False)

plt.figure(figsize=(10, 5))
ax = script_series.plot(kind="bar", color="#e65100", edgecolor="#bf360c")
plt.title("Fig 18: Subword Tokenizer Expansion (mBERT Tokens per Character) by Script", fontsize=14, fontweight="bold", pad=12)
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

# Copy all updated figures to artifact directory
for f in ["fig1_label_distribution.png", "fig2_label_log.png", "fig9_missing_values_heatmap.png", "fig15_correlation_heatmap.png", "fig18_cjk_token_efficiency.png"]:
    shutil.copy2(os.path.join(EDA_DIR, f), os.path.join(ARTIFACT_DIR, f))
print("Copied all updated figures to artifact directory!")

# Save stats bundle for reporting
summary_bundle = {
    "script_means": script_means,
    "stat_tests": {
        "hangul_vs_latin": {"t": float(t_hang), "p": float(p_hang), "u": float(u_hang), "p_u": float(p_hang_u)},
        "jpan_vs_latin": {"t": float(t_jp), "p": float(p_jp), "u": float(u_jp), "p_u": float(p_jp_u)},
        "hans_vs_latin": {"t": float(t_zh), "p": float(p_zh), "u": float(u_zh), "p_u": float(p_zh_u)},
        "chi2": {"stat": float(chi2_stat), "p": float(p_val_chi2), "dof": int(dof)}
    },
    "corr_entity_count": corr_matrix["entity_count"].to_dict()
}
with open(os.path.join(EDA_DIR, "refined_stats_bundle.json"), "w", encoding="utf-8") as f:
    json.dump(summary_bundle, f, indent=2)

print("="*70)
print("SUCCESSFULLY GENERATED ALL REFINED TABLES, TESTS, AND CHARTS!")
print("="*70)
