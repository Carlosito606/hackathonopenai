# Hackathon Memory Challenge (zespół Vibers): każda maszyna buduje własne rozwiązanie, potem łączymy najlepsze

- **Co:** Pracujemy równolegle na kilku maszynach (Karol, Patryk, Patryk 2, Antoni). Każda maszyna buduje od zera do końca własne, kompletne rozwiązanie zadania z hackathonu („własna rakieta”). Podejścia mają się od siebie różnić, żeby pokryć jak najwięcej pomysłów. Potem testujemy wszystkie na tych samych danych i sprawdzamy, które poszło najlepiej. Na koniec bierzemy z każdego projektu to, co najlepsze, i łączymy w jedno rozwiązanie (permutacje najlepszych elementów). Wiedza krąży przez kanał agentów: gdy agent coś odkryje albo się na czymś wyłoży, od razu dzieli się tym na kanale.
- **Kto:** Patryk Wójcicki (polecenie dla wszystkich agentów zespołu).
- **Skąd:** rozmowa z agentem opencode 30.10.2026 („każda maszyna wybiera inne podejście… każdy ma swoją rakietę… agenci dzielą się eksperiencem… potem permutacje tych elementów”).
- **Data:** 30.10.2026
- **Status:** decyzja.

## Dopisek agenta (propozycja, status: do potwierdzenia)

- Mamy jednego agenta Reactora (slot t10) dla całego zespołu. Nowa historia u jednej osoby przerywa przebieg innej (`history_changed`). Propozycja: przebiegi Reactora ustawiamy w kolejce na kanale („zajmuję Reactora od–do”), a w czasie, gdy przebieg trwa, nikt inny nie wysyła `--new-history`. Każdy rozwija i testuje swoje rozwiązanie na lokalnym modelu.
- Dane dostępowe Reactora: tylko prywatnie w zespole, nigdy na kanale, w repozytorium ani na zrzutach ekranu.
- Porównanie rozwiązań: te same pytania dev bez puli `splits/dev_holdout.txt`, oficjalny `score.py`, wynik per typ pytania.
