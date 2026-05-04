#!/bin/bash
#SBATCH --job-name=milestone3
#SBATCH --output=logs/milestone3_%j.out
#SBATCH --error=logs/milestone3_%j.err
#SBATCH --time=04:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --partition=cpu

# 2 CPUs: 1 for the main benchmark thread + 1 for the background flush thread.
# All index implementations (DynamicPGM, LIPP, HybridPGMLipp, AsyncHybridPGMLipp)
# are run under the same SLURM allocation to ensure a fair comparison.

set -e
cd /scratch/gpfs/LI/yuming/workspace/hw/COS568-LI-SP26
mkdir -p logs

echo "=== Building benchmark ==="
cd build
cmake -DCMAKE_BUILD_TYPE=Release .. -DCMAKE_CXX_STANDARD=17 > /dev/null
make -j2
cd ..

echo "=== Generating workloads ==="
bash scripts/generate_milestone3_workloads.sh

echo "=== Running Milestone 3 benchmarks ==="
bash scripts/run_milestone3.sh

echo "=== Generating plots ==="
module load anaconda3/2023.3
python3 scripts/plot_milestone3.py

echo "=== Done ==="
