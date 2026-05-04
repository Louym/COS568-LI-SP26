#!/usr/bin/env python3
"""
Comprehensive visualization for Milestone 1.
Generates plots showing ALL results (all configs, all 3 runs).
"""

import os
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results"
PLOTS_DIR   = Path(__file__).parent.parent / "plots"
PLOTS_DIR.mkdir(exist_ok=True)

DATASETS = ["fb_100M_public_uint64", "books_100M_public_uint64", "osmc_100M_public_uint64"]
DATASET_LABELS = {
    "fb_100M_public_uint64":    "FB (100M)",
    "books_100M_public_uint64": "Books (100M)",
    "osmc_100M_public_uint64":  "OSM-C (100M)",
}

# Colour per index family
FAMILY_COLOR = {"BTree": "#FF9800", "LIPP": "#2196F3", "DynamicPGM": "#4CAF50"}
FAMILY_EDGE  = {"BTree": "#E65100", "LIPP": "#0D47A1", "DynamicPGM": "#1B5E20"}

def config_label(row):
    """Short label for a row's hyperparameter config."""
    if pd.isna(row.get("search_method")) or str(row.get("search_method")) == "nan":
        return row["index_name"]
    sm = str(row["search_method"])
    abbrev = {"LinearSearch": "LS", "BinarySearch": "BS",
              "InterpolationSearch": "IS", "LinearAVX": "AVX",
              "ExponentialSearch": "ES"}
    sm_short = abbrev.get(sm, sm[:3])
    val = str(int(float(row["value"]))) if not pd.isna(row.get("value")) else ""
    return f"{row['index_name']}\n{sm_short},{val}"

# ─────────────────────────────────────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────────────────────────────────────

def load_lookup_only(dataset):
    fname = RESULTS_DIR / f"{dataset}_ops_2M_0.000000rq_0.500000nl_0.000000i_results_table.csv"
    df = pd.read_csv(fname)
    run_cols = ["lookup_throughput_mops1","lookup_throughput_mops2","lookup_throughput_mops3"]
    df["mean"] = df[run_cols].mean(axis=1)
    df["std"]  = df[run_cols].std(axis=1)
    df["runs"] = df[run_cols].values.tolist()
    df["label"] = df.apply(config_label, axis=1)
    return df, run_cols

def load_insert_lookup(dataset):
    fname = RESULTS_DIR / f"{dataset}_ops_2M_0.000000rq_0.500000nl_0.500000i_0m_results_table.csv"
    df = pd.read_csv(fname)
    ins_cols = ["insert_throughput_mops1","insert_throughput_mops2","insert_throughput_mops3"]
    lkp_cols = ["lookup_throughput_mops1","lookup_throughput_mops2","lookup_throughput_mops3"]
    df["ins_mean"] = df[ins_cols].mean(axis=1)
    df["ins_std"]  = df[ins_cols].std(axis=1)
    df["ins_runs"] = df[ins_cols].values.tolist()
    df["lkp_mean"] = df[lkp_cols].mean(axis=1)
    df["lkp_std"]  = df[lkp_cols].std(axis=1)
    df["lkp_runs"] = df[lkp_cols].values.tolist()
    df["label"] = df.apply(config_label, axis=1)
    return df

def load_mixed(dataset, insert_ratio):
    fname = RESULTS_DIR / f"{dataset}_ops_2M_0.000000rq_0.500000nl_{insert_ratio:.6f}i_0m_mix_results_table.csv"
    df = pd.read_csv(fname)
    run_cols = ["mixed_throughput_mops1","mixed_throughput_mops2","mixed_throughput_mops3"]
    df["mean"] = df[run_cols].mean(axis=1)
    df["std"]  = df[run_cols].std(axis=1)
    df["runs"] = df[run_cols].values.tolist()
    df["label"] = df.apply(config_label, axis=1)
    return df, run_cols

