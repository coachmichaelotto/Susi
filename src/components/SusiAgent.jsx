import React, { useState, useRef, useEffect } from 'react';
import { useConversation } from '@elevenlabs/react';
import './SusiAgent.css';

const AGENT_ID = import.meta.env.VITE_AGENT_ID || 'agent_6001kmswk8etf5rrfknb32hamt1k';

function SusiAgent() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const messagesEndRef = useRef(null);

  const conversation = useConversation({
    onConnect: () => {
      setMessages(prev => [...prev, { type: 'system', text: 'Verbunden mit Susi', ts: Date.now() }]);
    },
    onDisconnect: () => {
      setMessages(prev => [...prev, { type: 'system', text: 'Verbindung getrennt', ts: Date.now() }]);
    },
    onMessage: (message) => {
      if (message.user_transcription_event) {
        setMessages(prev => [...prev, {
          type: 'user',
          text: message.user_transcription_event.user_transcript,
          ts: Date.now(),
        }]);
      }
      if (message.agent_response_event) {
        setMessages(prev => [...prev, {
          type: 'agent',
          text: message.agent_response_event.agent_response,
          ts: Date.now(),
        }]);
      }
    },
    onError: (error) => {
      setMessages(prev => [...prev, { type: 'error', text: error.message, ts: Date.now() }]);
    },
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startConversation = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      await conversation.startSession({ agentId: AGENT_ID, connectionType: 'webrtc' });
    } catch {
      setMessages(prev => [...prev, { type: 'error', text: 'Mikrofon-Zugriff verweigert', ts: Date.now() }]);
    }
  };

  const sendMessage = async () => {
    const text = userInput.trim();
    if (!text) return;
    conversation.sendUserMessage(text);
    setMessages(prev => [...prev, { type: 'user', text, ts: Date.now() }]);
    setUserInput('');
  };

  const isConnected = conversation.status === 'connected';
  const isSpeaking = conversation.isSpeaking;

  const formatTime = (ts) =>
    new Date(ts).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="susi-container">

      <div className="susi-status-bar">
        <div className={`status-dot ${isConnected ? (isSpeaking ? 'speaking' : 'listening') : 'offline'}`} />
        <span className="status-label">
          {!isConnected && 'Nicht verbunden'}
          {isConnected && isSpeaking && 'Susi spricht …'}
          {isConnected && !isSpeaking && 'Hört zu …'}
        </span>
        {isConnected && isSpeaking && (
          <div className="sound-wave">
            <span /><span /><span /><span /><span />
          </div>
        )}
      </div>

      <div className="susi-messages">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🎙️</div>
            <p>Starte ein Gespräch mit Susi</p>
            <p className="empty-hint">Klicke auf „Gespräch starten" und sprich einfach los.</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`bubble-row ${msg.type}`}>
            {msg.type === 'agent' && <div className="avatar agent-avatar">S</div>}
            <div className="bubble">
              <p>{msg.text}</p>
              <span className="bubble-time">{formatTime(msg.ts)}</span>
            </div>
            {msg.type === 'user' && <div className="avatar user-avatar">Du</div>}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="susi-controls">
        <div className="action-buttons">
          <button
            onClick={startConversation}
            disabled={isConnected}
            className="btn btn-start"
            title="Gespräch starten"
          >
            <span className="btn-icon">🎙️</span>
            Gespräch starten
          </button>
          <button
            onClick={() => conversation.endSession()}
            disabled={!isConnected}
            className="btn btn-stop"
            title="Gespräch beenden"
          >
            <span className="btn-icon">⏹</span>
            Beenden
          </button>
        </div>

        <div className="text-input-row">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Nachricht eingeben …"
            disabled={!isConnected}
          />
          <button
            onClick={sendMessage}
            disabled={!isConnected || !userInput.trim()}
            className="btn btn-send"
          >
            Senden
          </button>
        </div>
      </div>

    </div>
  );
}

export default SusiAgent;
