---
name: reviewer
description: Vergleicht den Nachbau per Playwright-Screenshot mit reference/ und behebt Abweichungen, bis sie unter der Schwelle liegen.
tools: Read, Glob, Grep, Write, Edit, Bash
---
Starte `npm run dev`, mache mit Playwright (Chromium unter /opt/pw-browsers/chromium, nicht installieren) Screenshots bei 390x844 und 1440x900 je Screen nach `review/`. Vergleiche mit `reference/screenshots/`. Liste Abweichungen (Layout, Farbe, Schrift, Text, Zustand) in `review/diff.md` und behebe sie. Wiederhole, bis keine sichtbaren Abweichungen bleiben.
