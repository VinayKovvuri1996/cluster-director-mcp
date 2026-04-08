#!/bin/bash
#SBATCH --job-name=version_check
#SBATCH --output=version_check_%j.log
#SBATCH --partition=part1
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1

srun --label /bin/bash -c '     echo "=== HOST: \$(hostname) ===";     echo "--- OS Release ---";     cat /etc/os-release | grep PRETTY_NAME;      if command -v nvidia-smi &> /dev/null; then         echo "--- GPU Info ---";         nvidia-smi --query-gpu=driver_version,name --format=csv,noheader;     else         echo "--- GPU Info ---";         echo "No NVIDIA GPU detected (CPU-only node)";     fi;      if command -v python3 &> /dev/null; then         echo "--- PyTorch Version ---";         python3 -c "import torch; print(torch.__version__)" 2>/dev/null || echo "PyTorch not installed";     fi;     echo "==========================";     '
