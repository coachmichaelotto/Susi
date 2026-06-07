import React from 'react';
import SusiAgent from './components/SusiAgent';
import './App.css';

function App() {
  return (
    <div className="app">
      <header>
        <h1>Susi - ElevenLabs Conversational AI</h1>
        <p>Agent: Susi Bestandskunden</p>
      </header>
      <main>
        <SusiAgent />
      </main>
    </div>
  );
}

export default App;
