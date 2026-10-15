# Validação dos ranges

Os ranges do app vêm de um solver de equilíbrio de Nash push/fold (chip EV) escrito em Python (`solver/`). Antes de calcular o cenário do app (9 jogadores, BB ante de 1bb, 5–15bb), o mesmo solver foi rodado com os parâmetros exatos de cada tabela pública conhecida e o resultado foi comparado mão a mão.

Não existe tabela pública de um jogo com BB ante *de verdade* (só o big blind paga o ante, e por isso joga com 1bb a menos): as tabelas "BB ante" que existem (ex.: PokerCoaching) são, por baixo, um ante clássico com o mesmo dinheiro morto. Por isso a validação é feita nos parâmetros de cada fonte, e a diferença para o BB ante real é mostrada à parte.

## 1. Heads-up sem ante — HoldemResources (HRC)

Fonte: dados brutos do equilíbrio publicados pela HoldemResources (`holdemresources_hu_equilibrium.zip`, frequência de push e call por mão, passo de 0,05bb) e a tabela clássica <https://www.holdemresources.net/hune>.

* Stacks comparados: 189 (1,2bb a 19,9bb, passo 0,1bb) × 169 mãos, push e call.
* **Decisões diferentes vs. dados brutos do HRC: 0 no push, 0 no call.** Maior diferença no % do range: 0,09 ponto (push) e 0,05 (call).
* Contra a tabela simplificada da página (valores arredondados a 0,1bb): 62 células de push e 2 de call diferem, todas em mãos onde a própria tabela difere dos dados brutos do HRC (mãos com gaps, como 43s/53s/63s, ou mistas perto do limite).

| Stack | Push (nós) | Push (HRC) | Call (nós) | Call (HRC) |
|---:|---:|---:|---:|---:|
| 2,0bb | 89,4% | 89,4% | 100,0% | 100,0% |
| 3,0bb | 77,9% | 78,0% | 92,3% | 92,3% |
| 5,0bb | 71,5% | 71,5% | 62,1% | 62,1% |
| 8,0bb | 61,9% | 61,9% | 45,0% | 45,0% |
| 10,0bb | 58,3% | 58,3% | 37,4% | 37,4% |
| 12,0bb | 53,2% | 53,2% | 33,0% | 33,0% |
| 15,0bb | 45,7% | 45,7% | 28,6% | 28,6% |
| 19,0bb | 40,9% | 40,9% | 22,6% | 22,6% |

## 2. 9 jogadores, 7,5bb, ante 0,1bb/jogador — HRC

Fonte: export de texto do HRC no blog da HoldemResources ("card bunching effects", cenário padrão sem bunching), com frequências mistas. Solver rodado com 9 jogadores, ante clássico 0,1bb, 7,5bb.

**Push:** 8 ranges comparados; 7 idênticos mão a mão; 1 mão diferente no total (média 0,12 por range); diferença média no % do range 0,06 ponto; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo 0,001bb.

Direção das diferenças: 1 mão só no nosso range, 0 só no da fonte.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| UTG 7,5bb | 18,6% | 18,1% | 22 | — |
| UTG+1 7,5bb | 20,4% | 20,4% | — | — |
| UTG+2 7,5bb | 23,4% | 23,4% | — | — |
| LJ 7,5bb | 27,9% | 27,9% | — | — |
| HJ 7,5bb | 33,0% | 33,0% | — | — |
| CO 7,5bb | 37,6% | 37,6% | — | — |
| BTN 7,5bb | 47,2% | 47,2% | — | — |
| SB 7,5bb | 77,4% | 77,4% | — | — |

**Call:** 1 range comparado; 1 idêntico mão a mão; 0 mãos diferentes no total (média 0,00 por range); diferença média no % do range 0,00 ponto.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| BB vs SB 7,5bb | 62,3% | 62,3% | — | — |

## 3. PokerCoaching — tabela com ante (10 jogadores, 0,1bb/jogador)

