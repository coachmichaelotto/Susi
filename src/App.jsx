import React from 'react';
import SusiAgent from './components/SusiAgent';
import './App.css';

function App() {
  return (
    <div className="app">
      <header>
        <h1>Susi – Urlaubsvertretung</h1>
        <p>Michael Otto · R+V Versicherung · Berliner Volksbank</p>
      </header>
      <main>
        <SusiAgent />
      </main>
    </div>
  );
}

export default App;
