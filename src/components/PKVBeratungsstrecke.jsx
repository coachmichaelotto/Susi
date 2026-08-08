import React, { useState, useEffect, useRef } from 'react';
import './PKVBeratungsstrecke.css';

const STEPS = [
  { id: 1, label: 'Begrüßung', icon: '👋' },
  { id: 2, label: 'Qualifizierung', icon: '📋' },
  { id: 3, label: 'Bedarfsanalyse', icon: '🔍' },
  { id: 4, label: 'Wunschleistungen', icon: '⭐' },
  { id: 5, label: 'Tarifempfehlung', icon: '📊' },
  { id: 6, label: 'Abschluss', icon: '✅' },
];

const FLOW = [
  // Step 1: Begrüßung
  {
    step: 1,
    messages: [
      {
        from: 'susi',
        text: 'Guten Tag! Mein Name ist Susi, Ihre persönliche Beraterin bei der R+V Versicherung. Ich freue mich, Sie heute zu begleiten. Wie darf ich Sie ansprechen?',
      },
    ],
    input: {
      type: 'text',
      placeholder: 'Ihr Name...',
      key: 'name',
      label: 'Ihr Name',
    },
    nextText: 'Weiter',
    susiReply: (data) =>
      `Herzlich willkommen, ${data.name}! Ich bin heute für Sie da, um gemeinsam die beste private Krankenversicherung für Ihre individuelle Situation zu finden. Das dauert in der Regel nur 10–15 Minuten. Bereit?`,
  },
  // Step 2: Qualifizierung
  {
    step: 2,
    messages: [
      {
        from: 'susi',
        text: 'Damit ich Ihnen die passenden Tarife empfehlen kann, benötige ich zunächst einige Angaben zu Ihrer beruflichen Situation.',
      },
    ],
    input: {
      type: 'choice',
      key: 'beruf',
      label: 'Welche Beschäftigung trifft auf Sie zu?',
      options: [
        { value: 'angestellter', label: '💼 Angestellter / Arbeitnehmer' },
        { value: 'selbststaendiger', label: '🏢 Selbstständiger / Freiberufler' },
        { value: 'beamter', label: '⚖️ Beamter / Beamtenanwärter' },
        { value: 'sonstiges', label: '📌 Sonstiges' },
      ],
    },
    nextText: 'Weiter',
    susiReply: (data) => {
      const replies = {
        angestellter:
          'Perfekt. Als Angestellter können Sie in die PKV wechseln, wenn Ihr Bruttojahreseinkommen die Jahresarbeitsentgeltgrenze von 73.800 € (2025) übersteigt. Wir schauen uns das gemeinsam an.',
        selbststaendiger:
          'Großartig! Als Selbstständiger haben Sie freie Wahl zwischen GKV und PKV – und in der Regel die besten Möglichkeiten, von den Vorteilen der PKV zu profitieren.',
        beamter:
          'Sehr gut! Als Beamter erhalten Sie Beihilfe vom Dienstherrn – die PKV ergänzt diese ideal. Das ist die klassische und günstigste Lösung für Beamte.',
        sonstiges:
          'Kein Problem, wir finden gemeinsam die passende Lösung für Ihre Situation.',
      };
      return replies[data.beruf] || 'Danke für die Angabe!';
    },
  },
  // Step 3: Bedarfsanalyse
  {
    step: 3,
    messages: [
      {
        from: 'susi',
        text: 'Jetzt schauen wir uns Ihre persönliche Situation an. Das hilft mir, gezielt die richtigen Leistungen für Sie zusammenzustellen.',
      },
    ],
    input: {
      type: 'multi',
      key: 'bedarf',
      label: 'Was ist Ihnen bei Ihrer Krankenversicherung besonders wichtig?',
      options: [
        { value: 'chefarzt', label: '🏥 Chefarztbehandlung im Krankenhaus' },
        { value: 'einbettzimmer', label: '🛏️ Einbettzimmer im Krankenhaus' },
        { value: 'freie_arztwahl', label: '👨‍⚕️ Freie Arzt- und Spezialistenwahl' },
        { value: 'zahn', label: '🦷 Hochwertige Zahnversorgung' },
        { value: 'kurze_wartezeiten', label: '⏱️ Kurze Wartezeiten beim Arzt' },
        { value: 'ausland', label: '✈️ Weltweiter Krankenversicherungsschutz' },
      ],
    },
    nextText: 'Weiter',
    susiReply: (data) =>
      `Danke! Ich habe Ihre Wünsche notiert: ${(data.bedarf || [])
        .map((v) => ({ chefarzt: 'Chefarztbehandlung', einbettzimmer: 'Einbettzimmer', freie_arztwahl: 'Freie Arztwahl', zahn: 'Zahnversorgung', kurze_wartezeiten: 'Kurze Wartezeiten', ausland: 'Auslandsschutz' }[v]))
        .filter(Boolean)
        .join(', ')}. Darauf aufbauend stelle ich Ihnen gleich die optimalen Tarife vor.`,
  },
  // Step 4: Wunschleistungen
  {
    step: 4,
    messages: [
      {
        from: 'susi',
        text: 'Eine kurze Frage zum Budget: In welchem monatlichen Beitragsrahmen möchten Sie sich bewegen?',
      },
    ],
    input: {
      type: 'choice',
      key: 'budget',
      label: 'Monatlicher Beitrag (für Ihre Person)',
      options: [
        { value: 'niedrig', label: '💚 Bis 350 € / Monat – Basis-Schutz' },
        { value: 'mittel', label: '💛 350–550 € / Monat – Komfort-Schutz' },
        { value: 'hoch', label: '🔶 550–750 € / Monat – Premium-Schutz' },
        { value: 'max', label: '💎 Über 750 € / Monat – Top-Schutz' },
      ],
    },
    nextText: 'Tarife anzeigen',
    susiReply: (data) =>
      `Sehr gut! Mit einem Budget von ${
        { niedrig: 'bis 350 €', mittel: '350–550 €', hoch: '550–750 €', max: 'über 750 €' }[data.budget]
      } pro Monat kann ich Ihnen hervorragende Tarife zusammenstellen. Lassen Sie mich die Empfehlungen für Sie vorbereiten...`,
  },
  // Step 5: Tarifempfehlung
  {
    step: 5,
    messages: [
      {
        from: 'susi',
        text: 'Auf Basis Ihrer Angaben habe ich drei Tarife für Sie herausgesucht. Jeder Tarif ist auf Ihre Bedürfnisse abgestimmt.',
      },
    ],
    input: {
      type: 'tarife',
      key: 'tarif',
    },
    nextText: 'Angebot anfragen',
    susiReply: (data) =>
      `Ausgezeichnete Wahl! Der ${
        { basis: 'R+V BASIS', komfort: 'R+V KOMFORT', premium: 'R+V PREMIUM' }[data.tarif] || 'ausgewählte Tarif'
      } ist ideal für Ihre Situation. Ich bereite jetzt Ihr persönliches Angebot vor.`,
  },
  // Step 6: Abschluss
  {
    step: 6,
    messages: [
      {
        from: 'susi',
        text: 'Herzlichen Glückwunsch! Sie haben alle Schritte abgeschlossen. Ihr persönliches Angebot ist bereit.',
      },
    ],
    input: {
      type: 'abschluss',
    },
    nextText: null,
    susiReply: null,
  },
];

