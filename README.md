# Susi – ElevenLabs Conversational AI Agent

Susi Bestandskunden ist ein Sprach-Assistent auf Basis von ElevenLabs
Conversational AI. Dieses Repository enthält eine React-Web-App (Vite)
mit WebRTC-Sprachverbindung sowie einen optionalen Token-Server, damit der
API-Key niemals im Browser landet.

**Agent ID:** `agent_6001kmswk8etf5rrfknb32hamt1k`

## Features der Web-App

- 🎙️ Echtzeit-Sprachkonversation über **WebRTC** (niedrige Latenz)
- 💬 Zusätzliche **Texteingabe** an den Agenten
- 🟢 Animierter **Status-Orb** (Bereit / Hört zu / Spricht)
- 🔊 **Lautstärkeregler** und Stummschaltung
- 👍 **Feedback**-Buttons (Daumen hoch/runter)
- 🕑 Nachrichtenverlauf mit Zeitstempeln und Auto-Scroll
- ⚠️ Klare Fehlermeldungen (z.B. bei verweigertem Mikrofonzugriff)
- 🔐 Optionaler **Token-Server** – der API-Key bleibt serverseitig

## Quick Start

### 1. Abhängigkeiten installieren

```bash
npm install
```

### 2. Umgebungsvariablen anlegen

`.env` aus der Vorlage erstellen:

```bash
cp .env.example .env
```

> ⚠️ **Sicherheitshinweis:** Der ElevenLabs API-Key darf **nicht** mit dem
> `VITE_`-Präfix gesetzt werden – sonst landet er im Browser-Bundle.
> Nutze für den Key den serverseitigen Token-Server (siehe unten).

### 3a. Variante A – ohne Server (öffentlicher Agent)

Funktioniert sofort für öffentliche Agenten, ganz ohne API-Key im Browser:

```bash
npm run dev
```

Im Code wird auf die `agentId` zurückgefallen, wenn kein Token-Endpoint
gesetzt ist.

### 3b. Variante B – mit Token-Server (empfohlen für Produktion)

In einem Terminal den Token-Server starten:

```bash
ELEVENLABS_API_KEY=dein_key npm run server
```

In einem zweiten Terminal die Web-App starten:

```bash
npm run dev
```

Der Vite-Dev-Server leitet `/api/token` automatisch an den Token-Server
(Port `8787`) weiter. Setze `VITE_TOKEN_ENDPOINT=/api/token` in der `.env`,
damit die App den serverseitigen Token nutzt.

## Umgebungsvariablen

| Variable               | Seite   | Beschreibung                                            |
| ---------------------- | ------- | ------------------------------------------------------- |
| `VITE_AGENT_ID`        | Client  | Agent-ID (Fallback ohne Token-Server)                   |
| `VITE_TOKEN_ENDPOINT`  | Client  | URL für den WebRTC-Token, z.B. `/api/token`             |
| `ELEVENLABS_API_KEY`   | Server  | **Geheim** – nur serverseitig                           |
| `AGENT_ID`             | Server  | Agent-ID für die Token-Anfrage                          |
| `PORT`                 | Server  | Port des Token-Servers (Standard `8787`)                |
| `ALLOWED_ORIGIN`       | Server  | CORS-Origin (in Produktion auf eigene Domain begrenzen) |

## Weitere Integrationsmethoden

Der Agent lässt sich auch ohne diese App einbinden:

1. **React SDK** (`@elevenlabs/react`) – diese App
2. **React Native SDK** (`@elevenlabs/react-native`) – mobile Apps
3. **Embeddable Widget** (`@elevenlabs/convai-widget`) – Drop-in HTML-Komponente
4. **Python SDK** (`elevenlabs`) – Backend / CLI
5. **Direct WebSocket** – `wss://api.elevenlabs.io/v1/convai/conversation`
6. **WebRTC** – produktionsreife, latenzarme Sprachverbindung

## Projektstruktur

```
.
├── src/
│   ├── components/
│   │   ├── SusiAgent.jsx     # Konversations-UI (Sprache + Text)
│   │   └── SusiAgent.css
│   ├── App.jsx
│   ├── main.jsx
│   └── server.js            # Optionaler Token-Server (WebRTC)
├── index.html
├── package.json
├── vite.config.js           # Dev-Proxy /api -> Token-Server
└── README.md
```

## Dokumentation

- [Full Documentation](https://elevenlabs.io/docs/eleven-agents)
- [API Reference](https://elevenlabs.io/docs/api-reference/introduction)
- [Agents API](https://elevenlabs.io/docs/api-reference/agents/get)
- [Conversations API](https://elevenlabs.io/docs/api-reference/conversations/get)

## Lizenz

MIT
