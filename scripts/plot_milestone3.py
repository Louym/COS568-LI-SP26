#!/usr/bin/env python3
"""
Milestone 3 plot generator.

Produces 12 bar plots (throughput + index size) for three datasets
(FB, Books, OSMC) × two workloads (90% Insert, 10% Insert).
Each bar group contains four bars:
  DynamicPGM | LIPP | HybridPGMLipp (naive) | AsyncHybridPGMLipp (async)
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
    rows = []
    with open(filepath, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def best_config(rows, index_name, throughput_cols):
    """
    For a given index, find the single hyperparameter row with the highest
    mean throughput and return (mean, std, index_size_bytes).
    Each row is evaluated independently so mixing different configs in the
    same (search_method, value) group cannot dilute the best result.
    """
    best_mean = -1.0
    best_std  = 0.0
    best_size = 0
    for row in rows:
        if row.get("index_name", "").strip() != index_name:
            continue
        vals = []
        for c in throughput_cols:
            v = row.get(c, "").strip()
            if v:
                try:
                    vals.append(float(v))
                except ValueError:
                    pass
        if not vals:
            continue
        m = float(np.mean(vals))
        if m > best_mean:
            best_mean = m
            best_std  = float(np.std(vals))
            try:
                best_size = int(row["index_size_bytes"])
            except (ValueError, KeyError):
                best_size = 0
    return best_mean, best_std, best_size


def bar_plot(labels, values, errors, ylabel, title, filename, colors=None):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(labels))
    w = 0.5
    if colors is None:
        colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
    ax.bar(x, values, w, color=colors, edgecolor='black', linewidth=0.8)
    ax.errorbar(x, values, yerr=errors, fmt='none', color='black',
                capsize=5, linewidth=1.5, capthick=1.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=12)
    ax.set_ylim(0, max(v for v in values if v > 0) * 1.35 if any(v > 0 for v in values) else 1)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    plt.tight_layout()
    path = os.path.join(PLOTS_DIR, filename)
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"Saved {path}")


# ── configuration ─────────────────────────────────────────────────────────────

TCOLS = ["mixed_throughput_mops1", "mixed_throughput_mops2", "mixed_throughput_mops3"]

INDEXES = ["DynamicPGM", "LIPP", "HybridPGMLipp", "AsyncHybridPGMLipp"]
LABELS  = ["DynamicPGM", "LIPP", "Hybrid\n(naive)", "Adaptive\nHybrid"]
COLORS  = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']

DATASETS = {
    "fb":    "fb_100M_public_uint64",
    "books": "books_100M_public_uint64",
    "osmc":  "osmc_100M_public_uint64",
}
DATASET_LABELS = {
    "fb":    "FB",
    "books": "Books",
    "osmc":  "OSMC",
}
WORKLOADS = {
    "90i": ("0.900000i", "90% Insert / 10% Lookup"),
    "10i": ("0.100000i", "10% Insert / 90% Lookup"),
}

# ── collect results ────────────────────────────────────────────────────────────

results = {}  # results[(ds_key, wl_key)][idx] = (mean, std, size)

for ds_key, ds_name in DATASETS.items():
    for wl_key, (wl_pattern, _wl_label) in WORKLOADS.items():
        fname = f"{ds_name}_ops_2M_0.000000rq_0.500000nl_{wl_pattern}_0m_mix_results_table.csv"
        fpath = os.path.join(RESULTS_DIR, fname)
        if not os.path.isfile(fpath):
            print(f"WARNING: result file not found: {fpath}")
            results[(ds_key, wl_key)] = {idx: (0, 0, 0) for idx in INDEXES}
            continue
        rows = parse_csv(fpath)
        results[(ds_key, wl_key)] = {}
        for idx in INDEXES:
            results[(ds_key, wl_key)][idx] = best_config(rows, idx, TCOLS)

# ── generate plots ─────────────────────────────────────────────────────────────

for ds_key, ds_name in DATASETS.items():
    ds_label = DATASET_LABELS[ds_key]
    for wl_key, (wl_pattern, wl_label) in WORKLOADS.items():
        r = results[(ds_key, wl_key)]

        vals  = [r[i][0] for i in INDEXES]
        errs  = [r[i][1] for i in INDEXES]
        sizes = [r[i][2] / 1e9 for i in INDEXES]   # bytes → GB

        # Throughput
        bar_plot(
            LABELS, vals, errs,
            ylabel="Throughput (Mops/s)",
            title=f"Throughput – {ds_label} ({wl_label})",
            filename=f"m3_throughput_{ds_key}_{wl_key}.png",
            colors=COLORS,
        )

        # Index size
        bar_plot(
            LABELS, sizes, [0] * len(INDEXES),
            ylabel="Index Size (GB)",
            title=f"Index Size – {ds_label} ({wl_label})",
            filename=f"m3_size_{ds_key}_{wl_key}.png",
            colors=COLORS,
        )

# ── summary table ──────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SUMMARY (best config per index per workload)")
print("=" * 70)
for ds_key in DATASETS:
    for wl_key, (_, wl_label) in WORKLOADS.items():
        print(f"\n{DATASET_LABELS[ds_key]} – {wl_label}:")
        r = results[(ds_key, wl_key)]
        for idx in INDEXES:
            m, s, sz = r[idx]
            print(f"  {idx:25s}  {m:7.3f} ± {s:.3f} Mops/s   size={sz/1e9:.3f} GB")
