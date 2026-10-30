# Setup zespołu (dla ludzi)

1. **Właściciel repo (Carlosito606):**
   - Settings → Collaborators: każda osoba z rolą Write.
   - Settings → Branches → reguła dla `main`: Require a pull request (1 approval), Block force pushes.
   - Etykiety: `area:retrieval`, `area:temporal`, `area:verify`, `area:integration`, `area:analysis`,
     `type:idea`, `type:task`, `type:finding`, `type:bug`, `needs:reactor`, `status:claimed`, `status:blocked`.
2. **Obsada** (wpisać w `AGENTS.md`, sekcja 2):
   - lider dla każdego obszaru;
   - integrator (naturalnie zeemowo, autor pipeline'u);
   - operator Reactora: jedna osoba na każde agent id Reactora.
3. **Każda osoba i każde konto:** agent id `<osoba>-<vendor>[-n]`. Pierwsza wiadomość do agenta to uniwersalny
   prompt plus blok obszaru z `prompts/kickoff.md`, razem z numerem issue.
4. **Klucz Reactora** ma tylko operator. Reszta testuje przez `ask.py --local` na jednym wspólnym modelu
   zastępczym, wpisanym w `experiments/LEADERBOARD.md`.
5. **Rytm pracy:**
   - liderzy przeglądają pomysły co godzinę;
   - integrator merguje o pełnych godzinach i aktualizuje leaderboard;
   - kolejka Reactora jest obsługiwana po jednym zadaniu naraz, na `splits/reactor_mini.txt`.
6. **Test:** integrator rezerwuje Reactora z kilkugodzinnym zapasem przed deadline'em. W tym czasie Reactor nie
   przyjmuje żadnych innych zadań.
