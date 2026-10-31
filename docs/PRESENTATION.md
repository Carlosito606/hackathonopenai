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
- Przebieg testu na Reactorze (31.10, 01:37-05:57 UTC): 146/146 odpowiedzi Reactora, 12 odmów (8,2%), każda
  odpowiedź z cytatem (średnio 1,57 sesji), mediana 75 s na pytanie (`README.md`, wiersz „final test run on
  Reactor”).
- Test nie ma odpowiedzi wzorcowych, więc trafności na teście jeszcze nie znamy. Czego się spodziewać: na 39
  pytaniach dev Reactor miał ok. 92-95% poprawnych i 0 fałszywych odmów
  (`experiments/r1/20261031-0010-reactor-calibration.md`), a na danych podobnych do testu dowodom brakuje sesji
  gold w ok. 18% pytań multi-session i 20% temporal (`experiments/r1/20261031-0210-final-dev-hard-v2-long.md`).

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
- Niezależny audyt: dwóch recenzentów GPT (tylko odczyt) sprawdziło dowody R1 dla wszystkich 146 pytań testu;
  do kodu trafiły tylko ogólne wzorce błędów, nic z treści testu (`experiments/r1/20261030-2300-gpt-audit-test-evidence.md`).

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
- Końcowy R1, 398 pytań w parach, wszystkie sesje gold w dowodach: dev 0,972, dev-hard v2 0,935, dev-hard-long
  (200 sesji na historię, jak w teście) 0,905; multi-session 0,969 / 0,907 / 0,825, temporal 0,922 / 0,833 / 0,804;
  pierwsza wersja R1 miała dev 0,952, dev-hard 0,889 (`experiments/r1/20261031-0210-final-dev-hard-v2-long.md`,
  `experiments/r1/20261030-2320-dev-hard.md`).
- Główne pozostałe ryzyko: pytania multi-session i temporal w historiach z 200 sesjami; dowodom brakuje tam sesji
  gold w ok. 18% i 20% pytań (`experiments/r1/20261031-0210-final-dev-hard-v2-long.md`).
- Dla porównania sam BM25 traci na dev-hard 13,1 pkt (`rockets/poligon/README.md`).

**Notatka:** Na czystym dev wyszukiwanie jest prawie pełne; słabe miejsca to pytania z wielu sesji i o czas, gdy
pojawiają się pułapki.

---

## Slajd 5a. Poligon: uczciwy sprawdzian zamiast łatwego dev

- Dev jest łatwiejszy niż test: test celowo dokłada rozmowy-pułapki i ma 200 rozmów na historię
  (`experiments/retrieval/20261031-0130-recall-audit.md`). Zbudowaliśmy dev-hard: każde pytanie dev dostaje 3-5 podobnych rozmów innych osób,
  które nie zawierają odpowiedzi, plus wersje bez odpowiedzi (usunięte dowody); 505 pytań, odtwarzalne co do bajtu
  na innym komputerze (`rockets/poligon/README.md`, `rockets/poligon/LOG.md`).
- Poligon sam się sprawdza: lokalny model (Qwen2.5-7B) próbuje odpowiedzieć z każdej wstrzykniętej rozmowy; 5,5%
  odpowiadało albo przeczyło wzorcowi (np. „chodzę na fitness 5 dni w tygodniu” przy wzorcu 4), więc v2 je wyrzuca
  (`rockets/poligon/README.md`, filtr 5).
- Pułapki trafiają do paczki dowodów w 99% pytań; pierwsza wersja R1 traciła na tym 6,3 pkt „wszystkich dowodów w
  paczce” (multi-session 0,918 → 0,753, temporal 0,892 → 0,804) (`experiments/r1/20261030-2320-dev-hard.md`).
- Przyczyna to tłok, nie ranking: 21 z 29 zgubionych dowodów wraca po usunięciu pułapek z tej samej listy
  (`coord/findings/20261031-0115-karol-claude-2-r1-near-miss-displacement.md`). Lekarstwo: różnorodność sesji w
  paczce; w kodzie finałowym R1 pytania liczące multi-session na dev-hard (70) 0,714 → 0,914 przy tym samym budżecie
  (`experiments/r1/20261031-0030-budget.md`, `coord/findings/20261031-0125-karol-claude-2-sessdiv-pack.md`).
