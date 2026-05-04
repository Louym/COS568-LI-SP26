#!/bin/bash
#SBATCH --job-name=milestone2
#SBATCH --output=logs/milestone2_%j.out
#SBATCH --error=logs/milestone2_%j.err
#SBATCH --time=02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --partition=cpu

cd /scratch/gpfs/LI/yuming/workspace/hw/COS568-LI-SP26

mkdir -p logs

echo "Building benchmark..."
cd build && make -j8 && cd ..

echo "Running milestone2 benchmarks..."
./scripts/run_milestone2.sh

echo "Generating plots..."
module load anaconda3/2023.3
python3 scripts/plot_milestone2.py

echo "Done."
