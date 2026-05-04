#!/usr/bin/env python3
"""
Milestone 2 plot generator.
Produces 4 bar plots for the Facebook dataset:
  1. Throughput – 90% Insert mixed workload
  2. Throughput – 10% Insert mixed workload
  3. Index size  – 90% Insert mixed workload
  4. Index size  – 10% Insert mixed workload
"""
import os
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict

RESULTS_DIR = "./results"
PLOTS_DIR   = "./plots"
os.makedirs(PLOTS_DIR, exist_ok=True)

# ── helpers ───────────────────────────────────────────────────────────────────

def parse_csv(filepath):
    """Return list-of-dicts for each row."""
    rows = []
    with open(filepath, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def best_row(rows, index_name, throughput_cols):
    """
    From all rows belonging to `index_name`, pick the one whose average
    throughput (across the three repeat columns) is highest.
    Returns (avg_throughput, index_size_bytes).
    """
    best_avg  = -1
    best_size = 0
    for row in rows:
        if row["index_name"].strip() != index_name:
            continue
        try:
            vals = [float(row[c]) for c in throughput_cols if row.get(c, "").strip()]
            if not vals:
                continue
            avg = np.mean(vals)
            if avg > best_avg:
                best_avg  = avg
                best_size = int(row["index_size_bytes"])
        except ValueError:
            continue
    return best_avg, best_size


def make_bar_plot(labels, values, errors, ylabel, title, filename,
                  colors=None, ymax=None):
    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(labels))
    width = 0.5
    if colors is None:
        colors = ['#4C72B0', '#DD8452', '#55A868']
    bars = ax.bar(x, values, width, color=colors, edgecolor='black', linewidth=0.8)
    ax.errorbar(x, values, yerr=errors, fmt='none', color='black',
                capsize=5, linewidth=1.5, capthick=1.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=13)
    if ymax:
        ax.set_ylim(0, ymax)
    else:
        ax.set_ylim(0, max(values) * 1.3 if values else 1)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, filename)
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved {path}")


# ── data extraction ────────────────────────────────────────────────────────────

TCOLS = ["mixed_throughput_mops1", "mixed_throughput_mops2", "mixed_throughput_mops3"]

workloads = {
    "90pct_insert": "fb_100M_public_uint64_ops_2M_0.000000rq_0.500000nl_0.900000i_0m_mix_results_table.csv",
    "10pct_insert": "fb_100M_public_uint64_ops_2M_0.000000rq_0.500000nl_0.100000i_0m_mix_results_table.csv",
}

INDEXES = ["DynamicPGM", "LIPP", "HybridPGMLipp"]
COLORS  = ['#4C72B0', '#DD8452', '#55A868']
LABELS  = ["DynamicPGM", "LIPP", "Hybrid"]

results = {}  # results[workload][index] = (mean_tput, std_tput, size_bytes)

for wkey, fname in workloads.items():
    fpath = os.path.join(RESULTS_DIR, fname)
    rows  = parse_csv(fpath)
    results[wkey] = {}
    for idx in INDEXES:
        # Collect all rows for this index
        idx_rows = [r for r in rows if r["index_name"].strip() == idx]
        if not idx_rows:
            results[wkey][idx] = (0, 0, 0)
            continue
        # Find best configuration (highest mean throughput)
        best_mean = -1
        best_std  = 0
        best_size = 0
        by_variant = defaultdict(list)
        for row in idx_rows:
            key = (row.get("search_method",""), row.get("value",""))
            by_variant[key].append(row)
        for key, rlist in by_variant.items():
            # Aggregate all throughput values across rows in this variant
            vals = []
            for r in rlist:
                for c in TCOLS:
                    v = r.get(c, "").strip()
                    if v:
                        try: vals.append(float(v))
                        except ValueError: pass
            if not vals:
                continue
            mean_v = np.mean(vals)
            if mean_v > best_mean:
                best_mean = mean_v
                best_std  = np.std(vals)
                best_size = int(rlist[0]["index_size_bytes"])
        results[wkey][idx] = (best_mean, best_std, best_size)

# ── throughput plots ───────────────────────────────────────────────────────────

for wkey, title_suffix, short in [
    ("90pct_insert", "90% Insert / 10% Lookup", "90i"),
    ("10pct_insert", "10% Insert / 90% Lookup", "10i"),
]:
    vals   = [results[wkey][i][0] for i in INDEXES]
    errs   = [results[wkey][i][1] for i in INDEXES]
    make_bar_plot(
        LABELS, vals, errs,
        ylabel="Throughput (Mops/s)",
        title=f"Throughput – FB Dataset ({title_suffix})",
        filename=f"milestone2_throughput_{short}.png",
        colors=COLORS,
    )

# ── index size plots ───────────────────────────────────────────────────────────

for wkey, title_suffix, short in [
    ("90pct_insert", "90% Insert / 10% Lookup", "90i"),
    ("10pct_insert", "10% Insert / 90% Lookup", "10i"),
]:
    sizes_gb = [results[wkey][i][2] / 1e9 for i in INDEXES]
    make_bar_plot(
        LABELS, sizes_gb, [0]*len(INDEXES),
        ylabel="Index Size (GB)",
        title=f"Index Size – FB Dataset ({title_suffix})",
        filename=f"milestone2_size_{short}.png",
        colors=COLORS,
    )

# ── print summary ─────────────────────────────────────────────────────────────
print("\n=== Summary ===")
for wkey in workloads:
    print(f"\n{wkey}:")
    for idx in INDEXES:
        m, s, sz = results[wkey][idx]
        print(f"  {idx:20s}: throughput={m:.3f} ± {s:.3f} Mops/s, size={sz/1e9:.2f} GB")
