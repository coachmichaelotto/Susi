import React, { useState, useRef } from 'react';
import { useConversation } from '@elevenlabs/react';
import './SusiAgent.css';

const VACATION_AGENT_ID = import.meta.env.VITE_VACATION_AGENT_ID || 'agent_2101kzttd6y0fd0agf02sx7a4czc';

function SusiAgent() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [bookedAppointments, setBookedAppointments] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const conversation = useConversation({
    onConnect: () => {
      setMessages(prev => [...prev, {
        type: 'system',
        text: 'Verbunden mit Susi Urlaubsvertretung'
      }]);
    },
    onDisconnect: () => {
      setMessages(prev => [...prev, {
        type: 'system',
        text: 'Gespräch beendet'
      }]);
    },
    onMessage: (message) => {
      if (message.user_transcription_event) {
        setMessages(prev => [...prev, {
          type: 'user',
          text: message.user_transcription_event.user_transcript
        }]);
        scrollToBottom();
      }
      if (message.agent_response_event) {
        setMessages(prev => [...prev, {
          type: 'agent',
          text: message.agent_response_event.agent_response
        }]);
        scrollToBottom();
      }
      if (message.agent_tool_response) {
        const tool = message.agent_tool_response;
        if (tool.tool_name === 'book_appointment' && tool.response) {
          try {
            const result = JSON.parse(tool.response);
            if (result.success || result.status === 'booked') {
              setBookedAppointments(prev => [...prev, {
                name: result.customer_name || '',
                datetime: result.datetime || result.slot || '',
                concern: result.concern || '',
                timestamp: new Date().toLocaleString('de-DE')
              }]);
            }
          } catch {
            // Tool-Antwort kein JSON — ignorieren
          }
        }
      }
    },
    onError: (error) => {
      setMessages(prev => [...prev, {
        type: 'error',
        text: `Fehler: ${error.message}`
      }]);
    },
  });

  const startConversation = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      await conversation.startSession({
        agentId: VACATION_AGENT_ID,
        connectionType: 'webrtc',
      });
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        text: 'Mikrofon-Zugriff verweigert oder Verbindungsfehler.'
      }]);
    }
  };

  const sendMessage = () => {
    if (userInput.trim() && conversation.status === 'connected') {
      conversation.sendUserMessage(userInput);
      setUserInput('');
    }
  };

  return (
    <div className="agent-container">

      <div className="vacation-banner">
        <div className="vacation-icon">🤖</div>
        <div className="vacation-info">
          <strong>Susi – Digitale Assistentin</strong>
          <span>Nimmt Anliegen auf · vereinbart Termine · informiert Michael Otto per E-Mail</span>
        </div>
        <div className="agent-badge">
          <span>Susi</span>
          <span className="agent-badge-sub">KI-Assistentin</span>
        </div>
      </div>

      <div className="conversation-box">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-state">
              Gespräch starten, um Anliegen aufzunehmen
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.type}`}>
              <span className="badge">
                {msg.type === 'user' ? 'Anrufer' :
                 msg.type === 'agent' ? 'Susi' :
                 msg.type === 'error' ? 'Fehler' : 'System'}
              </span>
              <p>{msg.text}</p>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="controls">
        <div className="status">
          <div className="status-row">
            <span>Status:</span>
            <strong className={`status-value ${conversation.status}`}>
              {conversation.status === 'connected' ? 'Verbunden' :
               conversation.status === 'connecting' ? 'Verbindet…' : 'Getrennt'}
            </strong>
          </div>
          {conversation.status === 'connected' && (
            <div className="status-row">
              <span>Susi:</span>
              <strong>{conversation.isSpeaking ? '🔊 Spricht' : '👂 Hört zu'}</strong>
            </div>
          )}
        </div>

        <div className="button-group">
          <button
            onClick={startConversation}
            disabled={conversation.status === 'connected' || conversation.status === 'connecting'}
            className="btn btn-primary"
          >
            Gespräch starten
          </button>
          <button
            onClick={() => conversation.endSession()}
            disabled={conversation.status !== 'connected'}
            className="btn btn-danger"
          >
            Gespräch beenden
          </button>
        </div>

        {conversation.status === 'connected' && (
          <div className="input-group">
            <input
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Testnachricht eingeben…"
            />
            <button onClick={sendMessage} className="btn btn-secondary">
              Senden
            </button>
          </div>
        )}
      </div>

      {bookedAppointments.length > 0 && (
        <div className="appointments-box">
          <h3>Gebuchte Termine & Rückrufe</h3>
          {bookedAppointments.map((apt, idx) => (
            <div key={idx} className="appointment-item">
              <strong>{apt.name}</strong>
              <span>{apt.datetime}</span>
              {apt.concern && <span className="concern">{apt.concern}</span>}
              <span className="timestamp">Gebucht: {apt.timestamp}</span>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}

export default SusiAgent;
