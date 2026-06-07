import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useConversation } from '@elevenlabs/react';
import './SusiAgent.css';

const AGENT_ID = import.meta.env.VITE_AGENT_ID || 'agent_6001kmswk8etf5rrfknb32hamt1k';
// Optionaler serverseitiger Token-Endpoint (siehe src/server.js).
// Wenn gesetzt, wird WebRTC über einen kurzlebigen Conversation-Token aufgebaut,
// sodass der API-Key niemals im Browser landet.
const TOKEN_ENDPOINT = import.meta.env.VITE_TOKEN_ENDPOINT || '';

const STATUS_LABELS = {
  disconnected: 'Getrennt',
  connecting: 'Verbindet…',
  connected: 'Verbunden',
  disconnecting: 'Trennt…',
};

function formatTime(date) {
  return new Intl.DateTimeFormat('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

let messageIdCounter = 0;
function createMessage(type, text) {
  return { id: ++messageIdCounter, type, text, timestamp: new Date() };
}

function SusiAgent() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [volume, setVolume] = useState(0.8);
  const [muted, setMuted] = useState(false);
  const [errorBanner, setErrorBanner] = useState('');
  const [feedbackGiven, setFeedbackGiven] = useState(false);

  const messagesEndRef = useRef(null);

  const appendMessage = useCallback((type, text) => {
    setMessages((prev) => [...prev, createMessage(type, text)]);
  }, []);

  const conversation = useConversation({
    onConnect: () => {
      appendMessage('system', 'Mit Susi verbunden. Du kannst jetzt sprechen oder schreiben.');
      setErrorBanner('');
    },
    onDisconnect: () => {
      appendMessage('system', 'Verbindung zu Susi beendet.');
    },
    onMessage: (message) => {
      if (message?.user_transcription_event?.user_transcript) {
        appendMessage('user', message.user_transcription_event.user_transcript);
      }
      if (message?.agent_response_event?.agent_response) {
        appendMessage('agent', message.agent_response_event.agent_response);
      }
    },
    onError: (error) => {
      const text = error?.message || 'Unbekannter Fehler';
      console.error('Susi Agent Fehler:', error);
      setErrorBanner(text);
      appendMessage('error', text);
    },
    onModeChange: (mode) => {
      console.debug('Modus:', mode);
    },
  });

  const status = conversation.status;
  const isConnected = status === 'connected';
  const isBusy = status === 'connecting' || status === 'disconnecting';

  // Neue Nachrichten immer in den sichtbaren Bereich scrollen.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Lautstärke / Stummschaltung an die laufende Konversation weitergeben.
  useEffect(() => {
    if (!isConnected) return;
    conversation.setVolume({ volume: muted ? 0 : volume });
  }, [volume, muted, isConnected, conversation]);

  const fetchConversationToken = useCallback(async () => {
    if (!TOKEN_ENDPOINT) return null;
    const response = await fetch(TOKEN_ENDPOINT, { method: 'GET' });
    if (!response.ok) {
      throw new Error(`Token-Endpoint antwortete mit Status ${response.status}`);
    }
    const data = await response.json();
    return data.token || null;
  }, []);

  const startConversation = useCallback(async () => {
    setErrorBanner('');
    setFeedbackGiven(false);
    try {
      // Mikrofonzugriff anfragen – mit aussagekräftiger Fehlermeldung.
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (mediaError) {
        const reason =
          mediaError?.name === 'NotAllowedError'
            ? 'Mikrofonzugriff wurde verweigert. Bitte erlaube den Zugriff in den Browser-Einstellungen.'
            : 'Kein Mikrofon gefunden oder Zugriff nicht möglich.';
        setErrorBanner(reason);
        appendMessage('error', reason);
        return;
      }

      const token = await fetchConversationToken();

      if (token) {
        await conversation.startSession({ conversationToken: token, connectionType: 'webrtc' });
      } else {
        await conversation.startSession({ agentId: AGENT_ID, connectionType: 'webrtc' });
      }
    } catch (error) {
      const text = `Konversation konnte nicht gestartet werden: ${error?.message || error}`;
      console.error(text, error);
      setErrorBanner(text);
      appendMessage('error', text);
    }
  }, [appendMessage, conversation, fetchConversationToken]);

  const stopConversation = useCallback(async () => {
    try {
      await conversation.endSession();
    } catch (error) {
      console.error('Fehler beim Beenden:', error);
    }
  }, [conversation]);

  const sendMessage = useCallback(() => {
    const text = userInput.trim();
    if (!text || !isConnected) return;
    conversation.sendUserMessage(text);
    appendMessage('user', text);
    setUserInput('');
  }, [appendMessage, conversation, isConnected, userInput]);

  const handleFeedback = useCallback(
    (positive) => {
      try {
        conversation.sendFeedback(positive);
        setFeedbackGiven(true);
      } catch (error) {
        console.error('Feedback fehlgeschlagen:', error);
      }
    },
    [conversation],
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  const orbState = useMemo(() => {
    if (!isConnected) return 'idle';
    return conversation.isSpeaking ? 'speaking' : 'listening';
  }, [isConnected, conversation.isSpeaking]);

  const orbLabel = {
    idle: 'Bereit',
    listening: 'Hört zu',
    speaking: 'Spricht',
  }[orbState];

  return (
    <div className="agent-container">
      {errorBanner && (
        <div className="error-banner" role="alert">
          <span>⚠️ {errorBanner}</span>
          <button className="error-close" onClick={() => setErrorBanner('')} aria-label="Fehler schließen">
            ×
          </button>
        </div>
      )}

      <div className="status-bar">
        <div className={`orb orb-${orbState}`} aria-hidden="true">
          <span className="orb-core" />
        </div>
        <div className="status-text">
          <p className="status-line">
            Status: <strong>{STATUS_LABELS[status] || status}</strong>
          </p>
          <p className="agent-mode">{isConnected ? orbLabel : 'Nicht verbunden'}</p>
        </div>
      </div>

      <div className="conversation-box">
        <div className="messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">
              <p>👋 Hallo! Starte die Konversation, um mit Susi zu sprechen.</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`message ${msg.type}`}>
                <div className="message-header">
                  <span className="badge">{msg.type}</span>
                  <span className="message-time">{formatTime(msg.timestamp)}</span>
                </div>
                <p>{msg.text}</p>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="controls">
        <div className="button-group">
          <button
            onClick={startConversation}
            disabled={isConnected || isBusy}
            className="btn btn-primary"
          >
            {status === 'connecting' ? 'Verbindet…' : 'Konversation starten'}
          </button>
          <button
            onClick={stopConversation}
            disabled={!isConnected}
            className="btn btn-danger"
          >
            Konversation beenden
          </button>
          {messages.length > 0 && (
            <button onClick={clearMessages} className="btn btn-ghost">
              Verlauf löschen
            </button>
          )}
        </div>

        <div className="volume-group">
          <button
            className="btn btn-icon"
            onClick={() => setMuted((m) => !m)}
            disabled={!isConnected}
            aria-label={muted ? 'Ton einschalten' : 'Stummschalten'}
            title={muted ? 'Ton einschalten' : 'Stummschalten'}
          >
            {muted ? '🔇' : '🔊'}
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={muted ? 0 : volume}
            onChange={(e) => {
              setVolume(Number(e.target.value));
              if (muted) setMuted(false);
            }}
            disabled={!isConnected}
            aria-label="Lautstärke"
          />
          <span className="volume-value">{Math.round((muted ? 0 : volume) * 100)}%</span>
        </div>

        <div className="input-group">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Nachricht an Susi schreiben…"
            disabled={!isConnected}
          />
          <button
            onClick={sendMessage}
            disabled={!isConnected || !userInput.trim()}
            className="btn btn-secondary"
          >
            Senden
          </button>
        </div>

        {isConnected && (
          <div className="feedback-group">
            {feedbackGiven ? (
              <span className="feedback-thanks">Danke für dein Feedback!</span>
            ) : (
              <>
                <span className="feedback-label">War das hilfreich?</span>
                <button className="btn btn-ghost" onClick={() => handleFeedback(true)}>
                  👍 Ja
                </button>
                <button className="btn btn-ghost" onClick={() => handleFeedback(false)}>
                  👎 Nein
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default SusiAgent;
