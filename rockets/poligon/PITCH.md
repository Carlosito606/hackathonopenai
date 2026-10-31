# POLIGON w prezentacji: gotowy slajd do docs/PRESENTATION.md (karol-claude-2)

Format jak w `docs/PRESENTATION.md`: tytuł, 3-5 punktów, notatka, źródła w nawiasach. Liczby tylko z plików repo.
Proponowane miejsce: po slajdzie 5 („Liczby: wyszukiwanie”).

---

## Slajd 5a. Poligon: uczciwy sprawdzian zamiast łatwego dev

- Dev jest łatwiejszy niż test: test celowo dokłada rozmowy-pułapki, ma 200 rozmów na historię i więcej pytań bez
  odpowiedzi (8% wobec 6%). Zbudowaliśmy dev-hard: każde pytanie dev dostaje 3-5 podobnych rozmów innych osób,
  które nie zawierają odpowiedzi, plus wersje bez odpowiedzi (usunięte dowody); 505 pytań, odtwarzalne co do bajtu
  na innym komputerze (`rockets/poligon/README.md`, `rockets/poligon/LOG.md`).
- Poligon sam się sprawdza: lokalny model (Qwen2.5-7B) próbuje odpowiedzieć z każdej wstrzykniętej rozmowy; 5,5%
  odpowiadało albo przeczyło wzorcowi (np. „chodzę na fitness 5 dni w tygodniu” przy wzorcu 4), więc v2 je wyrzuca
  (`rockets/poligon/README.md`, filtr 5).
- Pułapki trafiają do paczki dowodów w 99% pytań; pierwsza wersja R1 traciła na tym 6,3 pkt „wszystkich dowodów w
  paczce” (multi-session 0,918 → 0,753, temporal 0,892 → 0,804) (`experiments/r1/20261030-2320-dev-hard.md`).
  Historie długości testu (200 rozmów zamiast ok. 50) zabierają prostemu BM25 kolejne 3 pkt i po raz pierwszy
  psują też pytania z jednej rozmowy (`coord/findings/20261031-0235-karol-claude-2-test-length-noise.md`).
- Przyczyna to tłok, nie ranking: 21 z 29 zgubionych dowodów wraca po usunięciu pułapek z tej samej listy
  (`coord/findings/20261031-0115-karol-claude-2-r1-near-miss-displacement.md`). Lekarstwo: różnorodność sesji w
  paczce; w kodzie finałowym R1 multi-session na dev-hard 0,714 → 0,914 przy tym samym budżecie
  (`experiments/r1/20261031-0030-budget.md`, `coord/findings/20261031-0125-karol-claude-2-sessdiv-pack.md`).
  Kod finałowy R1 na poligonie: wszystkie dowody w paczce dev 0,972 → dev-hard 0,935 → historie długości testu
  0,905; straty z tłoku spadły z 23 do 7 (`coord/findings/20261031-0325-karol-claude-2-final-r1-robustness.md`).
- Lokalny sędzia dla odpowiedzi, których `score.py` nie rozstrzyga: 95% zgodności na 490 przypadkach o znanym
  wyniku i 21 z 22 zgodnych z oceną człowieka na prawdziwych odpowiedziach Reactora
  (`coord/findings/20261031-0315-karol-claude-2-judge-vs-human.md`).

**Notatka:** Nie ufaliśmy wynikom na łatwym dev. Poligon pokazał, gdzie potok pęka (pytania z wielu rozmów, gdy
pułapki zajmują miejsce w paczce), i to zmieniło kod finałowy, zanim cokolwiek poszło do Reactora.
