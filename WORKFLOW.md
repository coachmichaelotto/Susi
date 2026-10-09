# 1:1-Nachbau-Workflow

1. Material nach `reference/` legen: `screenshots/` (alle Schritte in Reihenfolge, 01-..., 02-...), `html/` (Seitenexport), optional `notes.md` (Logik, Integrationen).
2. `analyst` -> erzeugt `spec/`.
3. `builder` je Screen, parallel (Screen-Liste aus `spec/screens.md`).
4. `integrator` -> Funnel-Routing, utm, ElevenLabs/Make.
5. `reviewer` -> Screenshot-Vergleich und Korrektur, bis deckungsgleich.

Start in Claude Code: "Führe WORKFLOW.md aus" – die Agenten liegen in `.claude/agents/`.
