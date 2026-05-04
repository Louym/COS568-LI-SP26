#!/usr/bin/env bash
# Run Milestone 3 benchmarks:
#   DynamicPGM, LIPP, HybridPGMLipp, AsyncHybridPGMLipp
#   on all three datasets (FB, Books, OSMC)
#   for both mixed workloads (90% insert, 10% insert)
#
# All indexes are run with the same number of CPUs (--cpus-per-task in slurm).

set -e
cd /scratch/gpfs/LI/yuming/workspace/hw/COS568-LI-SP26

BENCHMARK=./build/benchmark
if [ ! -f $BENCHMARK ]; then
    echo "benchmark binary does not exist; building..."
    cd build && make -j8 && cd ..
fi

mkdir -p results

INDEXES="DynamicPGM LIPP HybridPGMLipp AsyncHybridPGMLipp"

DATASETS="fb_100M_public_uint64 books_100M_public_uint64 osmc_100M_public_uint64"

for DATA in $DATASETS; do
    for WL in 0.900000i 0.100000i; do
        OPS="./data/${DATA}_ops_2M_0.000000rq_0.500000nl_${WL}_0m_mix"
        if [ ! -f "$OPS" ]; then
            echo "Workload $OPS not found – skipping."
            continue
        fi
        echo "=== Dataset: $DATA | Workload: $WL ==="
        for INDEX in $INDEXES; do
            echo "  Running $INDEX ..."
            $BENCHMARK ./data/$DATA $OPS --through --csv --only $INDEX -r 3
        done
    done
done

# ── Add CSV headers ──────────────────────────────────────────────────────────
echo "=== Adding CSV headers ==="
for FILE in ./results/*_mix_results_table.csv; do
    [ -f "$FILE" ] || continue
    # Remove existing header if present
    if head -n 1 "$FILE" | grep -q "index_name"; then
        sed -i '1d' "$FILE"
    fi
    sed -i '1s/^/index_name,build_time_ns1,build_time_ns2,build_time_ns3,index_size_bytes,mixed_throughput_mops1,mixed_throughput_mops2,mixed_throughput_mops3,search_method,value\n/' "$FILE"
    echo "  Header set for $FILE"
done

echo "=== Milestone 3 benchmarking complete! Results in ./results/ ==="