# ─────────────────────────────────────────────────────────────────────────────
# Core plotting helper: one panel showing ALL configs with scatter dots
# ─────────────────────────────────────────────────────────────────────────────

def draw_all_configs_panel(ax, df, mean_col, run_cols, ylabel, title, ylim=None, legend=True):
    """Draw one axes panel: one bar per config, coloured by index family, dots for each run."""
    xs, means, stds, colors, edges, labels, run_vals = [], [], [], [], [], [], []

    for i, (_, row) in enumerate(df.iterrows()):
        family = row["index_name"]
        xs.append(i)
        means.append(row[mean_col] if mean_col in row else row["mean"])
        stds.append(row["std"] if "std" in df.columns else 0)
        colors.append(FAMILY_COLOR[family])
        edges.append(FAMILY_EDGE[family])
        labels.append(row["label"])
        run_vals.append(row["runs"] if "runs" in df.columns
                        else [row[c] for c in run_cols])

    bars = ax.bar(xs, means, color=colors, edgecolor=edges, linewidth=0.8,
                  width=0.6, zorder=2)

    # Overlay individual run dots
    for i, runs in zip(xs, run_vals):
        jitter = np.linspace(-0.12, 0.12, len(runs))
        for j, v in zip(jitter, runs):
            ax.scatter(i + j, v, color="white", edgecolors=edges[i],
                       s=20, linewidths=0.8, zorder=3)

    ax.set_xticks(xs)
    ax.set_xticklabels(labels, fontsize=6)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    if ylim:
        ax.set_ylim(ylim)

    # Vertical separators between index families
    prev_family = None
    for i, (_, row) in enumerate(df.iterrows()):
        if prev_family and row["index_name"] != prev_family:
            ax.axvline(i - 0.5, color='grey', linestyle='--', linewidth=0.6, alpha=0.5)
        prev_family = row["index_name"]

    if legend:
        patches = [mpatches.Patch(facecolor=FAMILY_COLOR[f], edgecolor=FAMILY_EDGE[f], label=f)
                   for f in ["LIPP","BTree","DynamicPGM"]]
        ax.legend(handles=patches, fontsize=8, loc='upper right')

# ─────────────────────────────────────────────────────────────────────────────
# Figure 1: Lookup-only — all configs, all 3 datasets
# ─────────────────────────────────────────────────────────────────────────────

def fig_lookup_only():
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5), sharey=False)
    for ax, ds in zip(axes, DATASETS):
        df, run_cols = load_lookup_only(ds)
        draw_all_configs_panel(
            ax, df, "mean", run_cols,
            "Throughput (Mops/s)",
            DATASET_LABELS[ds],
            legend=(ds == DATASETS[0])
        )
    fig.suptitle("Lookup-Only Workload: All Configurations\n"
                 "(50% positive lookups, 50% negative lookups; white dots = individual runs)",
                 fontsize=11, fontweight='bold')
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "fig1_lookup_only_all.pdf", bbox_inches='tight')
    fig.savefig(PLOTS_DIR / "fig1_lookup_only_all.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Saved fig1_lookup_only_all")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 2: Insert throughput — all configs, all 3 datasets
# ─────────────────────────────────────────────────────────────────────────────

def fig_insert_throughput():
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ax, ds in zip(axes, DATASETS):
        df = load_insert_lookup(ds)
        df2 = df.copy()
        df2["mean"] = df2["ins_mean"]
        df2["std"]  = df2["ins_std"]
        df2["runs"] = df2["ins_runs"]
        draw_all_configs_panel(
            ax, df2, "mean", [],
            "Insert Throughput (Mops/s)",
            DATASET_LABELS[ds],
            legend=(ds == DATASETS[0])
        )
    fig.suptitle("Insert Throughput: All Configurations\n"
                 "(50% Insert / 50% Lookup workload; white dots = individual runs)",
                 fontsize=11, fontweight='bold')
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "fig2_insert_all.pdf", bbox_inches='tight')
    fig.savefig(PLOTS_DIR / "fig2_insert_all.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Saved fig2_insert_all")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 3: Post-insert lookup — all configs, all 3 datasets
