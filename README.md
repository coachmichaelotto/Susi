# Susi - ElevenLabs Conversational AI Agent

Susi Bestandskunden is a conversational AI agent powered by ElevenLabs.

**Agent ID:** `agent_6001kmswk8etf5rrfknb32hamt1k`

## Integration Methods

This repository contains implementations for multiple integration approaches:

1. **React SDK** - Web applications with WebRTC support
2. **React Native SDK** - Mobile applications
3. **Embeddable Widget** - Drop-in HTML component
4. **Python SDK** - Backend and CLI applications
5. **Direct WebSocket** - Custom implementations
6. **WebRTC** - Low-latency production deployments

## Quick Start

### React Web Integration

```bash
npm install
npm run dev
```

### Environment Setup

Create a `.env` file with your ElevenLabs API key:

```
VITE_ELEVENLABS_API_KEY=your_api_key_here
VITE_AGENT_ID=agent_6001kmswk8etf5rrfknb32hamt1k
```

## Documentation

- [Full Documentation](https://elevenlabs.io/docs/eleven-agents)
- [API Reference](https://elevenlabs.io/docs/api-reference/introduction)
- [Agents API](https://elevenlabs.io/docs/api-reference/agents/get)
- [Conversations API](https://elevenlabs.io/docs/api-reference/conversations/get)

## Project Structure

```
.
├── src/
│   ├── components/
│   │   └── SusiAgent.jsx
│   ├── App.jsx
│   └── main.jsx
├── public/
├── package.json
├── vite.config.js
└── README.md
```

## License

MIT
