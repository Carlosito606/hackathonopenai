# Memory Retrieval Challenge: zespół Vibers, rakieta R1 HYBRID

Szkic prezentacji końcowej. Każdy slajd: tytuł, 3-5 punktów, notatka dla mówiącego. Liczby pochodzą tylko z plików
repozytorium podanych w nawiasach.

---

## Slajd 1. Zadanie i ocena

- Pytania o długie, zaszumione historie rozmów z wielu sesji; odpowiedź ma cytować identyfikatory sesji, na których
  się opiera, albo odmówić, gdy historii brakuje odpowiedzi (`AGENTS.md`, sekcja 1).
- Trzy miary: trafność odpowiedzi (sędzia LLM), F1 cytowanych sesji, poprawność odmowy (`AGENTS.md`, sekcja 1).
- Ostateczne odpowiedzi musi dać nasz agent Reactor, a dane wejściowe przygotowuje kod z tego repozytorium
  (`AGENTS.md`, sekcja 1; `README.md`).
- Wynik testu: <uzupełnić po przebiegu>

**Notatka:** Zaczynamy od tego, co jest oceniane: nie tylko odpowiedź, ale też dobre cytaty i umiejętność
powiedzenia „nie wiem”.

---

## Slajd 2. Dlaczego to trudne

- Duże historie: w dev ok. 50 sesji na historię, w dev-large ok. 470, w teście 200
  (`experiments/retrieval/20261031-0130-recall-audit.md`).
- Pytania bez odpowiedzi to „prawie trafienia”: jedna podmieniona rzecz albo brak połowy pytania; samo podobieństwo
  tekstu ich nie wykrywa (`AGENTS.md`, sekcja 1, findings w `coord/findings/`).
- Daty względne („wczoraj”, „w zeszły weekend”) liczą się od daty sesji, a ta sama sesja ma różne daty w różnych
  historiach (`coord/findings/20261030-2010-karol-claude-relative-dates.md`).
- Wartości się zmieniają, także w jednej sesji; wygrywa najnowsza wypowiedź użytkownika (`AGENTS.md`, sekcja 1).
- Sesje-pułapki o innych osobach i podobnych zdarzeniach (`coord/findings/20261030-2310-karol-claude-2-dev-hard-drop.md`).

**Notatka:** Trudność nie leży w samym wyszukiwaniu, tylko w odróżnieniu właściwej sesji od bardzo podobnej i w
poprawnym liczeniu dat.

---

## Slajd 3. Nasz potok (R1 HYBRID)

- Jednostka: tura rozmowy (długie tury cięte na okna ok. 900 znaków); BM25 + gęste wektory `bge-base-en-v1.5`,
  łączone przez RRF, top 80 przestawia reranker `bge-reranker-v2-m3` (`README.md`, punkt 1).
- Pytania o okres („w sierpniu”, „N dni temu”) dostają kandydatów z okna dat, a pytania liczące — po jednym
  fragmencie z większej liczby sesji (`experiments/retrieval/20261031-0130-recall-audit.md`,
  `coord/handoffs/2026-10-31-retrieval-recall-audit.md`).
- Daty liczone w kodzie: każda data w dowodach dostaje znacznik `[RRRR-MM-DD, day N]`, więc model tylko odejmuje
  numery dni; daty przybliżone mają dopisek „about” (`README.md`, punkt 3;
  `experiments/temporal/20261030-2308-date-coverage.md`).
- Notatki do odpowiedzi: uważaj na prawie trafienia, najnowsza wypowiedź wygrywa, jedna krótka odpowiedź z
  etykietami `[E#]`, odmowa tylko gdy nic nie podaje odpowiedzi (`README.md`, punkt 4).
- Cytaty: gdy Reactor pominie etykiety w ostatniej linii, bierzemy je z całej jego odpowiedzi
  (`experiments/r1/20261031-0010-reactor-calibration.md`).

**Notatka:** Model językowy dostaje mało, ale dobrze dobrane fragmenty, a rachunki na datach robi za niego kod.

---

## Slajd 4. Jak pracowaliśmy

- Flota rakiet: każda maszyna buduje jeden kompletny potok wokół innego pomysłu; najlepsze części łączymy na końcu
  (`coord/STRATEGIA-wiele-rakiet.md`, `rockets/README.md`).
- Wspólny kontrakt czterech etapów (retrieve, enrich, assemble, decide) i jeden sędzia: te same podziały, ten sam
  model zastępczy, ten sam `score.py` (`rockets/README.md`, sekcja „Why”; `AGENTS.md`, sekcje 6-7).
- Kanał agentów: lekcje i ślepe uliczki od razu dla wszystkich; trwałe ustalenia w `coord/findings/`
  (`AGENTS.md`, sekcja 4).
- Jeden Reactor dla całego zespołu: przebiegi tylko w zarezerwowanych oknach, klucz tylko u ludzi
  (`AGENTS.md`, sekcja 5).
- Podział dev-hard do testu odporności: pytania dev z 3-5 wstrzykniętymi sesjami-pułapkami
  (`rockets/poligon/README.md`).

