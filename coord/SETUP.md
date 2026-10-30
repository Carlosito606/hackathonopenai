# Setup zespołu (dla ludzi, raz na start)

1. **Właściciel repo (Carlosito606):**
   - Settings → Collaborators: 3 osoby z rolą Write.
   - Settings → Branches → reguła dla `main`: Require a pull request (1 approval), Block force pushes.
2. **Przydział ról:** wpisać imiona w `AGENTS.md`, sekcja 2. Naturalny INTEGRATOR to autor obecnego pipeline'u
   (zeemowo), bo zna kod i jako pierwszy rozdziela `memsys.py`.
3. **Każda osoba:** klonuje repo, robi `pip install -r requirements.txt`, wrzuca dane do `../data/dev`, a jako
   pierwszą wiadomość do swojego agenta wkleja wspólny nagłówek i blok swojej roli z `prompts/kickoff.md`.
4. **Klucz Reactora** ma tylko INTEGRATOR. Reszta testuje przez `ask.py --local` z lokalnym modelem.
5. **Rytm pracy:** co 1–2 h mały PR od każdej osoby. INTEGRATOR merguje i aktualizuje tabelę wyników
   w `experiments/integrator/`.
