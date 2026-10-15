"""Turn data/validation/{hu,multiway}.json into VALIDACAO.md and the app's summary table.

Writes:
  VALIDACAO.md                              (repo root, Portuguese)
  data/validation/summary_for_app.json      (short table shown in the app's "como foi calculado" sheet)
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
VAL = os.path.join(ROOT, "data", "validation")

POS9 = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB"]


def pct(x):
    return f"{x:.1f}".replace(".", ",")


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


def margin_txt(mm):
    return "menos de 0,001bb" if mm < 0.0005 else f"{num(mm, 3)}bb"


def margin_phrase(mm):
    return "a menos de 0,001bb da indiferença" if mm < 0.0005 else f"a no máximo {num(mm, 3)}bb da indiferença"


def max_margin(rows):
    vals = [abs(v) for r in rows for v in r.get("diff_dev", {}).values() if v is not None]
    return max(vals) if vals else 0.0


def fmt_hands(hs, n=8):
    hs = list(hs)
    return ", ".join(hs[:n]) + (f" (+{len(hs) - n})" if len(hs) > n else "")


def main():
    hu = json.load(open(os.path.join(VAL, "hu.json"), encoding="utf-8"))
    mw = json.load(open(os.path.join(VAL, "multiway.json"), encoding="utf-8"))
    md = []
    app = []
    md.append("# Validação dos ranges\n")
    md.append("Os ranges do app vêm de um solver de equilíbrio de Nash push/fold (chip EV) escrito em Python "
              "(`solver/`). Antes de calcular o cenário do app (9 jogadores, BB ante de 1bb, 5–15bb), o mesmo "
              "solver foi rodado com os parâmetros exatos de cada tabela pública conhecida e o resultado foi "
              "comparado mão a mão.\n")
    md.append("Não existe tabela pública de um jogo com BB ante *de verdade* (só o big blind paga o ante, "
              "e por isso joga com 1bb a menos): as tabelas \"BB ante\" que existem (ex.: PokerCoaching) são, "
              "por baixo, um ante clássico com o mesmo dinheiro morto. Por isso a validação é feita nos "
              "parâmetros de cada fonte, e a diferença para o BB ante real é mostrada à parte.\n")

    # --- heads-up
    s = hu["summary"]
    raw = s["raw_equilibrium"]
    md.append("## 1. Heads-up sem ante — HoldemResources (HRC)\n")
    md.append("Fonte: dados brutos do equilíbrio publicados pela HoldemResources "
              "(`holdemresources_hu_equilibrium.zip`, frequência de push e call por mão, passo de 0,05bb) "
              "e a tabela clássica <https://www.holdemresources.net/hune>.\n")
    md.append(f"* Stacks comparados: {s['stacks_compared']} (1,2bb a 19,9bb, passo 0,1bb) × 169 mãos, push e call.")
    md.append(f"* **Decisões diferentes vs. dados brutos do HRC: {raw['push_action_mismatches']} no push, "
              f"{raw['call_action_mismatches']} no call.** Maior diferença no % do range: "
              f"{num(raw['max_abs_push_pct_diff'])} ponto (push) e {num(raw['max_abs_call_pct_diff'])} (call).")
    ch = s["chart"]
    md.append(f"* Contra a tabela simplificada da página (valores arredondados a 0,1bb): {ch['push_mismatches']} "
              f"células de push e {ch['call_mismatches']} de call diferem, todas em mãos onde a própria tabela "
              "difere dos dados brutos do HRC (mãos com gaps, como 43s/53s/63s, ou mistas perto do limite).\n")
    md.append("| Stack | Push (nós) | Push (HRC) | Call (nós) | Call (HRC) |")
    md.append("|---:|---:|---:|---:|---:|")
    for r in hu["rows"]:
        if r["stack"] in (2.0, 3.0, 5.0, 8.0, 10.0, 12.0, 15.0, 19.0) and "hr_push_pct" in r:
            md.append(f"| {pct(r['stack'])}bb | {pct(r['push_pct'])}% | {pct(r['hr_push_pct'])}% | "
                      f"{pct(r['call_pct'])}% | {pct(r['hr_call_pct'])}% |")
    md.append("")
    app.append({"ref": "Heads-up sem ante — dados brutos do HRC (1,2–19,9bb)",
                "result": f"{raw['push_action_mismatches'] + raw['call_action_mismatches']} decisões diferentes "
                          f"em {2 * s['hand_cells']:,} (push e call)".replace(",", ".")})

    # --- multiway
    labels = {
        "HRC blog 9-max 7.5bb, ante 0.1/player (no bunching)":
            ("## 2. 9 jogadores, 7,5bb, ante 0,1bb/jogador — HRC",
             "Fonte: export de texto do HRC no blog da HoldemResources (\"card bunching effects\", cenário padrão "
             "sem bunching), com frequências mistas. Solver rodado com 9 jogadores, ante clássico 0,1bb, 7,5bb."),
        "PokerCoaching app table 1 (10-handed, ante 0.1/player)":
            ("## 3. PokerCoaching — tabela com ante (10 jogadores, 0,1bb/jogador)",
             "Fonte: dados embutidos no app gratuito de push/fold da PokerCoaching.com (as mesmas tabelas "
             "impressas como \"BB Ante\" e \"12,5% Ante\" para 9 jogadores). Por baixo é um cálculo com "
             "10 jogadores e ante clássico de 0,1bb (1bb de dinheiro morto) sem o primeiro assento. "
             "Solver rodado com esses parâmetros, 5–15bb, todas as posições de push e todos os pares de call."),
        "PokerCoaching app table 0 (10-handed, no ante)":
            ("## 4. PokerCoaching — tabela sem ante (10 jogadores)",
             "Mesma fonte, tabela sem ante. 5–15bb, push e call."),
        "888poker / ICMIZER 9-max 12bb, ante 0.125/player":
            ("## 5. 888poker / ICMIZER — 9 jogadores, 12bb, ante 12,5%",
             "Fonte: capturas de tela do ICMIZER no artigo da 888poker (transcritas por cor de célula). "
             "Referência de menor precisão: transcrição de imagem, ante não totalmente documentado e um "
             "único gráfico para UTG e UTG+1 (comparado com as duas posições)."),
        "PROXY: PokerCoaching 'BB ante' chart vs our true 9-max BB ante":
            ("## 6. Nosso BB ante real vs. a tabela \"BB Ante\" da PokerCoaching",
             "Comparação informativa: o dinheiro morto é o mesmo (pote inicial de 2,5bb), mas na tabela da "
             "PokerCoaching todos pagam 0,1bb de ante, enquanto no BB ante real só o big blind paga 1bb — "
             "e por isso ele joga com 1bb a menos. As diferenças abaixo são o efeito dessa regra (mais fortes "
             "no SB e nos calls do BB), não erro de cálculo."),
    }
    for label, (title, desc) in labels.items():
        push_rows = mw["push"].get(label, [])
        call_rows = mw["call"].get(label, [])
        if not push_rows and not call_rows:
            continue
        md.append(title + "\n")
        md.append(desc + "\n")
        for kind, rows in (("Push", push_rows), ("Call", call_rows)):
            if not rows:
                continue
            n = len(rows)
            same = sum(1 for r in rows if r["n_diff"] == 0)
            nd = sum(r["n_diff"] for r in rows)
            hard = sum(len(r["hard_diff"]) for r in rows)
            mm = max_margin(rows)
            md.append(f"**{kind}:** {plural(n, 'range comparado', 'ranges comparados')}; "
                      f"{plural(same, 'idêntico', 'idênticos')} mão a mão; "
                      f"{plural(nd, 'mão diferente', 'mãos diferentes')} no total (média {num(nd / n)} por range); "
                      f"diferença média no % do range {num(sum(abs(r['our_pure_pct'] - r['ref_pct']) for r in rows) / n)} ponto"
                      + (f"; nas mãos que diferem, o nosso |EV(ação) − EV(fold)| é no máximo {margin_txt(mm)}" if nd else "")
                      + "." + "\n")
            oo = sum(len(r["only_ours"]) for r in rows)
            orf = sum(len(r["only_ref"]) for r in rows)
            if nd and not label.startswith("PROXY"):
                md.append(f"Direção das diferenças: {plural(oo, 'mão', 'mãos')} só no nosso range, "
                          f"{orf} só no da fonte.\n")
            # detail table for push (one line per position/stack) when small, else worst cases
            worst = sorted(rows, key=lambda r: -r["n_diff"])[:12]
            if kind == "Push" and n <= 16:
                worst = rows
            md.append("| Spot | Nós | Fonte | Mãos só nossas | Mãos só da fonte |")
            md.append("|---|---:|---:|---|---|")
            for r in worst:
                spot = (f"{r['position']} {pct(float(r['stack']))}bb" if kind == "Push"
                        else f"{r['caller']} vs {r['pusher']} {pct(float(r['stack']))}bb")
                md.append(f"| {spot} | {pct(r['our_pure_pct'])}% | {pct(r['ref_pct'])}% | "
                          f"{fmt_hands(r['only_ours']) or '—'} | {fmt_hands(r['only_ref']) or '—'} |")
            md.append("")
        if not label.startswith("PROXY"):
            allrows = push_rows + call_rows
            n = len(allrows)
            same = sum(1 for r in allrows if r["n_diff"] == 0)
            nd = sum(r["n_diff"] for r in allrows)
            ref_name = {"HRC blog 9-max 7.5bb, ante 0.1/player (no bunching)": "HRC 9-max 7,5bb (ante 0,1)",
                        "PokerCoaching app table 1 (10-handed, ante 0.1/player)": "PokerCoaching com ante, 5–15bb",
                        "PokerCoaching app table 0 (10-handed, no ante)": "PokerCoaching sem ante, 5–15bb",
                        "888poker / ICMIZER 9-max 12bb, ante 0.125/player": "ICMIZER 9-max 12bb (imagem)"}[label]
            mm = max_margin(allrows)
            app.append({"ref": ref_name,
                        "result": f"{n} ranges, {same} idênticos mão a mão; "
                                  + ((f"1 mão diferente, {margin_phrase(mm)}" if nd == 1 else
                                      f"{nd} mãos diferentes, todas {margin_phrase(mm)}") if nd else "nenhuma diferença")})
    md.append("## Como reproduzir\n")
    md.append("```\npython -m solver.run_all --n 2 --ante-type none --ante 0 --max-callers 1 "
              "--stacks 1.2:20:0.1 --tag hu_noante\npython -m solver.validate_hu\nsh data/run_chain.sh   "
              "# app + rodadas de validação\npython -m solver.validate_mw\npython -m solver.report_validation\n```\n")
    with open(os.path.join(ROOT, "VALIDACAO.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    note = ("Diferenças restantes ficam em mãos mistas ou a poucos centésimos de bb da indiferença; "
            "tabelas publicadas arredondam mãos mistas para push ou fold.")
    json.dump({"items": app, "note": note}, open(os.path.join(VAL, "summary_for_app.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n".join(md))


if __name__ == "__main__":
    main()