**Notatka:** Wielu agentów pracowało równolegle; porządek trzymały wspólne zasady, jeden sędzia i kolejka do
Reactora.

---

## Slajd 5. Liczby: wyszukiwanie

- Dev, 150 pytań: R@5 0,965 → 0,982 po dodaniu rerankera; wszystkie sesje gold w wysłanych dowodach 0,980 → 0,988
  (`README.md`, tabela „Dev retrieval”).
- Dev, 300 pytań bez holdoutu: wszystkie sesje gold w dowodach 0,960 → 0,973; multi-session 0,930 → 0,972,
  temporal 0,899 → 0,913 (`experiments/retrieval/20261031-0130-recall-audit.md`).
- Skala: dev-large (ok. 470 sesji), 30 pytań: 0,833 → 0,867; tylko orientacyjnie, jedno pytanie to 3-10 punktów
  (`experiments/retrieval/20261031-0130-recall-audit.md`).
- Dev-hard (sam BM25, sesje gold w top 5): spadek o 13,1 pkt ogółem; multi-session −24,7, temporal −19,6
  (`rockets/poligon/README.md`).

**Notatka:** Na czystym dev wyszukiwanie jest prawie pełne; słabe miejsca to pytania z wielu sesji i o czas, gdy
pojawiają się pułapki.

---

## Slajd 6. Liczby: odpowiedzi na Reactorze

- Kalibracja na 39 pytaniach dev bez holdoutu (warstwowo po typach): 0 fałszywych odmów
  (`experiments/r1/20261031-0010-reactor-calibration.md`).
- Po ręcznym przeczytaniu odpowiedzi, których `score.py` nie rozstrzygnął: ok. 92-95% poprawnych
  (`experiments/r1/20261031-0010-reactor-calibration.md`).
- F1 cytatów 0,910 po dodaniu awaryjnego brania etykiet z całej odpowiedzi (0,795 z samej ostatniej linii)
  (`experiments/r1/20261031-0010-reactor-calibration.md`).
- Odmowy: 3 z 4 poprawne; pytanie z przesłanką, której nigdy nie było, wciąż dostaje odpowiedź
  (`experiments/r1/20261031-0010-reactor-calibration.md`).
- Pokrycie wyrażeń z datą znacznikami: dev 57% → 86%, test 37% → 67%
  (`experiments/temporal/20261030-2308-date-coverage.md`).

**Notatka:** Reactor dobrze czyta dobrze dobrane dowody; największe ryzyko to prawie trafienia, na które
odpowiada zamiast odmówić.

---

## Slajd 7. Czego się nauczyliśmy, co nie wyszło

- Model zastępczy 7B (Qwen2.5-7B) odmawiał w ok. połowie pytań czasowych (0,500), a Reactor w żadnym z 39; wyniki
  modelu zastępczego nie przewidują wyników Reactora (`experiments/temporal/20261030-2308-date-coverage.md`,
  `experiments/r1/20261031-0010-reactor-calibration.md`).
- Przykład odpowiedzi w instrukcji dla modelu pochodził z danych testowych; wykryliśmy go i zastąpiliśmy neutralnym
  `<answer>` (commit ee87794, `experiments/r1/20261031-0010-reactor-calibration.md`).
- Wspólny GPU: równoległe zadania na jednej maszynie były przerywane; część pomiarów zrobiliśmy na mniejszych
  próbkach (`experiments/retrieval/20261031-0130-recall-audit.md`, „Sample limits”).
- Nie przyjęliśmy: logitów rerankera jako progu (multi-session 0,930 → 0,718) ani różnicowania sesji dla każdego
  pytania (`experiments/retrieval/20261031-0130-recall-audit.md`, „Not adopted”).
- Najlepsze łączenie wyszukiwania zależy od typu pytania (`coord/findings/20261030-2330-karol-claude-fusion-depends-on-type.md`).

**Notatka:** Mierzyliśmy każdą zmianę i odrzucaliśmy te, które pomagały jednemu typowi pytań kosztem innych.

---

## Slajd 8. Co dalej

- Wybór taktyki wyszukiwania według typu pytania (rakieta R8 ROUTER w `rockets/README.md`;
  `coord/findings/20261030-2330-karol-claude-fusion-depends-on-type.md`).
- Sprawdzanie prawie trafień przed odpowiedzią: cała nazwa rzeczy, a nie tylko podobieństwo (R7 GUARDIAN w
  `rockets/README.md`).
- Liczenie w kodzie liczby dni między dwoma zdarzeniami, gdy oba mają znacznik daty
  (`coord/handoffs/2026-10-30-temporal-date-coverage.md`).
- Pomiar R1 na całym dev-hard i dev-large (`rockets/poligon/LOG.md`, `experiments/retrieval/20261031-0130-recall-audit.md`).
- Wynik testu: <uzupełnić po przebiegu>

**Notatka:** Kolejny zysk jest w odporności na pułapki i w liczeniu dat w kodzie, nie w samym wyszukiwaniu.