Fonte: dados embutidos no app gratuito de push/fold da PokerCoaching.com (as mesmas tabelas impressas como "BB Ante" e "12,5% Ante" para 9 jogadores). Por baixo é um cálculo com 10 jogadores e ante clássico de 0,1bb (1bb de dinheiro morto) sem o primeiro assento. Solver rodado com esses parâmetros, 5–15bb, todas as posições de push e todos os pares de call.

**Push:** 88 ranges comparados; 69 idênticos mão a mão; 26 mãos diferentes no total (média 0,30 por range); diferença média no % do range 0,13 ponto; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo 0,015bb.

Direção das diferenças: 13 mãos só no nosso range, 13 só no da fonte.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| HJ 10,0bb | 28,8% | 30,3% | K6s | QTo, A3o |
| LJ 15,0bb | 17,8% | 18,1% | A3s, T8s | QJo |
| CO 5,0bb | 43,3% | 43,9% | — | J6s, 86s |
| BTN 10,0bb | 43,3% | 43,9% | 85s | K5o |
| UTG+1 11,0bb | 16,0% | 16,6% | 98s | KJo |
| LJ 5,0bb | 33,3% | 33,0% | Q7s | — |
| HJ 6,0bb | 36,4% | 36,0% | K2s | — |
| CO 7,0bb | 39,7% | 40,6% | — | J9o |
| UTG 7,0bb | 19,2% | 18,7% | 22 | — |
| CO 8,0bb | 36,6% | 37,6% | — | T9o |
| UTG+2 8,0bb | 22,5% | 23,4% | — | KTo |
| UTG 8,0bb | 17,2% | 17,5% | — | A3s |

**Call:** 396 ranges comparados; 319 idênticos mão a mão; 88 mãos diferentes no total (média 0,22 por range); diferença média no % do range 0,11 ponto; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo 0,046bb.

Direção das diferenças: 25 mãos só no nosso range, 63 só no da fonte.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| UTG+1 vs UTG 6,0bb | 11,6% | 11,8% | 44 | KTs, QJs |
| BB vs CO 7,0bb | 44,8% | 45,7% | J6s | 65s, K3o |
| BB vs UTG 5,0bb | 49,9% | 50,5% | T5s | J8o |
| BTN vs HJ 5,0bb | 29,7% | 30,9% | — | K5s, A3o |
| SB vs CO 7,0bb | 32,7% | 33,3% | — | T8s, 98s |
| BTN vs CO 8,0bb | 21,1% | 22,9% | — | QJo, A6o |
| SB vs BTN 8,0bb | 34,8% | 35,4% | — | T8s, 98s |
| UTG+2 vs UTG+1 9,0bb | 8,8% | 9,2% | 55 | ATo |
| HJ vs UTG+2 11,0bb | 9,7% | 9,5% | 55 | A9s |
| UTG+2 vs UTG 5,0bb | 14,6% | 15,5% | — | A9o |
| SB vs UTG 5,0bb | 30,9% | 30,6% | 76s | — |
| UTG+2 vs UTG+1 5,0bb | 16,9% | 16,4% | 33 | — |

## 4. PokerCoaching — tabela sem ante (10 jogadores)

Mesma fonte, tabela sem ante. 5–15bb, push e call.

**Push:** 88 ranges comparados; 76 idênticos mão a mão; 15 mãos diferentes no total (média 0,17 por range); diferença média no % do range 0,05 ponto; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo 0,002bb.