- Lokalny sędzia dla odpowiedzi, których `score.py` nie rozstrzyga: 95% zgodności na 490 przypadkach o znanym
  wyniku (`rockets/poligon/LOG.md`).

**Notatka:** Nie ufaliśmy wynikom na łatwym dev. Poligon pokazał, gdzie potok pęka (pytania z wielu rozmów, gdy
pułapki zajmują miejsce w paczce), i to zmieniło kod finałowy, zanim cokolwiek poszło do Reactora.

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
- Audyt dowodów testu: 13 pytań OK, 14 z brakującą turą, 109 z mylącą pułapką obok właściwej odpowiedzi,
  10 bez odpowiedzi w historii, 0 z pominiętą datą; z tego wzięliśmy reguły o innych osobach i o planach,
  dołączanie następnej tury użytkownika i okna dat (`experiments/r1/20261030-2300-gpt-audit-test-evidence.md`).
- Najlepsze łączenie wyszukiwania zależy od typu pytania (`coord/findings/20261030-2330-karol-claude-fusion-depends-on-type.md`).
- Tania bramka przed odpowiedzią (R7: nazwy z pytania w dowodach + SQuAD 2.0) bez modelu łapie 13 z 25 pytań bez
  odpowiedzi na dev i 26 ze 107 na dev-hard przy 2 fałszywych odmowach na 398 (kandydaci BM25); z kandydatami R1:
  dev 13 z 25 przy 2/398, dev-hard 27 ze 107 przy 4/398; ale na 43 pytaniach, w których
  kazałaby odmówić, Reactor z naszymi notatkami sam odmówił w 41 (zysk 1, strata 1), więc nie weszła do
  zgłoszenia (`rockets/r7/README.md`, `rockets/r7/LOG.md`).

**Notatka:** Mierzyliśmy każdą zmianę i odrzucaliśmy te, które pomagały jednemu typowi pytań kosztem innych.

---

## Slajd 8. Co dalej

- Wybór taktyki wyszukiwania według typu pytania (rakieta R8 ROUTER w `rockets/README.md`;
  `coord/findings/20261030-2330-karol-claude-fusion-depends-on-type.md`).
- Prawie trafienia, które Reactor wciąż przepuszcza: tanie sygnały (obecność nazwy, pewność SQuAD) już nic nie
  dodają, a sesje-pułapki je oszukują (na pytaniach dev-hard z usuniętymi dowodami najlepsza odpowiedź SQuAD
  pochodziła z cudzej sesji w 30 z 32); potrzebne
  sprawdzenie, czy zdanie z odpowiedzią dotyczy tego użytkownika (`rockets/r7/LOG.md`).
- Liczenie w kodzie liczby dni między dwoma zdarzeniami, gdy oba mają znacznik daty
  (`coord/handoffs/2026-10-30-temporal-date-coverage.md`).
- Odporność multi-session na pułapki (dev-hard −16,5 pkt) i pomiar R1 na całym dev-large
  (`experiments/r1/20261030-2320-dev-hard.md`, `experiments/retrieval/20261031-0130-recall-audit.md`).
- Przebieg testu na Reactorze (31.10, 01:37-05:57 UTC): 146/146 odpowiedzi Reactora, 12 odmów (8,2%), każda
  odpowiedź z cytatem (średnio 1,57 sesji), mediana 75 s na pytanie (`README.md`, wiersz „final test run on
  Reactor”).
- Test nie ma odpowiedzi wzorcowych, więc trafności na teście jeszcze nie znamy. Czego się spodziewać: na 39
  pytaniach dev Reactor miał ok. 92-95% poprawnych i 0 fałszywych odmów
  (`experiments/r1/20261031-0010-reactor-calibration.md`), a na danych podobnych do testu dowodom brakuje sesji
  gold w ok. 18% pytań multi-session i 20% temporal (`experiments/r1/20261031-0210-final-dev-hard-v2-long.md`).

**Notatka:** Kolejny zysk jest w odporności na pułapki i w liczeniu dat w kodzie, nie w samym wyszukiwaniu.
