import React, { useState } from 'react';
import SusiAgent from './components/SusiAgent';
import PKVBeratungsstrecke from './components/PKVBeratungsstrecke';
import './App.css';

const TABS = [
  { id: 'pkv', label: '🏥 PKV Beratungsstrecke', sub: 'Vorschau' },
  { id: 'susi', label: '🎙️ Susi Live Agent', sub: 'ElevenLabs' },
];

function App() {
  const [activeTab, setActiveTab] = useState('pkv');

  return (
    <div className="app">
      <header>
        <h1>Susi – KI-Beraterin</h1>
        <p>R+V Versicherung · PKV Beratungsstrecke</p>
        <div className="tab-bar">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
              <span className="tab-sub">{tab.sub}</span>
            </button>
          ))}
        </div>
      </header>
      <main>
        {activeTab === 'pkv' && <PKVBeratungsstrecke />}
        {activeTab === 'susi' && <SusiAgent />}
      </main>
    </div>
  );
}

export default App;