Direção das diferenças: 8 mãos só no nosso range, 7 só no da fonte.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| HJ 5,0bb | 28,8% | 29,4% | 87s | JTo |
| CO 7,0bb | 31,2% | 31,2% | 76s | 97s |
| HJ 13,0bb | 15,4% | 16,0% | A7s | KJo |
| UTG+2 5,0bb | 21,0% | 20,7% | 98s | — |
| SB 6,0bb | 68,3% | 68,6% | — | 63s |
| BTN 6,0bb | 39,4% | 38,5% | T9o | — |
| UTG 8,0bb | 11,8% | 11,5% | A5s | — |
| UTG+1 9,0bb | 12,1% | 11,8% | T9s | — |
| UTG 11,0bb | 8,6% | 9,1% | — | 66 |
| CO 12,0bb | 22,8% | 23,1% | — | Q8s |
| HJ 12,0bb | 16,9% | 16,6% | 98s | — |
| UTG 13,0bb | 7,2% | 7,5% | — | A3s |

**Call:** 396 ranges comparados; 351 idênticos mão a mão; 45 mãos diferentes no total (média 0,11 por range); diferença média no % do range 0,05 ponto; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo 0,028bb.

Direção das diferenças: 14 mãos só no nosso range, 31 só no da fonte.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| UTG+1 vs UTG 5,0bb | 8,3% | 7,8% | 66 | — |
| BB vs UTG 5,0bb | 23,4% | 22,5% | QJo | — |
| SB vs UTG+1 5,0bb | 15,1% | 14,6% | 33 | — |
| CO vs LJ 5,0bb | 12,8% | 13,1% | — | A7s |
| BTN vs LJ 5,0bb | 13,1% | 13,4% | — | KTs |
| CO vs HJ 5,0bb | 14,3% | 15,2% | — | A8o |
| BB vs HJ 5,0bb | 35,4% | 35,1% | T7s | — |
| SB vs CO 5,0bb | 26,7% | 27,6% | — | QTo |
| UTG+2 vs UTG 6,0bb | 7,2% | 7,5% | — | ATs |
| UTG+2 vs UTG+1 6,0bb | 7,5% | 7,8% | — | KQs |
| BTN vs LJ 6,0bb | 11,0% | 11,9% | — | KQo |
| BB vs LJ 6,0bb | 24,6% | 24,9% | — | T9s |

## 5. 888poker / ICMIZER — 9 jogadores, 12bb, ante 12,5%

Fonte: capturas de tela do ICMIZER no artigo da 888poker (transcritas por cor de célula). Referência de menor precisão: transcrição de imagem, ante não totalmente documentado e um único gráfico para UTG e UTG+1 (comparado com as duas posições).

**Push:** 8 ranges comparados; 0 idênticos mão a mão; 33 mãos diferentes no total (média 4,12 por range); diferença média no % do range 1,00 ponto; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo 0,168bb.

Direção das diferenças: 23 mãos só no nosso range, 10 só no da fonte.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| UTG 12,0bb | 13,7% | 12,7% | Q9s, J9s, T9s, 44 | A4s |
| UTG+1 12,0bb | 15,4% | 12,7% | A7s, Q9s, J9s, ATo, T9s, 44, 33 | A4s |
| UTG+2 12,0bb | 18,2% | 18,2% | A6s, T8s, 98s | QJo |
| LJ 12,0bb | 22,2% | 21,3% | A8o, 87s | Q8s |
| HJ 12,0bb | 27,0% | 27,3% | A6o | K7s, QTo |
| CO 12,0bb | 33,0% | 33,0% | 65s | J7s |
| BTN 12,0bb | 41,5% | 38,8% | K2s, Q9o, K8o, K7o | T6s |
| SB 12,0bb | 69,5% | 69,8% | Q2o | 75o, 52s |

## 6. Nosso BB ante real vs. a tabela "BB Ante" da PokerCoaching

Comparação informativa: o dinheiro morto é o mesmo (pote inicial de 2,5bb), mas na tabela da PokerCoaching todos pagam 0,1bb de ante, enquanto no BB ante real só o big blind paga 1bb — e por isso ele joga com 1bb a menos. As diferenças abaixo são o efeito dessa regra (mais fortes no SB e nos calls do BB), não erro de cálculo.

