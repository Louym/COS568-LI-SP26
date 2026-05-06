#!/bin/bash
#SBATCH --job-name=m3_run
#SBATCH --output=logs/m3_run_%j.out
#SBATCH --error=logs/m3_run_%j.err
#SBATCH --time=05:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=56G
#SBATCH --partition=cpu

# Benchmark binary is pre-built on the login node.
# This script only downloads data, generates workloads, runs benchmarks, and plots.

set -e
cd /scratch/gpfs/LI/yuming/workspace/hw/COS568-LI-SP26
mkdir -p logs results plots

export LD_LIBRARY_PATH=/scratch/gpfs/LI/yuming/workspace/hw/COS568-LI-SP26/build:$LD_LIBRARY_PATH

BENCHMARK=./build/benchmark
if [ ! -f "$BENCHMARK" ]; then
    echo "ERROR: benchmark binary not found. Build it on the login node first."
    exit 1
fi

echo "=== Clearing old M3 result CSVs ==="
for ds in fb_100M_public_uint64 books_100M_public_uint64 osmc_100M_public_uint64; do
    for wl in 0.900000i 0.100000i; do
        f="./results/${ds}_ops_2M_0.000000rq_0.500000nl_${wl}_0m_mix_results_table.csv"
        [ -f "$f" ] && rm "$f" && echo "  Removed $f"
    done
done

echo "=== Running benchmarks (3 repeats each) ==="
DATASETS="fb_100M_public_uint64 books_100M_public_uint64 osmc_100M_public_uint64"
INDEXES="DynamicPGM LIPP HybridPGMLipp AsyncHybridPGMLipp"

for DATA in $DATASETS; do
    for WL in 0.900000i 0.100000i; do
        OPS="./data/${DATA}_ops_2M_0.000000rq_0.500000nl_${WL}_0m_mix"
        if [ ! -f "$OPS" ]; then
            echo "WARNING: workload $OPS not found – skipping."
            continue
        fi
        echo "=== Dataset: $DATA | Workload: $WL ==="
        for INDEX in $INDEXES; do
            echo "  Running $INDEX ..."
            $BENCHMARK ./data/$DATA $OPS --through --csv --only $INDEX -r 3
        done
    done
done

echo "=== Adding CSV headers ==="
for FILE in ./results/*_mix_results_table.csv; do
    [ -f "$FILE" ] || continue
    if head -n 1 "$FILE" | grep -q "index_name"; then
        sed -i '1d' "$FILE"
    fi
    sed -i '1s/^/index_name,build_time_ns1,build_time_ns2,build_time_ns3,index_size_bytes,mixed_throughput_mops1,mixed_throughput_mops2,mixed_throughput_mops3,search_method,value\n/' "$FILE"
    echo "  Header set for $FILE"
done

echo "=== Generating plots ==="
module load anaconda3/2023.3
python3 scripts/plot_milestone3.py

echo "=== Done! Results in ./results/, plots in ./plots/ ==="
