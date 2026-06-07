import React, { useState } from 'react';
import { useConversation } from '@elevenlabs/react';
import './SusiAgent.css';

const AGENT_ID = import.meta.env.VITE_AGENT_ID || 'agent_6001kmswk8etf5rrfknb32hamt1k';

function SusiAgent() {
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');

  const conversation = useConversation({
    onConnect: () => {
      console.log('Connected to Susi Agent');
      setMessages(prev => [...prev, { type: 'system', text: 'Connected to Susi Agent' }]);
    },
    onDisconnect: () => {
      console.log('Disconnected from Susi Agent');
      setMessages(prev => [...prev, { type: 'system', text: 'Disconnected from Susi Agent' }]);
    },
    onMessage: (message) => {
      console.log('Message:', message);
      if (message.user_transcription_event) {
        setMessages(prev => [...prev, {
          type: 'user',
          text: message.user_transcription_event.user_transcript
        }]);
      }
      if (message.agent_response_event) {
        setMessages(prev => [...prev, {
          type: 'agent',
          text: message.agent_response_event.agent_response
        }]);
      }
    },
    onError: (error) => {
      console.error('Error:', error);
      setMessages(prev => [...prev, { type: 'error', text: `Error: ${error.message}` }]);
    },
    onModeChange: (mode) => {
      console.log('Mode:', mode);
    },
  });

  const startConversation = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      await conversation.startSession({
        agentId: AGENT_ID,
        connectionType: 'webrtc', // Low latency
      });
    } catch (error) {
      console.error('Failed to start conversation:', error);
      setMessages(prev => [...prev, { type: 'error', text: 'Failed to start conversation' }]);
    }
  };

  const sendMessage = async () => {
    if (userInput.trim()) {
      conversation.sendUserMessage(userInput);
      setMessages(prev => [...prev, { type: 'user', text: userInput }]);
      setUserInput('');
    }
  };

  return (
    <div className="agent-container">
      <div className="conversation-box">
        <div className="messages">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.type}`}>
              <span className="badge">{msg.type}</span>
              <p>{msg.text}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="controls">
        <div className="status">
          <p>Status: <strong>{conversation.status}</strong></p>
          <p>Agent is {conversation.isSpeaking ? '🔊 Speaking' : '👂 Listening'}</p>
        </div>

        <div className="button-group">
          <button
            onClick={startConversation}
            disabled={conversation.status === 'connected'}
            className="btn btn-primary"
          >
            Start Conversation
          </button>
          <button
            onClick={() => conversation.endSession()}
            disabled={conversation.status !== 'connected'}
            className="btn btn-danger"
          >
            Stop Conversation
          </button>
        </div>

        <div className="input-group">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Type a message..."
            disabled={conversation.status !== 'connected'}
          />
          <button
            onClick={sendMessage}
            disabled={conversation.status !== 'connected'}
            className="btn btn-secondary"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default SusiAgent;
