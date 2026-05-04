#!/usr/bin/env bash
# Generate the two mixed workloads (90% and 10% insert) for all three datasets
# needed for Milestone 3.

set -e
cd /scratch/gpfs/LI/yuming/workspace/hw/COS568-LI-SP26

mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=Release .. -DCMAKE_CXX_STANDARD=17 > /dev/null
make -j8 generate
cd ..

function gen() {
    local dataset=$1
    echo "Generating workloads for $dataset ..."
    ./build/generate ./data/$dataset 2000000 \
        --insert-ratio 0.9 --negative-lookup-ratio 0.5 --mix
    ./build/generate ./data/$dataset 2000000 \
        --insert-ratio 0.1 --negative-lookup-ratio 0.5 --mix
}

for ds in fb_100M_public_uint64 books_100M_public_uint64 osmc_100M_public_uint64; do
    gen $ds
done

echo "All Milestone 3 workloads generated."
