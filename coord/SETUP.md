# Setup floty (dla ludzi)

## Kickoff (pierwsza godzina)
1. **Obsada** (wpisać w `rockets/README.md` i `AGENTS.md`, sekcja 2):
   - jedna maszyna (osoba) = jedna rakieta;
   - mission control: kontrakt, scoreboard, punkty synchronizacji, złożenie statku;
   - operator Reactora: jedna osoba na każde agent id Reactora;
   - POLIGON.
   R1 HYBRID zostaje u zeemowo.
2. **Każda maszyna:** agent id `<osoba>-<vendor>[-n]` dla każdej sesji. Pierwsza wiadomość do agenta to
   uniwersalny prompt z `prompts/kickoff.md`, uzupełniony o linię misji swojej rakiety.
3. **Wspólny model zastępczy** (jeden dla wszystkich, np. Qwen2.5-7B-Instruct) wpisać w
   `experiments/LEADERBOARD.md`. Bez tego wyniki rakiet nie będą porównywalne.
4. **Kanał agentów:** każdy agent dostaje do niego dostęp. Format wiadomości i zasady są w `coord/CHANNEL.md`.
5. **Organizatorzy:** zapytać, czy da się dostać więcej agent id Reactora. Każde dodatkowe podwaja przepustowość.
6. **GitHub:** ochrona `main` (wymagany PR, blokada force-push). PR-y zmieniające tylko `rockets/<slug>/`
   właściciel rakiety merguje sam.

## Rytm
- Punkt synchronizacji co ok. 3 h:
  - mission control publikuje scoreboard (`[SCORE]`);
  - każda rakieta może przejąć najwyżej jedną część oznaczoną `[PART-READY]`;
  - 2–3 rakiety dostają okno na Reactorze.
- W połowie lotu: decyzja o resecie najsłabszej rakiety.
- Dokowanie: `core/permlab.py` na artefaktach wszystkich rakiet, 3–5 kandydatów na statek na Reactor mini
  i dev-hard, jedna kontrola na holdoucie.
- Test na Reactorze: zarezerwowany z kilkugodzinnym zapasem przed deadline'em.
