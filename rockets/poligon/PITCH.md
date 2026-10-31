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

Wykres do slajdu: `rockets/poligon/r1-robustness.svg` (pierwszy i zgłoszony R1, wszystkie dowody w paczce: dev,
dev-hard, historie długości testu; razem i multi-session). W markdownie: `![R1 na poligonie](../rockets/poligon/r1-robustness.svg)`.

**Notatka:** Nie ufaliśmy wynikom na łatwym dev. Poligon pokazał, gdzie potok pęka (pytania z wielu rozmów, gdy
pułapki zajmują miejsce w paczce), i to zmieniło kod finałowy, zanim cokolwiek poszło do Reactora.

---

## Tekst do powiedzenia (ok. 1 minuty)

„Zbiór dev, na którym wszyscy testowali, jest łatwiejszy niż test. Test celowo dokłada rozmowy, które wyglądają na
właściwe, ale nie zawierają odpowiedzi, i ma cztery razy dłuższe historie. Dlatego zbudowaliśmy poligon: do każdego
pytania z dev dokładamy trzy do pięciu podobnych rozmów innych osób. Lokalny model sprawdza każdą taką rozmowę i
wyrzuca te, które przypadkiem odpowiadają na pytanie, żeby poligon był uczciwy.

Na poligonie pierwsza wersja naszego potoku gubiła dowody w pytaniach z wielu rozmów: pułapki zajmowały miejsce w
paczce, którą wysyłamy do Reactora. Gdy to zobaczyliśmy, potok zaczął brać fragmenty z większej liczby różnych
rozmów. Straty z tego powodu spadły z 23 do 7, a zgłoszony potok traci na poligonie tylko 3,8 punktu.

Pokazało to też, co dalej: przy historiach długości testu brakujące dowody to głównie parafrazy, czyli rozmowy
opisujące to samo innymi słowami. Tam jest następny zysk.”

Liczby do pytań z sali: dev 0,972 → poligon 0,935 → historie długości testu 0,905 (wszystkie dowody w paczce,
398 pytań); sędzia lokalny zgodny z człowiekiem w 21 z 22 odpowiedzi Reactora.