# ─────────────────────────────────────────────────────────────────────────────

def fig_lookup_after_insert():
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ax, ds in zip(axes, DATASETS):
        df = load_insert_lookup(ds)
        df2 = df.copy()
        df2["mean"] = df2["lkp_mean"]
        df2["std"]  = df2["lkp_std"]
        df2["runs"] = df2["lkp_runs"]
        draw_all_configs_panel(
            ax, df2, "mean", [],
            "Lookup Throughput (Mops/s)",
            DATASET_LABELS[ds],
            legend=(ds == DATASETS[0])
        )
    fig.suptitle("Lookup Throughput After Insertions: All Configurations\n"
                 "(50% Insert / 50% Lookup workload; white dots = individual runs)",
                 fontsize=11, fontweight='bold')
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "fig3_lookup_after_insert_all.pdf", bbox_inches='tight')
    fig.savefig(PLOTS_DIR / "fig3_lookup_after_insert_all.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Saved fig3_lookup_after_insert_all")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 4: Mixed 10% insert — all configs, all 3 datasets
# ─────────────────────────────────────────────────────────────────────────────

def fig_mixed_10():
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ax, ds in zip(axes, DATASETS):
        df, run_cols = load_mixed(ds, 0.1)
        draw_all_configs_panel(
            ax, df, "mean", run_cols,
            "Throughput (Mops/s)",
            DATASET_LABELS[ds],
            legend=(ds == DATASETS[0])
        )
    fig.suptitle("Mixed Workload (10% Insert, 90% Lookup): All Configurations\n"
                 "(white dots = individual runs)",
                 fontsize=11, fontweight='bold')
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "fig4_mixed10_all.pdf", bbox_inches='tight')
    fig.savefig(PLOTS_DIR / "fig4_mixed10_all.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Saved fig4_mixed10_all")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 5: Mixed 90% insert — all configs, all 3 datasets
# ─────────────────────────────────────────────────────────────────────────────

def fig_mixed_90():
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ax, ds in zip(axes, DATASETS):
        df, run_cols = load_mixed(ds, 0.9)
        draw_all_configs_panel(
            ax, df, "mean", run_cols,
            "Throughput (Mops/s)",
            DATASET_LABELS[ds],
            legend=(ds == DATASETS[0])
        )
    fig.suptitle("Mixed Workload (90% Insert, 10% Lookup): All Configurations\n"
                 "(white dots = individual runs)",
                 fontsize=11, fontweight='bold')
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "fig5_mixed90_all.pdf", bbox_inches='tight')
    fig.savefig(PLOTS_DIR / "fig5_mixed90_all.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Saved fig5_mixed90_all")

# ─────────────────────────────────────────────────────────────────────────────
# Figure 6: Best-config summary comparison (one bar per index, grouped by dataset)
# ─────────────────────────────────────────────────────────────────────────────

def best_of(df, metric_col):
    """Return a dict {index_name: (mean, std, [runs])} keeping best config per family."""
    df = df.copy()
    df["_m"] = df[metric_col]
    best = df.loc[df.groupby("index_name")["_m"].idxmax()]
    out = {}
    for _, row in best.iterrows():
        out[row["index_name"]] = (row["mean"], row["std"], row["runs"])
    return out

