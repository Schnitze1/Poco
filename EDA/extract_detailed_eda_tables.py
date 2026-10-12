import json
import pandas as pd
import numpy as np

df = pd.read_csv(r"d:\Repos\Poco\EDA\eda_sample_50k.csv")

print("--- SHAPE & DTYPES ---")
print("Shape:", df.shape)
print("Data Types:")
print(df.dtypes)

print("\n--- DETAILED SUMMARY STATISTICS (df.describe()) ---")
desc = df.describe().T
desc["skewness"] = df.skew(numeric_only=True)
desc["kurtosis"] = df.kurtosis(numeric_only=True)
print(desc[["count", "mean", "std", "min", "25%", "50%", "75%", "max", "skewness", "kurtosis"]].to_string())

print("\n--- OUTLIERS BREAKDOWN: UPPER, LOWER, BOTH ---")
num_cols = ["char_length", "word_count", "token_count", "entity_count", "pii_token_count", 
            "pii_token_ratio", "pii_char_length", "pii_char_ratio", "avg_entity_char_len", "unique_entity_types"]

for col in num_cols:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    low_out = (df[col] < lower_bound).sum()
    up_out = (df[col] > upper_bound).sum()
    min_val = df[col].min()
    max_val = df[col].max()
    print(f"{col:20s}: Min={min_val:8.2f}, Max={max_val:8.2f}, Q1={q1:8.2f}, Q3={q3:8.2f}, IQR={iqr:8.2f} | Lower Threshold={lower_bound:8.2f} (Low Outliers: {low_out:5d}) | Upper Threshold={upper_bound:8.2f} (Up Outliers: {up_out:5d})")

print("\n--- CORRELATION MATRIX (PEARSON & SPEARMAN) ---")
p_corr = df[num_cols].corr(method="pearson")
s_corr = df[num_cols].corr(method="spearman")

print("\nPearson Correlation with Target 'entity_count':")
print(p_corr["entity_count"].sort_values(ascending=False))

print("\nSpearman Correlation with Target 'entity_count':")
print(s_corr["entity_count"].sort_values(ascending=False))

print("\nPearson Correlation with Target 'pii_token_ratio' (Density):")
print(p_corr["pii_token_ratio"].sort_values(ascending=False))

print("\n--- TOP CORRELATED PAIRS (Multicollinearity / Near-Collinear) ---")
corr_unstacked = p_corr.abs().unstack()
corr_unstacked = corr_unstacked[corr_unstacked < 1.0].sort_values(ascending=False)
seen = set()
for (v1, v2), val in corr_unstacked.items():
    pair = tuple(sorted([v1, v2]))
    if pair not in seen:
        seen.add(pair)
        print(f"{v1:20s} & {v2:20s}: Pearson r = {p_corr.loc[v1, v2]:.4f} (Abs: {val:.4f})")
    if len(seen) >= 15:
        break

print("\n--- NEGATIVE RELATIONSHIPS ---")
neg_pairs = []
for col1 in num_cols:
    for col2 in num_cols:
        if col1 < col2:
            r = p_corr.loc[col1, col2]
            if r < 0:
                neg_pairs.append((col1, col2, r))
neg_pairs.sort(key=lambda x: x[2])
for col1, col2, r in neg_pairs:
    print(f"{col1:20s} & {col2:20s}: Pearson r = {r:.4f}")

print("\n--- TEMPERATURE-SOLAR-LOAD ANALOGOUS CLUSTER ---")
# Tripartite cluster: char_length, token_count, entity_count
tri_corr = df[["char_length", "token_count", "entity_count", "pii_token_ratio"]].corr()
print(tri_corr)