**Push:** 88 ranges comparados; 21 idênticos mão a mão; 136 mãos diferentes no total (média 1,55 por range); diferença média no % do range 0,69 ponto; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo 0,116bb.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| HJ 5,0bb | 37,0% | 39,1% | — | Q5s, T7s, 97s, K7o, 76s |
| SB 7,0bb | 81,0% | 78,3% | 83s, 95o, 85o, T3o | 52s |
| SB 12,0bb | 70,1% | 66,8% | T2s, 93s, J6o, 96o, Q2o | — |
| CO 5,0bb | 42,7% | 43,9% | — | Q3s, J6s, 86s, 76s |
| LJ 5,0bb | 31,8% | 33,0% | Q7s | K3s, 87s, A2o |
| CO 7,0bb | 40,0% | 40,6% | K6o | T9o, 86s, 65s |
| SB 9,0bb | 76,5% | 73,5% | 92s, 75o, J3o, J2o | — |
| SB 10,0bb | 73,8% | 72,0% | 92s, 73s, 52s, J4o | — |
| HJ 10,0bb | 29,1% | 30,3% | K6s | 97s, 76s, A3o |
| SB 5,0bb | 85,8% | 83,1% | 84o, 93o, 92o | — |
| UTG+2 5,0bb | 29,0% | 30,6% | — | K9o, 87s, 22 |
| UTG+1 5,0bb | 25,3% | 27,0% | — | T8s, A6o, 22 |

**Call:** 396 ranges comparados; 175 idênticos mão a mão; 972 mãos diferentes no total (média 2,45 por range); diferença média no % do range 1,34 ponto; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo 0,282bb.

| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |
|---|---:|---:|---|---|
| BB vs UTG 5,0bb | 74,4% | 50,5% | J3s, J2s, T5s, T4s, T3s, T2s, 94s, 93s (+31) | — |
| BB vs UTG+2 5,0bb | 81,9% | 59,9% | T3s, T2s, 94s, 93s, 92s, 83s, 82s, J7o (+25) | — |
| BB vs UTG+1 5,0bb | 75,6% | 57,5% | J2s, T3s, T2s, 94s, 93s, 92s, 83s, 82s (+22) | — |
| BB vs LJ 5,0bb | 81,9% | 65,0% | T2s, 93s, 92s, 83s, 82s, 73s, 72s, J6o (+18) | — |
| BB vs HJ 5,0bb | 87,3% | 68,6% | 92s, 83s, 82s, 73s, 72s, J6o, T6o, 96o (+18) | — |
| BB vs LJ 6,0bb | 59,9% | 45,4% | Q2s, J5s, J4s, J3s, J2s, T5s, T4s, 95s (+18) | — |
| BB vs UTG+2 6,0bb | 53,9% | 40,9% | Q4s, Q3s, Q2s, J6s, J5s, J4s, J3s, T6s (+17) | — |
| BB vs HJ 6,0bb | 63,8% | 50,2% | J4s, J3s, J2s, T5s, T4s, T3s, 95s, J8o (+15) | — |
| BB vs CO 6,0bb | 67,4% | 54,5% | J2s, T5s, T4s, T3s, T2s, 95s, 94s, 84s (+15) | — |
| BB vs UTG+1 6,0bb | 48,1% | 36,6% | Q5s, Q4s, Q3s, J6s, J5s, J4s, T6s, J9o (+14) | — |
| BB vs BTN 6,0bb | 75,9% | 62,6% | T3s, T2s, 94s, 93s, 92s, 84s, 73s, J6o (+14) | — |
| BB vs CO 5,0bb | 89,1% | 73,8% | 92s, 83s, 82s, 72s, 62s, T5o, 95o, 85o (+13) | — |

## Como reproduzir

```
python -m solver.run_all --n 2 --ante-type none --ante 0 --max-callers 1 --stacks 1.2:20:0.1 --tag hu_noante
python -m solver.validate_hu
sh data/run_chain.sh   # app + rodadas de validação
python -m solver.validate_mw
python -m solver.report_validation
```