def draw_best_grouped(ax, data_by_ds, indexes, ylabel, title):
    """Grouped bars: x=datasets, groups=indexes (best config each)."""
    ds_labels = list(data_by_ds.keys())
    n_ds  = len(ds_labels)
    n_idx = len(indexes)
    w = 0.22
    x = np.arange(n_ds) * (n_idx * w + 0.15)
    for i, idx in enumerate(indexes):
        means = [data_by_ds[d].get(idx, (0,0,[]))[0] for d in ds_labels]
        stds  = [data_by_ds[d].get(idx, (0,0,[]))[1] for d in ds_labels]
        runs  = [data_by_ds[d].get(idx, (0,0,[]))[2] for d in ds_labels]
        offset = (i - n_idx/2 + 0.5) * w
        ax.bar(x + offset, means, w,
               color=FAMILY_COLOR[idx], edgecolor=FAMILY_EDGE[idx],
               linewidth=0.8, label=idx, zorder=2,
               yerr=stds, capsize=3, error_kw={"elinewidth":1})
        # individual run dots
        for xi, run_list in zip(x + offset, runs):
            jitter = np.linspace(-0.05, 0.05, len(run_list))
            for jj, v in zip(jitter, run_list):
                ax.scatter(xi + jj, v, color="white",
                           edgecolors=FAMILY_EDGE[idx],
                           s=18, linewidths=0.8, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(ds_labels, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

def fig_best_summary():
    indexes = ["LIPP", "BTree", "DynamicPGM"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))

    # Row 0: lookup-only, insert-tput, lookup-after-insert
    # Row 1: mixed 10%, mixed 90%, index size

    # Lookup-only
    data = {DATASET_LABELS[ds]: best_of(load_lookup_only(ds)[0], "mean") for ds in DATASETS}
    draw_best_grouped(axes[0,0], data, indexes, "Throughput (Mops/s)", "Lookup-Only")

    # Insert throughput
    def ins_data():
        d = {}
        for ds in DATASETS:
            df = load_insert_lookup(ds).copy()
            df["mean"] = df["ins_mean"]; df["std"] = df["ins_std"]; df["runs"] = df["ins_runs"]
            d[DATASET_LABELS[ds]] = best_of(df, "mean")
        return d
    draw_best_grouped(axes[0,1], ins_data(), indexes, "Insert Throughput (Mops/s)", "Insert Throughput")

    # Lookup after insert
    def lkp_ins_data():
        d = {}
        for ds in DATASETS:
            df = load_insert_lookup(ds).copy()
            df["mean"] = df["lkp_mean"]; df["std"] = df["lkp_std"]; df["runs"] = df["lkp_runs"]
            d[DATASET_LABELS[ds]] = best_of(df, "mean")
        return d
    draw_best_grouped(axes[0,2], lkp_ins_data(), indexes, "Throughput (Mops/s)", "Lookup After Insert")

    # Mixed 10%
    data10 = {DATASET_LABELS[ds]: best_of(load_mixed(ds,0.1)[0], "mean") for ds in DATASETS}
    draw_best_grouped(axes[1,0], data10, indexes, "Throughput (Mops/s)", "Mixed (10% Insert, 90% Lookup)")

    # Mixed 90%
    data90 = {DATASET_LABELS[ds]: best_of(load_mixed(ds,0.9)[0], "mean") for ds in DATASETS}
    draw_best_grouped(axes[1,1], data90, indexes, "Throughput (Mops/s)", "Mixed (90% Insert, 10% Lookup)")

    # Index size
    size_data = {}
    for ds in DATASETS:
        df, _ = load_lookup_only(ds)
        # best config per index by mean lookup
        best = df.loc[df.groupby("index_name")["mean"].idxmax()]
        size_data[DATASET_LABELS[ds]] = {row["index_name"]: (row["index_size_bytes"]/1e9, 0, [])
                                          for _, row in best.iterrows()}
    draw_best_grouped(axes[1,2], size_data, indexes, "Index Size (GB)", "Index Size (Best Config)")

    fig.suptitle("Summary: Best Configuration per Index (error bars = std; white dots = 3 individual runs)",
                 fontsize=12, fontweight='bold')
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "fig6_best_summary.pdf", bbox_inches='tight')
    fig.savefig(PLOTS_DIR / "fig6_best_summary.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("Saved fig6_best_summary")

# ─────────────────────────────────────────────────────────────────────────────
# Print full CSV-style summary table to stdout (for copy-paste into LaTeX)
# ─────────────────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "="*80)
    print("FULL RESULTS SUMMARY")
    print("="*80)
    for ds in DATASETS:
        print(f"\n{'─'*70}")
        print(f"Dataset: {DATASET_LABELS[ds]}")
        print(f"{'─'*70}")

        print("\n[1] Lookup-Only")
        df, _ = load_lookup_only(ds)
        print(f"  {'Index':<12} {'Config':<25} {'Run1':>8} {'Run2':>8} {'Run3':>8} {'Mean':>8} {'Std':>6}")
        for _, r in df.iterrows():
            cfg = f"{r.get('search_method','')},{r.get('value','')}" if not pd.isna(r.get('search_method')) else "—"
            runs = r["runs"]
            print(f"  {r['index_name']:<12} {cfg:<25} {runs[0]:>8.3f} {runs[1]:>8.3f} {runs[2]:>8.3f} {r['mean']:>8.3f} {r['std']:>6.3f}")

        print("\n[2] Insert Throughput (50% Insert)")
        df2 = load_insert_lookup(ds)
        print(f"  {'Index':<12} {'Config':<25} {'Run1':>8} {'Run2':>8} {'Run3':>8} {'Mean':>8} {'Std':>6}")
        for _, r in df2.iterrows():
            cfg = f"{r.get('search_method','')},{r.get('value','')}" if not pd.isna(r.get('search_method')) else "—"
            runs = r["ins_runs"]
            print(f"  {r['index_name']:<12} {cfg:<25} {runs[0]:>8.3f} {runs[1]:>8.3f} {runs[2]:>8.3f} {r['ins_mean']:>8.3f} {r['ins_std']:>6.3f}")

        print("\n[3] Lookup Throughput After Insert")
        print(f"  {'Index':<12} {'Config':<25} {'Run1':>8} {'Run2':>8} {'Run3':>8} {'Mean':>8} {'Std':>6}")
        for _, r in df2.iterrows():
            cfg = f"{r.get('search_method','')},{r.get('value','')}" if not pd.isna(r.get('search_method')) else "—"
            runs = r["lkp_runs"]
            print(f"  {r['index_name']:<12} {cfg:<25} {runs[0]:>8.3f} {runs[1]:>8.3f} {runs[2]:>8.3f} {r['lkp_mean']:>8.3f} {r['lkp_std']:>6.3f}")

        print("\n[4] Mixed 10% Insert")
        df3, _ = load_mixed(ds, 0.1)
        print(f"  {'Index':<12} {'Config':<25} {'Run1':>8} {'Run2':>8} {'Run3':>8} {'Mean':>8} {'Std':>6}")
        for _, r in df3.iterrows():
            cfg = f"{r.get('search_method','')},{r.get('value','')}" if not pd.isna(r.get('search_method')) else "—"
            runs = r["runs"]
            print(f"  {r['index_name']:<12} {cfg:<25} {runs[0]:>8.3f} {runs[1]:>8.3f} {runs[2]:>8.3f} {r['mean']:>8.3f} {r['std']:>6.3f}")

        print("\n[5] Mixed 90% Insert")
        df4, _ = load_mixed(ds, 0.9)
        print(f"  {'Index':<12} {'Config':<25} {'Run1':>8} {'Run2':>8} {'Run3':>8} {'Mean':>8} {'Std':>6}")
        for _, r in df4.iterrows():
            cfg = f"{r.get('search_method','')},{r.get('value','')}" if not pd.isna(r.get('search_method')) else "—"
            runs = r["runs"]
            print(f"  {r['index_name']:<12} {cfg:<25} {runs[0]:>8.3f} {runs[1]:>8.3f} {runs[2]:>8.3f} {r['mean']:>8.3f} {r['std']:>6.3f}")


if __name__ == "__main__":
    fig_lookup_only()
    fig_insert_throughput()
    fig_lookup_after_insert()
    fig_mixed_10()
    fig_mixed_90()
    fig_best_summary()
    print_summary()
    print("\nAll plots saved to:", PLOTS_DIR)
