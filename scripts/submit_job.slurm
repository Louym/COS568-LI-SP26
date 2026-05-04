#!/bin/bash
#SBATCH --job-name=hw     # 作业名称
#SBATCH --nodes=1                   # 占用节点数
#SBATCH --ntasks=1                  # 运行的任务数
#SBATCH --cpus-per-task=16          # 每个任务分配的 CPU 核心数
#SBATCH --mem=64G                   # 申请的总内存
#SBATCH --time=60:00             # 运行时间限制 (时:分:秒)
#SBATCH --output=logs/%x_%j.out   # 标准输出日志文件
#SBATCH --error=logs/%x_%j.err    # 标准错误日志文件

# 加载必要的模块 (根据实际环境调整)
source xxx/bin/activate
bash scripts/run_all.sh
