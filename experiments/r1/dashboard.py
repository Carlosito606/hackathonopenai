"""One picture of R1 (team Vibers): the pipeline and the measured results, for people.

    python experiments/r1/dashboard.py docs/vibers-wyniki.png

Calibration numbers are read from runs/r1/20261031-0125-reactor-cal39 and the test run from ship/predictions.jsonl;
retrieval numbers are copied from the experiment notes named on the picture.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CAL = ROOT / "runs/r1/20261031-0125-reactor-cal39"
TYPES = [("single-session-user", "fakt od użytkownika"), ("single-session-assistant", "co powiedział asystent"),
         ("knowledge-update", "aktualna wartość"), ("multi-session", "łączenie / liczenie"),
         ("temporal-reasoning", "daty i odstępy"), ("abstention", "pytania bez odpowiedzi")]
GREEN, LIGHT, RED, BLUE, GREY = "#2e7d32", "#9ccc65", "#d32f2f", "#1565c0", "#607d8b"


def rj(p):
    return [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]


def calibration():
    ver = {v["question_id"]: v["verdict"] for v in rj(CAL / "verdicts.jsonl")}
    out = defaultdict(lambda: {"n": 0, "auto": 0, "read": 0, "wrong": 0})
    for r in rj(CAL / "details-new.jsonl"):
        x = out["abstention" if r["gold_abstain"] else r["question_type"]]
        x["n"] += 1
        if r["answer"] == "correct":
            x["auto"] += 1
        elif r["answer"] == "unjudged" and ver[r["question_id"]] == "correct":
            x["read"] += 1
        else:
            x["wrong"] += 1
    return out


def box(ax, x, y, w, h, text, color):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.02", fc=color, ec="none"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color="white", fontsize=10.5, wrap=True)


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18, color="#37474f", lw=1.6))


def main(out):
    fig = plt.figure(figsize=(16, 21), dpi=110, facecolor="white")
    fig.text(0.5, 0.982, "Vibers · Memory Retrieval Challenge · rakieta R1 HYBRID", ha="center", fontsize=22,
             weight="bold")
    fig.text(0.5, 0.968, "Jak działa system i co zmierzyliśmy (31.10.2026). Liczby z plików w repozytorium; źródło pod "
             "każdym wykresem.", ha="center", fontsize=12, color=GREY)

    # 1. pipeline
    ax = fig.add_axes([0.03, 0.77, 0.94, 0.185])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0, 0.97, "1. Jak to działa: od historii rozmów do odpowiedzi", fontsize=15, weight="bold", va="top")
    top = [("Historia użytkownika\n200 rozmów", GREY), ("Cięcie na wypowiedzi\n(okna ~900 znaków)", BLUE),
           ("Szukanie: słowa (BM25)\n+ znaczenie (bge)", BLUE), ("Sortowanie modelem\noceniającym (reranker)", BLUE),
           ("Okna dat i różne\nrozmowy przy liczeniu", BLUE)]
    bot = [("Materiał do 18 000 znaków\n+ odpowiedź użytkownika", "#6a1b9a"),
           ("Daty w kodzie:\n„[2023-06-10, day 161]”", "#6a1b9a"), ("Zasady odpowiedzi\n(pułapki, najnowsze)", "#6a1b9a"),
           ("Reactor (organizatorzy)\nodpowiada i cytuje", GREEN), ("Plik zgłoszenia\npredictions.jsonl", GREEN)]
    w, h = 0.17, 0.28
    xs = [0.005 + i * 0.2 for i in range(5)]
    for i, (t, c) in enumerate(top):
        box(ax, xs[i], 0.52, w, h, t, c)
        if i:
            arrow(ax, xs[i - 1] + w, 0.66, xs[i], 0.66)
    for i, (t, c) in enumerate(bot):
        box(ax, xs[i], 0.08, w, h, t, c)
        if i:
            arrow(ax, xs[i - 1] + w, 0.22, xs[i], 0.22)
    arrow(ax, xs[4] + w / 2, 0.52, xs[0] + w / 2, 0.36)

    # 2. calibration
    cal = calibration()
    ax = fig.add_axes([0.2, 0.47, 0.29, 0.25])
    labels = [f"{pl}\n({k})" for k, pl in TYPES]
    auto = [cal[k]["auto"] for k, _ in TYPES]
    read = [cal[k]["read"] for k, _ in TYPES]
    wrong = [cal[k]["wrong"] for k, _ in TYPES]
    y = range(len(TYPES))[::-1]
    ax.barh(y, auto, color=GREEN, label="dobrze (automat)")
    ax.barh(y, read, left=auto, color=LIGHT, label="dobrze (sprawdzone ręcznie)")
    ax.barh(y, wrong, left=[a + r for a, r in zip(auto, read)], color=RED, label="źle")
    for yi, k in zip(y, [k for k, _ in TYPES]):
        c = cal[k]
        ax.text(c["n"] + 0.15, yi, f"{c['auto'] + c['read']}/{c['n']}", va="center", fontsize=12, weight="bold")
    ax.set_yticks(list(y), labels, fontsize=9.5)
    ax.set_xlabel("liczba pytań")
    tot = {f: sum(cal[k][f] for k, _ in TYPES) for f in ("n", "auto", "read", "wrong")}
    fig.text(0.03, 0.735, f"2. Reactor na 39 pytaniach DEV (z wzorcami): {tot['auto'] + tot['read']}/{tot['n']} dobrze", fontsize=14, weight="bold")
    ax.legend(loc="lower right", bbox_to_anchor=(1.02, 0.0), fontsize=8.5, frameon=True, framealpha=0.95)
    ax.set_xlim(0, 16)
    ax.set_xticks(range(0, 10, 2))
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.03, 0.44, "Źródło: runs/r1/20261031-0125-reactor-cal39 (details-new, verdicts).\nLosowa próba dev bez puli holdout, po typach.", fontsize=9, color=GREY)

    # 3. test run
    preds = rj(ROOT / "ship/predictions.jsonl")
    ans = [p for p in preds if not p["abstain"]]
    ax = fig.add_axes([0.55, 0.47, 0.42, 0.25])
    ax.axis("off")
    ax.set_title("3. Finał na TEŚCIE (146 pytań, bez odpowiedzi wzorcowych)", fontsize=14, weight="bold", loc="left")
    rows = [(f"{len(preds)}/146", "pytań z odpowiedzią Reactora (0 błędów, 0 przekroczeń czasu)", GREEN),
            (f"{len(preds) - len(ans)} ({(len(preds) - len(ans)) / len(preds) * 100:.1f}%)".replace(".", ","), "odmów „brak informacji”; "
             "organizatorzy: ok. 8% pytań bez odpowiedzi", BLUE),
            (f"{sum(bool(p['citations']) for p in preds)}/146", "wierszy z cytatem (także każda odmowa)", GREEN),
            (f"{sum(len(p['citations']) for p in ans) / len(ans):.2f}".replace(".", ","), "rozmowy cytowane na odpowiedź", BLUE),
            ("75 s", "mediana czasu odpowiedzi Reactora (maks. 269 s)", GREY),
            ("01:37–05:57", "czas przebiegu (UTC), wszystko za pierwszym podejściem", GREY)]
    for i, (big, small, c) in enumerate(rows):
        yy = 0.9 - i * 0.165
        ax.text(0.0, yy, big, fontsize=22, weight="bold", color=c, va="center")
        ax.text(0.36, yy, small, fontsize=11, va="center", wrap=True)
    fig.text(0.55, 0.44, "Źródło: ship/predictions.jsonl, experiments/r1/20261031-0600-final-run.md.\nTrafności na teście nie znamy do ogłoszenia wyników.", fontsize=9, color=GREY)

    # 4. retrieval robustness
    rob = {  # experiments/r1/20261031-0210-final-dev-hard-v2-long.md: all gold sessions in the evidence pack
        "aktualna wartość": (1.000, 1.000, 0.983), "łączenie / liczenie": (0.969, 0.907, 0.825),
        "fakt od asystenta": (1.000, 1.000, 1.000), "fakt od użytkownika": (1.000, 1.000, 1.000),
        "daty i odstępy": (0.922, 0.833, 0.804), "WSZYSTKIE": (0.972, 0.935, 0.905)}
    ax = fig.add_axes([0.08, 0.18, 0.56, 0.2])
    names = list(rob)
    wbar = 0.26
    for j, (lab, col) in enumerate([("dev (50 rozmów)", "#90caf9"), ("dev z pułapkami", "#42a5f5"),
                                     ("z pułapkami, 200 rozmów (jak test)", "#0d47a1")]):
        vals = [rob[n][j] for n in names]
        bars = ax.bar([i + (j - 1) * wbar for i in range(len(names))], vals, wbar, color=col, label=lab)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.2f}".replace(".", ","),
                    ha="center", fontsize=8)
    ax.set_xticks(range(len(names)), names, fontsize=10)
    ax.set_ylim(0.7, 1.04)
    ax.set_ylabel("udział pytań z kompletem\nwłaściwych rozmów w materiale")
    fig.text(0.03, 0.415, "4. Czy wyszukiwanie znajduje właściwe rozmowy? (398 pytań dev)", fontsize=14, weight="bold")
    ax.legend(fontsize=9, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.03, 0.135, "Źródło: experiments/r1/20261031-0210-final-dev-hard-v2-long.md.\nPierwsza wersja R1 na danych z pułapkami: 0,889 ogółem, łączenie 0,753 (experiments/r1/20261030-2320-dev-hard.md).", fontsize=9, color=GREY)

    # 5. reactor vs stand-in, citations
    ax = fig.add_axes([0.71, 0.18, 0.26, 0.2])
    labs = ["odmowy\nzbędne\nQwen 7B", "odmowy\nzbędne\nReactor", "cytaty\nlinia\nkońcowa", "cytaty\n+ nasze\nobejście"]
    vals = [0.40, 0.0, 0.795, 0.910]
    cols = [RED, GREEN, "#90caf9", BLUE]
    bars = ax.bar(range(4), vals, color=cols)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.0%}" if v <= 0.4 else f"{v:.2f}".replace(".", ","),
                ha="center", fontsize=11, weight="bold")
    ax.set_xticks(range(4), labs, fontsize=9)
    ax.set_ylim(0, 1.05)
    fig.text(0.70, 0.415, "5. Reactor vs model zastępczy", fontsize=14, weight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.70, 0.105, "Źródło: experiments/r1/\n20261031-0010-reactor-calibration.md\n(35 pytań dev z odpowiedzią).", fontsize=9, color=GREY)

    # 6. what 37/39 means
    ax = fig.add_axes([0.03, 0.005, 0.94, 0.085])
    ax.axis("off")
    ax.text(0, 1, "6. Co znaczy „37/39”", fontsize=15, weight="bold", va="top")
    txt = (f"• 39 pytań ze zbioru DEV (nie test), odpowiadał prawdziwy Reactor. Oficjalny score.py: {tot['auto']} dobrze "
           f"od razu, {tot['read'] + 1} „nie umiem rozstrzygnąć”, 1 źle.\n"
           f"• Te {tot['read'] + 1} przeczytaliśmy ręcznie: {tot['read']} dobrze (np. „UCLA” przy wzorcu „University of "
           "California, Los Angeles (UCLA)”, „54” przy „54 days”), 1 źle.\n"
           "• Błędy: (1) pytanie o kolejność dwóch osób: Reactor wskazał złą osobę; (2) pytanie-pułapka bez odpowiedzi "
           "w historii: Reactor odpowiedział zamiast odmówić.\n"
           "• Na teście spodziewamy się mniej: dłuższe historie i celowe pułapki (wykres 4, ciemne słupki).")
    ax.text(0, 0.7, txt, fontsize=11, va="top", linespacing=1.6)

    fig.savefig(out, facecolor="white")
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/vibers-wyniki.png")
