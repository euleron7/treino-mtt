#!/bin/sh
# Solução do app + rodadas de validação (cada uma em paralelo internamente).
# Pré-requisito: data/eq2.npz e data/eq3.npz (python -m solver.equity_hu; python -m solver.equity_3way 80000)
cd "$(dirname "$0")/.." || exit 1
export PYTHONPATH=. OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python -u -m solver.run_all --tag 9max_bbante_mc2 --iters 2000 --procs 16 > data/run_mc2.log 2>&1
python -u -m solver.run_all --tag 9max_bbante_mc2 --refine 2e-5 --iters 8000 --procs 8 >> data/run_mc2.log 2>&1
python -u -m solver.run_all --tag hu_noante --n 2 --ante-type none --ante 0 --max-callers 1 --stacks 1.2:20:0.1 --iters 4000 --procs 8 > data/run_hu.log 2>&1
python -u -m solver.run_all --tag val_hrc_9max_7p5 --n 9 --ante-type classic --ante 0.1 --stacks 7.5 --iters 2000 --procs 8 > data/run_val_hrc.log 2>&1
python -u -m solver.run_all --tag val_888_12bb --n 9 --ante-type classic --ante 0.125 --stacks 12 --iters 2000 --procs 8 > data/run_val_888.log 2>&1
python -u -m solver.run_all --tag val_pc10_ante01 --n 10 --ante-type classic --ante 0.1 --stacks 5:15:1 --iters 1500 --procs 16 > data/run_val_pc10a.log 2>&1
python -u -m solver.run_all --tag val_pc10_noante --n 10 --ante-type none --ante 0 --stacks 5:15:1 --iters 1500 --procs 16 > data/run_val_pc10n.log 2>&1
echo CHAIN DONE