const TARIFE = [
  {
    id: 'basis',
    name: 'R+V BASIS',
    preis: '289 €',
    highlight: false,
    farbe: '#10b981',
    leistungen: [
      'Freie Arztwahl (Facharzt)',
      'Stationäre Grundversorgung',
      'Zahnersatz 60 %',
      '100 % ambulante Behandlung',
      'Sehhilfen bis 150 €',
    ],
  },
  {
    id: 'komfort',
    name: 'R+V KOMFORT',
    preis: '429 €',
    highlight: true,
    farbe: '#2563eb',
    leistungen: [
      'Chefarztbehandlung',
      'Einbettzimmer im Krankenhaus',
      'Zahnersatz 80 %',
      'Kieferorthopädie bis 3.000 €',
      'Weltweiter Krankenversicherungsschutz',
      'Naturheilkunde & alternative Medizin',
    ],
  },
  {
    id: 'premium',
    name: 'R+V PREMIUM',
    preis: '649 €',
    highlight: false,
    farbe: '#7c3aed',
    leistungen: [
      'Chefarzt & Wunschspezialist weltweit',
      'Einbettzimmer (international)',
      'Zahnersatz 100 %',
      'Kieferorthopädie unbegrenzt',
      'Kurleistungen & Präventionsprogramme',
      'Psychotherapie ohne Begrenzung',
      'Assistenzleistungen 24/7',
    ],
  },
];

