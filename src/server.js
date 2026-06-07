/**
 * Minimaler Token-Server für ElevenLabs Conversational AI (WebRTC).
 *
 * Zweck: Der ElevenLabs API-Key bleibt ausschließlich auf dem Server.
 * Der Browser fordert über GET /api/token einen kurzlebigen
 * Conversation-Token an und baut damit die WebRTC-Verbindung auf.
 *
 * Start:  ELEVENLABS_API_KEY=... npm start
 */

import http from 'node:http';

const PORT = process.env.PORT || 8787;
const API_KEY = process.env.ELEVENLABS_API_KEY;
const AGENT_ID = process.env.AGENT_ID || 'agent_6001kmswk8etf5rrfknb32hamt1k';
// Im Produktivbetrieb auf die eigene Domain einschränken.
const ALLOWED_ORIGIN = process.env.ALLOWED_ORIGIN || '*';

if (!API_KEY) {
  console.error('Fehler: Umgebungsvariable ELEVENLABS_API_KEY ist nicht gesetzt.');
  process.exit(1);
}

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', ALLOWED_ORIGIN);
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

const server = http.createServer(async (req, res) => {
  setCors(res);

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === 'GET' && url.pathname === '/api/token') {
    try {
      const apiResponse = await fetch(
        `https://api.elevenlabs.io/v1/convai/conversation/token?agent_id=${AGENT_ID}`,
        { headers: { 'xi-api-key': API_KEY } },
      );

      if (!apiResponse.ok) {
        const detail = await apiResponse.text();
        res.writeHead(apiResponse.status, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'ElevenLabs Token-Anfrage fehlgeschlagen', detail }));
        return;
      }

      const data = await apiResponse.json();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ token: data.token }));
    } catch (error) {
      console.error('Token-Fehler:', error);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Interner Serverfehler' }));
    }
    return;
  }

  if (req.method === 'GET' && url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok' }));
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Nicht gefunden' }));
});

server.listen(PORT, () => {
  console.log(`Token-Server läuft auf http://localhost:${PORT}`);
  console.log(`  → GET /api/token   (Agent: ${AGENT_ID})`);
  console.log(`  → GET /health`);
});
