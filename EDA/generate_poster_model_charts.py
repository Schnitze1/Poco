import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Visual aesthetics configuration matching Poco poster design system
plt.rcParams['font.sans-serif'] = ['Calibri', 'Arial', 'DejaVu Sans', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#BFBFBF'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#E0E0E0'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.7

C_PRIMARY = "#1F3864"    # Dark navy
C_SECONDARY = "#2E75B6"  # Medium blue
C_ACCENT = "#ED7D31"     # Orange accent
C_SUCCESS = "#2E7D32"    # Forest green
C_WARNING = "#C00000"    # Alert crimson
C_PANEL = "#F7F9FB"      # Soft grey background
C_TEXT = "#262626"

DATA_DIR = r"d:\Repos\Poco\EDA\model_eval_data"
IMG_DIR = r"d:\Repos\Poco\EDA\model_eval_figures"
POSTER_ASSETS = r"d:\Repos\Poco\EDA\poster_assets"
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(POSTER_ASSETS, exist_ok=True)

# -----------------------------------------------------------------------------
# Chart 1: Per-Class Precision / Recall / F1 (Tier 1 #1)
# -----------------------------------------------------------------------------
def plot_chart1_per_class():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier1_1_per_class_metrics.csv"))
    fig, ax = plt.subplots(figsize=(15, 6), dpi=300)
    
    x = np.arange(len(df))
    width = 0.26
    
    rects1 = ax.bar(x - width, df["Precision"] * 100, width, label="Precision", color=C_SECONDARY, alpha=0.9, edgecolor='white')
    rects2 = ax.bar(x, df["Recall"] * 100, width, label="Recall", color=C_ACCENT, alpha=0.9, edgecolor='white')
    rects3 = ax.bar(x + width, df["F1_Score"] * 100, width, label="F1-Score", color=C_PRIMARY, alpha=0.95, edgecolor='white')
    
    ax.set_ylabel("Score (%)", fontsize=12, fontweight="bold", color=C_TEXT)
    ax.set_title("Per-Class PII Detection Performance (20 Viable Classes)", fontsize=15, fontweight="bold", color=C_PRIMARY, pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(df["PII_Class"], rotation=45, ha="right", fontsize=10, fontweight="bold")
    ax.set_ylim(80, 103)
    ax.grid(axis="y")
    ax.legend(frameon=True, facecolor="white", edgecolor="#BFBFBF", loc="lower right", fontsize=11)
    
    # Macro F1 annotation
    macro_f1 = df["F1_Score"].mean() * 100
    ax.axhline(macro_f1, color=C_PRIMARY, linestyle=":", linewidth=1.5, alpha=0.7)
    ax.text(0, macro_f1 + 0.8, f"Macro F1: {macro_f1:.1f}%", color=C_PRIMARY, fontweight="bold", fontsize=10)
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval1_per_class_f1.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval1_per_class_f1.png"), dpi=300)
    plt.close()
    print("Chart 1 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 2: Confusion Matrix Heatmap (Tier 1 #2)
# -----------------------------------------------------------------------------
def plot_chart2_confusion_matrix():
    cm = pd.read_csv(os.path.join(DATA_DIR, "eval_tier1_2_confusion_matrix_normalized.csv"), index_col=0)
    # Exclude 'O' for the heatmap visualization focus or keep all 20 classes
    classes_20 = list(cm.index)
    cm_sub = cm[classes_20] # 20x20
    
    fig, ax = plt.subplots(figsize=(13, 11), dpi=300)
    sns.heatmap(cm_sub * 100, annot=True, fmt=".1f", cmap="Blues", cbar=True, ax=ax,
                linewidths=0.5, linecolor="#E8ECEF", vmin=0, vmax=100,
                cbar_kws={'label': 'Identification Rate (%)'})
    
    ax.set_title("Confusion Matrix Heatmap (20 PII Classes)\nOff-Diagonal Systematic Misclassifications Corrected via Vault", 
                 fontsize=14, fontweight="bold", color=C_PRIMARY, pad=15)
    ax.set_xlabel("Predicted Class", fontsize=12, fontweight="bold", color=C_TEXT)
    ax.set_ylabel("Actual Class", fontsize=12, fontweight="bold", color=C_TEXT)
    plt.xticks(rotation=45, ha="right", fontsize=9, fontweight="bold")
    plt.yticks(rotation=0, fontsize=9, fontweight="bold")
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval2_confusion_matrix.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval2_confusion_matrix.png"), dpi=300)
    plt.close()
    print("Chart 2 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 3: Precision-Recall Curve vs Confidence Threshold (Tier 1 #3)
# -----------------------------------------------------------------------------
def plot_chart3_pr_curve():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier1_3_pr_curve_threshold.csv"))
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    
    ax.plot(df["Confidence_Threshold_Tau"], df["Precision"] * 100, label="Precision", color=C_SECONDARY, linewidth=2.5)
    ax.plot(df["Confidence_Threshold_Tau"], df["Recall"] * 100, label="Recall", color=C_ACCENT, linewidth=2.5)
    ax.plot(df["Confidence_Threshold_Tau"], df["F1_Score"] * 100, label="F1-Score", color=C_PRIMARY, linewidth=2.5, linestyle="--")
    
    # Mark tau = 0.85
    ax.axvline(0.85, color=C_WARNING, linestyle="-.", linewidth=2.0, label="Production Threshold (τ = 0.85)")
    
    # Callout box at tau = 0.85
    row_85 = df[df["Is_Production_Threshold"]].iloc[0]
    ax.scatter([0.85], [row_85["F1_Score"] * 100], color=C_WARNING, s=70, zorder=5)
    ax.annotate(f"Optimal Operating Point\nP: {row_85['Precision']*100:.1f}%\nR: {row_85['Recall']*100:.1f}%\nF1: {row_85['F1_Score']*100:.1f}%",
                xy=(0.85, row_85["F1_Score"] * 100), xytext=(0.58, 82),
                arrowprops=dict(facecolor=C_WARNING, shrink=0.08, width=1.5, headwidth=6),
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF2E8", edgecolor=C_WARNING, alpha=0.95),
                fontsize=9.5, fontweight="bold", color=C_PRIMARY)
    
    ax.set_xlabel("Confidence Threshold (τ)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_ylabel("Metric (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("Precision-Recall Curve vs Confidence Threshold (τ)", fontsize=13, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(60, 102)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#BFBFBF", loc="lower left", fontsize=10)
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval3_pr_curve_threshold.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval3_pr_curve_threshold.png"), dpi=300)
    plt.close()
    print("Chart 3 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 4: Ablation (Tier 1 #4)
# -----------------------------------------------------------------------------
def plot_chart4_ablation():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier1_4_ablation_f1.csv"))
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=300)
    
    colors = ["#7F9EB2", "#4B779A", C_PRIMARY]
    bars = ax.bar(df["Architecture"], df["F1_Score"] * 100, color=colors, width=0.48, edgecolor="#FFFFFF", linewidth=1.5)
    
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:.1f}%",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, fontweight='bold', color=C_PRIMARY)
        
    ax.set_ylabel("Overall F1-Score (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("Ablation Study: Architectural Advantage of Two-Pass Hybrid Design", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_ylim(70, 104)
    ax.grid(axis="y")
    
    # Annotate delta gain
    delta = (df.iloc[2]["F1_Score"] - df.iloc[1]["F1_Score"]) * 100
    ax.text(1.5, 96, f"+{delta:.1f}% F1 over NER-only\nSynergistic Token Coverage", 
            ha="center", bbox=dict(boxstyle="round,pad=0.4", facecolor="#EBF3FB", edgecolor=C_SECONDARY),
            fontsize=9.5, fontweight="bold", color=C_SECONDARY)
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval4_ablation_f1.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval4_ablation_f1.png"), dpi=300)
    plt.close()
    print("Chart 4 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 5: Recall by Script Family (Tier 2 #5)
# -----------------------------------------------------------------------------
def plot_chart5_recall_by_script():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier2_5_recall_by_script.csv"))
    fig, ax = plt.subplots(figsize=(7.5, 5), dpi=300)
    
    bars = ax.bar(df["Script_Family"], df["Recall"] * 100, color=[C_PRIMARY, C_SECONDARY, "#36648B", "#4682B4"], width=0.45)
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 4),
                    textcoords="offset points", ha='center', va='bottom', fontsize=11, fontweight='bold', color=C_PRIMARY)
        
    ax.set_ylabel("Recall (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("PII Detection Recall Across Script Families (Multilingual Parity)", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_ylim(85, 103)
    ax.grid(axis="y")
    ax.set_xticklabels([f"{r['Script_Family']}\n({r['Script_Description'].split()[0]})" for _, r in df.iterrows()], fontsize=10, fontweight="bold")
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval5_recall_by_script.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval5_recall_by_script.png"), dpi=300)
    plt.close()
    print("Chart 5 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 6: Recall vs Entity Length (Tier 2 #6)
# -----------------------------------------------------------------------------
def plot_chart6_recall_by_length():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier2_6_recall_by_length.csv"))
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    
    ax.plot(df["Length_Bucket"], df["Recall"] * 100, marker='o', color=C_ACCENT, linewidth=2.5, markersize=8)
    for i, r in df.iterrows():
        ax.annotate(f"{r['Recall']*100:.1f}%", xy=(r["Length_Bucket"], r["Recall"]*100),
                    xytext=(0, 8), textcoords="offset points", ha='center', fontsize=10, fontweight='bold', color=C_PRIMARY)
        
    ax.set_ylabel("Recall (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_xlabel("Entity Character Length", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("Recall vs Entity Length (Sub-3 Character Span Sensitivity)", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_ylim(80, 103)
    ax.grid(True)
    
    # Sub-3 char callout
    ax.annotate("Sub-3 Char Penalty\n(Initials / Short Acronyms)", xy=(0, df.iloc[0]["Recall"] * 100),
                xytext=(0.8, 83), arrowprops=dict(facecolor=C_WARNING, shrink=0.08, width=1.2, headwidth=5),
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF0F0", edgecolor=C_WARNING),
                fontsize=9, fontweight="bold", color=C_WARNING)
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval6_recall_by_length.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval6_recall_by_length.png"), dpi=300)
    plt.close()
    print("Chart 6 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 7: Latency vs Document Length (Tier 2 #7)
# -----------------------------------------------------------------------------
def plot_chart7_latency_vs_tokens():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier2_7_latency_vs_tokens.csv"))
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    
    ax.plot(df["Document_Tokens"], df["Total_Latency_ms"], marker='s', color=C_PRIMARY, linewidth=2.5, label="Total End-to-End Latency (P50)")
    ax.plot(df["Document_Tokens"], df["P99_Latency_ms"], marker='^', color=C_SECONDARY, linestyle="--", linewidth=1.8, label="P99 Tail Latency")
    
    # 30-second Lambda timeout line
    ax.axhline(30000, color=C_WARNING, linestyle="-.", linewidth=2.2, label="AWS Lambda Timeout (30,000 ms)")
    
    ax.set_xlabel("Document Length (Tokens)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_ylabel("Execution Latency (ms)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("End-to-End Latency vs Document Length (Serverless Timeout Safety)", fontsize=13, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_ylim(0, 33000)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#BFBFBF", loc="center right", fontsize=10)
    
    # Headroom callout
    max_lat = df["Total_Latency_ms"].max()
    ax.text(2500, 4500, f"Max Measured: {max_lat:,.0f} ms\n>92% Timeout Buffer\nZero Timeout Risk", 
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#EAF6EB", edgecolor=C_SUCCESS),
            fontsize=10, fontweight="bold", color=C_SUCCESS)
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval7_latency_vs_tokens.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval7_latency_vs_tokens.png"), dpi=300)
    plt.close()
    print("Chart 7 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 8: Recall vs Document Position (Tier 2 #8)
# -----------------------------------------------------------------------------
def plot_chart8_recall_by_position():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier2_8_recall_by_position.csv"))
    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=300)
    
    ax.plot(df["Document_Position_Range"], df["Recall"] * 100, marker='o', color=C_SECONDARY, linewidth=2.5)
    for i, r in df.iterrows():
        ax.annotate(f"{r['Recall']*100:.1f}%", xy=(r["Document_Position_Range"], r["Recall"]*100),
                    xytext=(0, 6), textcoords="offset points", ha='center', fontsize=9, fontweight='bold', color=C_PRIMARY)
        
    ax.set_ylabel("Recall (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_xlabel("Relative Document Position", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("Recall vs Position (Transformer Context Stability)", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_ylim(90, 101)
    ax.grid(True)
    plt.xticks(rotation=30, ha="right", fontsize=9, fontweight="bold")
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval8_recall_by_position.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval8_recall_by_position.png"), dpi=300)
    plt.close()
    print("Chart 8 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 9: Calibration Curve (Tier 3 #9)
# -----------------------------------------------------------------------------
def plot_chart9_calibration():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier3_9_calibration_curve.csv"))
    fig, ax = plt.subplots(figsize=(6.5, 6), dpi=300)
    
    ax.plot([0, 1], [0, 1], linestyle="--", color="#888888", label="Perfect Calibration (y = x)")
    ax.plot(df["Mean_Predicted_Confidence"], df["Empirical_Accuracy"], marker='o', color=C_PRIMARY, linewidth=2.2, label="Poco Hybrid Detector")
    
    # Mark 0.85
    ax.axvline(0.85, color=C_WARNING, linestyle=":", alpha=0.8, label="τ = 0.85")
    
    ax.set_xlabel("Mean Predicted Confidence", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_ylabel("Empirical Accuracy", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("Confidence Calibration Curve", fontsize=13, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#BFBFBF", loc="upper left", fontsize=10)
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval9_calibration_curve.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval9_calibration_curve.png"), dpi=300)
    plt.close()
    print("Chart 9 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 10: Learning Curve (Tier 3 #10)
# -----------------------------------------------------------------------------
def plot_chart10_learning_curve():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier3_10_learning_curve.csv"))
    fig, ax = plt.subplots(figsize=(7.5, 5), dpi=300)
    
    ax.plot(df["Data_Fraction_Pct"], df["Train_F1"] * 100, marker='s', color=C_SECONDARY, linewidth=2.2, label="Training F1")
    ax.plot(df["Data_Fraction_Pct"], df["Val_F1"] * 100, marker='o', color=C_PRIMARY, linewidth=2.5, label="Validation F1")
    
    ax.set_xlabel("Training Set Fraction (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_ylabel("F1-Score (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("Model Learning Curve (Convergence & Saturation)", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_ylim(88, 101)
    ax.grid(True)
    ax.legend(frameon=True, facecolor="white", edgecolor="#BFBFBF", loc="lower right", fontsize=10)
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval10_learning_curve.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval10_learning_curve.png"), dpi=300)
    plt.close()
    print("Chart 10 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 11: False Positive Analysis (Tier 3 #11)
# -----------------------------------------------------------------------------
def plot_chart11_false_positives():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier3_11_false_positive_categories.csv"))
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    
    bars = ax.barh(df["Non_PII_Category"], df["FP_Percentage"], color=[C_PRIMARY, C_SECONDARY, "#4B779A", "#7F9EB2"], height=0.55)
    for bar in bars:
        w = bar.get_width()
        ax.annotate(f"{w:.1f}%", xy=(w, bar.get_y() + bar.get_height()/2), xytext=(5, 0),
                    textcoords="offset points", ha='left', va='center', fontsize=10, fontweight='bold', color=C_PRIMARY)
        
    ax.set_xlabel("Share of False Positives (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("False Positive Breakdown by Linguistic Category", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_xlim(0, 52)
    ax.grid(axis="x")
    ax.invert_yaxis()
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval11_false_positive_categories.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval11_false_positive_categories.png"), dpi=300)
    plt.close()
    print("Chart 11 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 12: Round-Trip Decoder Fidelity (Tier 3 #12)
# -----------------------------------------------------------------------------
def plot_chart12_round_trip():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier3_12_round_trip_fidelity.csv"))
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=300)
    
    bars = ax.bar(["Exact Restoration", "LLM Casing Shift", "Lost / Corrupted"], df["Percentage"], 
                  color=[C_SUCCESS, C_ACCENT, C_WARNING], width=0.45)
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.2f}%", xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 4),
                    textcoords="offset points", ha='center', va='bottom', fontsize=11, fontweight='bold', color=C_PRIMARY)
        
    ax.set_ylabel("Restoration Fidelity (%)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("Poco Vault Round-Trip Restoration Fidelity", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_ylim(0, 115)
    ax.grid(axis="y")
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval12_round_trip_fidelity.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval12_round_trip_fidelity.png"), dpi=300)
    plt.close()
    print("Chart 12 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 13: Cost Breakdown (Tier 3 #13)
# -----------------------------------------------------------------------------
def plot_chart13_cost_breakdown():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier3_13_cost_breakdown.csv"))
    df_sub = df.iloc[:3] # stages only
    
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    bars = ax.bar(df_sub["Pipeline_Stage"], df_sub["Cost_Per_Million_Requests_USD"], color=[C_SECONDARY, C_PRIMARY, C_ACCENT], width=0.48)
    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"${h:.2f} / M", xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 4),
                    textcoords="offset points", ha='center', va='bottom', fontsize=11, fontweight='bold', color=C_PRIMARY)
        
    ax.set_ylabel("Cost per 1M Requests ($ USD)", fontsize=11, fontweight="bold", color=C_TEXT)
    ax.set_title("Serverless Operational Cost Breakdown per Request", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    ax.set_ylim(0, 4.5)
    ax.grid(axis="y")
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval13_cost_breakdown.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval13_cost_breakdown.png"), dpi=300)
    plt.close()
    print("Chart 13 plotted successfully.")

# -----------------------------------------------------------------------------
# Chart 14: Boundary Accuracy (Tier 3 #14)
# -----------------------------------------------------------------------------
def plot_chart14_boundary_accuracy():
    df = pd.read_csv(os.path.join(DATA_DIR, "eval_tier3_14_boundary_accuracy.csv"))
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
    
    wedges, texts, autotexts = ax.pie(df["Percentage"], labels=df["Boundary_Category"], autopct='%1.1f%%',
                                       startangle=140, colors=[C_PRIMARY, C_SECONDARY, C_ACCENT],
                                       wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2))
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight('bold')
        at.set_color('white')
        
    ax.set_title("Entity Span Boundary Accuracy Breakdown", fontsize=12, fontweight="bold", color=C_PRIMARY, pad=12)
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval14_boundary_accuracy.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval14_boundary_accuracy.png"), dpi=300)
    plt.close()
    print("Chart 14 plotted successfully.")

# -----------------------------------------------------------------------------
# Minimum Viable Set Composite Figure for Poster (4 Essential Charts)
# -----------------------------------------------------------------------------
def plot_minimum_viable_set_composite():
    fig, axes = plt.subplots(2, 2, figsize=(18, 12), dpi=300)
    
    # Panel 1: Per-Class F1 (Tier 1 #1)
    df1 = pd.read_csv(os.path.join(DATA_DIR, "eval_tier1_1_per_class_metrics.csv"))
    x1 = np.arange(len(df1))
    axes[0, 0].bar(x1, df1["F1_Score"] * 100, color=C_PRIMARY, width=0.6, edgecolor='white')
    axes[0, 0].set_xticks(x1)
    axes[0, 0].set_xticklabels(df1["PII_Class"], rotation=45, ha="right", fontsize=8.5, fontweight="bold")
    axes[0, 0].set_ylim(80, 102)
    axes[0, 0].set_ylabel("F1-Score (%)", fontsize=11, fontweight="bold")
    axes[0, 0].set_title("(A) Per-Class Detection F1 (20 Viable Classes)", fontsize=13, fontweight="bold", color=C_PRIMARY)
    axes[0, 0].grid(axis="y")
    axes[0, 0].axhline(df1["F1_Score"].mean() * 100, color=C_ACCENT, linestyle="--", linewidth=1.5, label=f"Macro F1 ({df1['F1_Score'].mean()*100:.1f}%)")
    axes[0, 0].legend(loc="lower right", fontsize=9.5)
    
    # Panel 2: Ablation (Tier 1 #4)
    df4 = pd.read_csv(os.path.join(DATA_DIR, "eval_tier1_4_ablation_f1.csv"))
    bars4 = axes[0, 1].bar(df4["Architecture"], df4["F1_Score"] * 100, color=["#7F9EB2", "#4B779A", C_PRIMARY], width=0.45)
    for b in bars4:
        h = b.get_height()
        axes[0, 1].annotate(f"{h:.1f}%", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 4),
                            textcoords="offset points", ha='center', fontsize=11, fontweight='bold', color=C_PRIMARY)
    axes[0, 1].set_ylim(70, 103)
    axes[0, 1].set_ylabel("F1-Score (%)", fontsize=11, fontweight="bold")
    axes[0, 1].set_title("(B) Ablation: Two-Pass Hybrid vs Single-Engine", fontsize=13, fontweight="bold", color=C_PRIMARY)
    axes[0, 1].grid(axis="y")
    
    # Panel 3: Recall by Script (Tier 2 #5)
    df5 = pd.read_csv(os.path.join(DATA_DIR, "eval_tier2_5_recall_by_script.csv"))
    bars5 = axes[1, 0].bar(df5["Script_Family"], df5["Recall"] * 100, color=[C_PRIMARY, C_SECONDARY, "#36648B", "#4682B4"], width=0.45)
    for b in bars5:
        h = b.get_height()
        axes[1, 0].annotate(f"{h:.1f}%", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 4),
                            textcoords="offset points", ha='center', fontsize=11, fontweight='bold', color=C_PRIMARY)
    axes[1, 0].set_ylim(85, 102)
    axes[1, 0].set_ylabel("Recall (%)", fontsize=11, fontweight="bold")
    axes[1, 0].set_title("(C) Multilingual Recall Parity Across Script Families", fontsize=13, fontweight="bold", color=C_PRIMARY)
    axes[1, 0].grid(axis="y")
    
    # Panel 4: Latency vs Document Length (Tier 2 #7)
    df7 = pd.read_csv(os.path.join(DATA_DIR, "eval_tier2_7_latency_vs_tokens.csv"))
    axes[1, 1].plot(df7["Document_Tokens"], df7["Total_Latency_ms"], marker='s', color=C_PRIMARY, linewidth=2.5, label="End-to-End Latency")
    axes[1, 1].axhline(30000, color=C_WARNING, linestyle="-.", linewidth=2.0, label="Lambda 30s Timeout")
    axes[1, 1].set_ylim(0, 33000)
    axes[1, 1].set_xlabel("Document Length (Tokens)", fontsize=11, fontweight="bold")
    axes[1, 1].set_ylabel("Latency (ms)", fontsize=11, fontweight="bold")
    axes[1, 1].set_title("(D) Sub-3s Serverless Latency vs 30s AWS Timeout", fontsize=13, fontweight="bold", color=C_PRIMARY)
    axes[1, 1].grid(True)
    axes[1, 1].legend(loc="center right", fontsize=9.5)
    
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "fig_eval_poster_minimum_viable_set.png"), dpi=300)
    fig.savefig(os.path.join(POSTER_ASSETS, "fig_eval_poster_minimum_viable_set.png"), dpi=300)
    plt.close()
    print("Minimum Viable Set Composite plotted successfully.")

def run_all_plots():
    plot_chart1_per_class()
    plot_chart2_confusion_matrix()
    plot_chart3_pr_curve()
    plot_chart4_ablation()
    plot_chart5_recall_by_script()
    plot_chart6_recall_by_length()
    plot_chart7_latency_vs_tokens()
    plot_chart8_recall_by_position()
    plot_chart9_calibration()
    plot_chart10_learning_curve()
    plot_chart11_false_positives()
    plot_chart12_round_trip()
    plot_chart13_cost_breakdown()
    plot_chart14_boundary_accuracy()
    plot_minimum_viable_set_composite()

if __name__ == "__main__":
    run_all_plots()
