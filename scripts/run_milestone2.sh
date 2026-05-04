#!/bin/bash
# Milestone 2 benchmark: compare DynamicPGM, LIPP, HybridPGMLipp on fb_100M
# using two mixed workloads: 90% insert (0.900000i) and 10% insert (0.100000i)

set -e

BENCHMARK=build/benchmark
if [ ! -f $BENCHMARK ]; then
    echo "benchmark binary does not exist; building..."
    ./scripts/build_benchmark.sh
fi

mkdir -p results

DATA=fb_100M_public_uint64

echo "=== Running 90% insert mixed workload ==="
for INDEX in DynamicPGM LIPP HybridPGMLipp; do
    echo "  Running $INDEX"
    $BENCHMARK ./data/$DATA \
        ./data/${DATA}_ops_2M_0.000000rq_0.500000nl_0.900000i_0m_mix \
        --through --csv --only $INDEX -r 3
done

echo "=== Running 10% insert mixed workload ==="
for INDEX in DynamicPGM LIPP HybridPGMLipp; do
    echo "  Running $INDEX"
    $BENCHMARK ./data/$DATA \
        ./data/${DATA}_ops_2M_0.000000rq_0.500000nl_0.100000i_0m_mix \
        --through --csv --only $INDEX -r 3
done

echo "=== Adding CSV headers ==="
for FILE in ./results/${DATA}_ops_2M_0.000000rq_0.500000nl_0.900000i_0m_mix_results_table.csv \
            ./results/${DATA}_ops_2M_0.000000rq_0.500000nl_0.100000i_0m_mix_results_table.csv; do
    if [ -f "$FILE" ]; then
        if head -n 1 "$FILE" | grep -q "index_name"; then
            sed -i '1d' "$FILE"
        fi
        sed -i '1s/^/index_name,build_time_ns1,build_time_ns2,build_time_ns3,index_size_bytes,mixed_throughput_mops1,mixed_throughput_mops2,mixed_throughput_mops3,search_method,value\n/' "$FILE"
        echo "Header set for $FILE"
    fi
done

echo "=== Milestone 2 benchmarking complete! Results in ./results/ ==="