export default function PKVBeratungsstrecke() {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState({});
  const [chatHistory, setChatHistory] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [multiSelected, setMultiSelected] = useState([]);
  const [choiceValue, setChoiceValue] = useState('');
  const [tarifSelected, setTarifSelected] = useState('');
  const [showReply, setShowReply] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [completed, setCompleted] = useState(false);
  const chatEndRef = useRef(null);

  const flow = FLOW[currentStep];

  useEffect(() => {
    if (currentStep < FLOW.length) {
      setIsTyping(true);
      const timer = setTimeout(() => {
        setIsTyping(false);
        const newMessages = FLOW[currentStep].messages.map((m) => ({ ...m, step: currentStep }));
        setChatHistory((prev) => [...prev, ...newMessages]);
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [currentStep]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isTyping]);

  const handleNext = () => {
    const key = flow.input?.key;
    let value;
    if (flow.input?.type === 'text') value = inputValue;
    else if (flow.input?.type === 'choice') value = choiceValue;
    else if (flow.input?.type === 'multi') value = multiSelected;
    else if (flow.input?.type === 'tarife') value = tarifSelected;

    if (!value || (Array.isArray(value) && value.length === 0)) return;

    const newData = { ...formData, [key]: value };
    setFormData(newData);

    // Add user message to chat
    let userText = '';
    if (flow.input?.type === 'text') userText = value;
    else if (flow.input?.type === 'choice') {
      const opt = flow.input.options?.find((o) => o.value === value);
      userText = opt ? opt.label : value;
    } else if (flow.input?.type === 'multi') {
      const labels = value.map((v) => flow.input.options?.find((o) => o.value === v)?.label).filter(Boolean);
      userText = labels.join(', ');
    } else if (flow.input?.type === 'tarife') {
      const t = TARIFE.find((t) => t.id === value);
      userText = t ? `${t.name} – ${t.preis}/Monat` : value;
    }

    setChatHistory((prev) => [...prev, { from: 'user', text: userText, step: currentStep }]);

    // Susi reply
    if (flow.susiReply) {
      setIsTyping(true);
      setTimeout(() => {
        setIsTyping(false);
        const replyText = flow.susiReply(newData);
        setChatHistory((prev) => [...prev, { from: 'susi', text: replyText, step: currentStep }]);
        setShowReply(true);

        setTimeout(() => {
          if (currentStep < FLOW.length - 1) {
            setCurrentStep((s) => s + 1);
            setInputValue('');
            setChoiceValue('');
            setMultiSelected([]);
            setTarifSelected('');
            setShowReply(false);
          } else {
            setCompleted(true);
          }
        }, 1200);
      }, 1200);
    }
  };

  const toggleMulti = (val) => {
    setMultiSelected((prev) =>
      prev.includes(val) ? prev.filter((v) => v !== val) : [...prev, val]
    );
  };

  const isNextDisabled = () => {
    if (isTyping || showReply) return true;
    const t = flow.input?.type;
    if (t === 'text') return !inputValue.trim();
    if (t === 'choice') return !choiceValue;
    if (t === 'multi') return multiSelected.length === 0;
    if (t === 'tarife') return !tarifSelected;
    return false;
  };

  const progress = Math.round(((currentStep) / (FLOW.length - 1)) * 100);

  return (
    <div className="pkv-container">
      {/* Header */}
      <div className="pkv-header">
        <div className="pkv-header-info">
          <div className="pkv-logo">
            <span className="pkv-logo-icon">🏥</span>
            <div>
              <div className="pkv-logo-title">PKV Beratungsstrecke</div>
              <div className="pkv-logo-sub">R+V Versicherung · Vorschau</div>
            </div>
          </div>
          <div className="pkv-progress-info">
            <span>Schritt {Math.min(currentStep + 1, STEPS.length)} von {STEPS.length}</span>
            <div className="pkv-progress-bar">
              <div className="pkv-progress-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Steps */}
      <div className="pkv-steps">
        {STEPS.map((step, idx) => (
          <div
            key={step.id}
            className={`pkv-step ${idx < currentStep ? 'done' : ''} ${idx === currentStep ? 'active' : ''}`}
          >
            <div className="pkv-step-icon">
              {idx < currentStep ? '✓' : step.icon}
            </div>
            <div className="pkv-step-label">{step.label}</div>
          </div>
        ))}
      </div>

      {/* Main layout */}
      <div className="pkv-main">
        {/* Chat */}
        <div className="pkv-chat">
          <div className="pkv-chat-messages">
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`pkv-msg pkv-msg--${msg.from}`}>
                {msg.from === 'susi' && (
                  <div className="pkv-msg-avatar">
                    <span>S</span>
                  </div>
                )}
                <div className="pkv-msg-bubble">
                  {msg.from === 'susi' && <div className="pkv-msg-name">Susi</div>}
                  <p>{msg.text}</p>
                </div>
                {msg.from === 'user' && (
                  <div className="pkv-msg-avatar pkv-msg-avatar--user">
                    <span>Sie</span>
                  </div>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="pkv-msg pkv-msg--susi">
                <div className="pkv-msg-avatar"><span>S</span></div>
                <div className="pkv-msg-bubble pkv-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input area */}
          {!isTyping && !showReply && !completed && flow && flow.input && (
            <div className="pkv-input-area">
              {flow.input.type === 'text' && (
                <div className="pkv-input-wrap">
                  <label className="pkv-input-label">{flow.input.label}</label>
                  <div className="pkv-input-row">
                    <input
                      type="text"
                      className="pkv-text-input"
                      placeholder={flow.input.placeholder}
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && !isNextDisabled() && handleNext()}
                      autoFocus
                    />
                  </div>
                </div>
              )}

              {flow.input.type === 'choice' && (
                <div className="pkv-input-wrap">
                  <label className="pkv-input-label">{flow.input.label}</label>
                  <div className="pkv-choice-grid">
                    {flow.input.options.map((opt) => (
                      <button
                        key={opt.value}
                        className={`pkv-choice-btn ${choiceValue === opt.value ? 'selected' : ''}`}
                        onClick={() => setChoiceValue(opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {flow.input.type === 'multi' && (
                <div className="pkv-input-wrap">
                  <label className="pkv-input-label">{flow.input.label} <em>(Mehrfachauswahl)</em></label>
                  <div className="pkv-choice-grid pkv-choice-grid--multi">
                    {flow.input.options.map((opt) => (
                      <button
                        key={opt.value}
                        className={`pkv-choice-btn ${multiSelected.includes(opt.value) ? 'selected' : ''}`}
                        onClick={() => toggleMulti(opt.value)}
                      >
                        {multiSelected.includes(opt.value) && <span className="pkv-check">✓ </span>}
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {flow.input.type === 'tarife' && (
                <div className="pkv-tarife-wrap">
                  {TARIFE.map((tarif) => (
                    <div
                      key={tarif.id}
                      className={`pkv-tarif ${tarif.highlight ? 'pkv-tarif--highlight' : ''} ${tarifSelected === tarif.id ? 'pkv-tarif--selected' : ''}`}
                      onClick={() => setTarifSelected(tarif.id)}
                      style={{ '--tarif-color': tarif.farbe }}
                    >
                      {tarif.highlight && <div className="pkv-tarif-badge">Empfohlen</div>}
                      <div className="pkv-tarif-name">{tarif.name}</div>
                      <div className="pkv-tarif-preis">{tarif.preis}<span>/Monat</span></div>
                      <ul className="pkv-tarif-leistungen">
                        {tarif.leistungen.map((l, i) => (
                          <li key={i}>✓ {l}</li>
                        ))}
                      </ul>
                      <div className="pkv-tarif-select-btn">
                        {tarifSelected === tarif.id ? '✓ Ausgewählt' : 'Auswählen'}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {flow.input.type !== 'abschluss' && (
                <button
                  className="pkv-next-btn"
                  onClick={handleNext}
                  disabled={isNextDisabled()}
                >
                  {flow.nextText || 'Weiter'} →
                </button>
              )}
            </div>
          )}

          {completed && (
            <div className="pkv-abschluss">
              <div className="pkv-abschluss-icon">🎉</div>
              <h3>Ihre Beratung ist abgeschlossen!</h3>
              <p>
                Susi hat alle Informationen erfasst. Ein R+V-Berater wird sich in Kürze mit Ihrem
                persönlichen Angebot bei Ihnen melden.
              </p>
              <div className="pkv-abschluss-actions">
                <div className="pkv-abschluss-item">
                  <span>📧</span> Angebot per E-Mail erhalten
                </div>
                <div className="pkv-abschluss-item">
                  <span>📞</span> Rückruf vereinbaren
                </div>
                <div className="pkv-abschluss-item">
                  <span>📄</span> Antrag direkt stellen
                </div>
              </div>
              <button
                className="pkv-restart-btn"
                onClick={() => {
                  setCurrentStep(0);
                  setFormData({});
                  setChatHistory([]);
                  setInputValue('');
                  setChoiceValue('');
                  setMultiSelected([]);
                  setTarifSelected('');
                  setShowReply(false);
                  setCompleted(false);
                }}
              >
                ↺ Neue Beratung starten
              </button>
            </div>
          )}
        </div>

        {/* Summary sidebar */}
        <div className="pkv-sidebar">
          <div className="pkv-sidebar-title">Ihre Angaben</div>
          {Object.keys(formData).length === 0 && (
            <p className="pkv-sidebar-empty">Noch keine Angaben erfasst.</p>
          )}
          {formData.name && (
            <div className="pkv-sidebar-item">
              <span className="pkv-sidebar-key">Name</span>
              <span className="pkv-sidebar-val">{formData.name}</span>
            </div>
          )}
          {formData.beruf && (
            <div className="pkv-sidebar-item">
              <span className="pkv-sidebar-key">Beruf</span>
              <span className="pkv-sidebar-val">
                {{ angestellter: 'Angestellter', selbststaendiger: 'Selbstständiger', beamter: 'Beamter', sonstiges: 'Sonstiges' }[formData.beruf]}
              </span>
            </div>
          )}
          {formData.bedarf && formData.bedarf.length > 0 && (
            <div className="pkv-sidebar-item pkv-sidebar-item--col">
              <span className="pkv-sidebar-key">Bedarf</span>
              <div className="pkv-tags">
                {formData.bedarf.map((v) => (
                  <span key={v} className="pkv-tag">
                    {{ chefarzt: 'Chefarzt', einbettzimmer: 'Einbettzimmer', freie_arztwahl: 'Freie Arztwahl', zahn: 'Zahn', kurze_wartezeiten: 'Wartezeiten', ausland: 'Ausland' }[v]}
                  </span>
                ))}
              </div>
            </div>
          )}
          {formData.budget && (
            <div className="pkv-sidebar-item">
              <span className="pkv-sidebar-key">Budget</span>
              <span className="pkv-sidebar-val">
                {{ niedrig: 'bis 350 €/Monat', mittel: '350–550 €/Monat', hoch: '550–750 €/Monat', max: 'über 750 €/Monat' }[formData.budget]}
              </span>
            </div>
          )}
          {formData.tarif && (
            <div className="pkv-sidebar-item">
              <span className="pkv-sidebar-key">Tarif</span>
              <span className="pkv-sidebar-val pkv-sidebar-val--highlight">
                {TARIFE.find((t) => t.id === formData.tarif)?.name}
              </span>
            </div>
          )}

          <div className="pkv-sidebar-divider" />
          <div className="pkv-sidebar-title">Über diese Vorschau</div>
          <p className="pkv-sidebar-info">
            Diese interaktive Vorschau zeigt, wie Susi Kunden durch eine PKV-Beratung führt.
            Im Live-Betrieb erfolgt die Beratung per Sprachdialog über die ElevenLabs-KI.
          </p>
        </div>
      </div>
    </div>
  );
}
