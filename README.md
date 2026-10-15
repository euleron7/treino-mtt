# Treino MTT — push/fold, call vs all-in e outs

Treinador de poker de torneio para o celular, que funciona offline.

**App:** https://euleron7.github.io/treino-mtt/

| Modo | O que treina |
|---|---|
| **Push/Fold** | Mesa de 9, BB ante, 5–15bb. O app mostra sua posição, o stack e a mão, e você aperta PUSH ou FOLD. |
| **Call vs all-in** | Alguém deu all-in e foldaram até você. O app mostra quem empurrou, sua posição, o stack, o pote e o preço do call, e você aperta CALL ou FOLD. |
| **Outs** | O app mostra sua mão, a do vilão e o board (flop ou turn). Você diz quantos outs tem e a % pela regra do 2 e 4. A correção traz o número exato de outs, as cartas, a % exata e a equity real. |

Nos três modos o app mostra se você acertou, a resposta certa, o EV da decisão e o placar. Também há uma lista dos seus erros, que fica salva no aparelho. Nos modos de push e call, cada resposta mostra também a tabela 13×13 do spot com a sua mão marcada. A aba **Tabelas** permite consultar todos os ranges.

## Instalar no celular

Abra o link uma vez com internet. Depois:

* **Android (Chrome):** menu ⋮ → *Instalar app* (ou *Adicionar à tela inicial*).
* **iPhone (Safari):** botão Compartilhar → *Adicionar à Tela de Início*.

Depois da primeira visita o app abre sem internet: um service worker guarda a página, os ranges e os ícones.

## O modelo

* 9 jogadores: UTG, UTG+1, UTG+2, LJ, HJ, CO, BTN, SB e BB. Todos começam a mão com o mesmo stack, contado em bb antes de postar.
* Blinds de 0,5/1 e **BB ante de 1bb**. Só o big blind paga o ante, e esse dinheiro fica morto no pote. Por isso o BB joga com 1bb a menos: com 10bb, ele cobre só 9bb de um all-in.
* **Chip EV.** O objetivo é maximizar fichas; não há ICM.
* Quando foldam até você, as opções são push ou fold. Quem está atrás pode dar call ou fold. Cabem **até 2 callers**, ou seja, potes de até 3 jogadores; o mesmo limite do HRC (modo enumerado) e do ICMIZER. Side pots são calculados exatamente.
* A remoção de cartas entre os jogadores que estão no pote é exata. As cartas de quem já foldou são ignoradas, como nas calculadoras padrão (sem "card bunching"). Uma simulação independente mediu o efeito disso: depois de vários folds, os pushes marginais de CO, BTN e SB e os calls marginais dos blinds rendem cerca de 0,2–0,3bb a menos do que o mostrado, porque quem foldou tende a ter cartas baixas.
* Algumas mãos são **mistas** no equilíbrio, isto é, jogadas só em parte das vezes. Nelas o app aceita as duas respostas e mostra a frequência.

## Como os ranges foram calculados (`solver/`)

1. **Avaliador de mãos** (`evaluator.py`). Avaliador de 7 cartas em numba, baseado em tabelas. Foi conferido contra um avaliador de força bruta (melhor das 21 combinações) em 60 mil mãos.
2. **Equity heads-up exata** (`equity_hu.py`). Os 812.175 confrontos entre combos se reduzem a 47.008 por isomorfismo de naipes. Cada um foi enumerado nos 1.712.304 boards possíveis, em 88 s. Exemplos: AA vs KK = 81,95%, AKo vs QQ = 43,24%.
3. **Equity de 3 jogadores** (`equity_3way.py`). Monte Carlo estratificado com 80 mil boards por trio de classes de mão (818.805 trios). Guarda a parte de cada jogador no pote principal e no side pot. Conferido contra enumeração exata.
4. **Equilíbrio de Nash** (`nash.py`). Cada posição que abre é um subjogo independente. Cada subjogo é resolvido por *fictitious play* com média linear: melhor resposta contra as estratégias médias, até o ganho de qualquer desvio ficar abaixo de ~0,0001bb. O resultado são frequências por mão e o EV(ação) − EV(fold) de cada uma.
5. **Dados do app** (`build_web.py` → `docs/ranges.js`). Para cada spot ficam o EV em centésimos de bb e as frequências das mãos mistas.

## Validação

Antes de calcular o cenário do app, o mesmo solver foi rodado com os parâmetros exatos de tabelas públicas conhecidas. Os detalhes estão em [VALIDACAO.md](VALIDACAO.md). Resumo:

* **Heads-up sem ante, contra os dados brutos de equilíbrio da HoldemResources (HRC):** 0 decisões diferentes em 189 stacks × 169 mãos, no push e no call.
* **9 jogadores, 7,5bb, ante de 0,1bb por jogador, contra o export do HRC:** 7 das 8 posições de push e o call do BB batem mão a mão. A diferença que sobra é uma mão que o próprio HRC joga mista.
* **PokerCoaching (10 jogadores, com e sem ante, 5–15bb, todos os ranges de push e de call; 484 ranges em cada tabela):** 388 e 427 ranges idênticos mão a mão. Toda mão que difere está a no máximo 0,05bb da indiferença, ou seja, são mãos limítrofes.
* **Simulação independente:** uma simulação Monte Carlo do jogo real conferiu os EVs do solver em 18 spots, com 5,9 bilhões de mãos. Nenhuma diferença passou do ruído e nenhuma decisão inverteu.

Não existe tabela pública de BB ante *real*. As tabelas "BB ante" disponíveis usam ante clássico com o mesmo dinheiro morto. A comparação com elas aparece separada em VALIDACAO.md: a regra do BB ante muda principalmente o push do SB e os calls do BB em stacks curtos.

## Modo outs

* **Out** é uma carta que, se sair na próxima rua, deixa você **na frente** da mão do vilão. Cartas que só empatam aparecem à parte e não contam.
* **Chance exata** é a probabilidade de sair pelo menos um out. Ela usa as cartas que ainda não foram vistas: 45 no flop e 44 no turn, porque a sua mão, a do vilão e o board são conhecidos. O app também mostra a conta "sem ver o vilão" (47/46 cartas, a tabela clássica) e a equity real até o river.
* A % conta como certa se ficar entre a menor e a maior das estimativas razoáveis, com uma pequena folga. As estimativas são: a exata, a da tabela clássica, a regra do 2 e 4 e, no flop com mais de 8 outs, a regra corrigida 4 × outs − (outs − 8).
* Situações em que você só perde no kicker (quase todas as cartas empatam) ficam de fora.

## Recalcular

```
pip install numpy numba scipy pillow
python -m solver.equity_hu                     # ~1,5 min
python -m solver.equity_3way 80000             # ~7 min
python -m solver.run_all --tag 9max_bbante_mc2 --iters 2000
python -m solver.run_all --tag 9max_bbante_mc2 --refine 2e-5 --iters 8000
python -m solver.build_web 9max_bbante_mc2     # gera docs/ranges.js
python -m solver.make_icons
```

A validação (`solver/validate_hu.py`, `solver/validate_mw.py`, `solver/report_validation.py`) precisa das tabelas de referência. Elas não ficam neste repositório porque são material de terceiros. As fontes estão listadas em VALIDACAO.md.

## Arquivos

```
docs/            o app publicado (index.html, ranges.js, sw.js, manifest, ícones)
solver/          avaliador, equities, solver de Nash, geração dos dados e validação
data/solutions/  soluções completas (frequência e EV por mão, inclusive overcalls)
data/validation/ resultados das comparações com as tabelas públicas
```
