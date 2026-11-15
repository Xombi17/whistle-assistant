import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, 
  Settings, 
  History, 
  Key, 
  Copy, 
  Check, 
  Trash2, 
  RefreshCw, 
  Sparkles, 
  Cpu, 
  Sliders, 
  Terminal, 
  Radio, 
  Layers,
  ChevronRight,
  ShieldCheck,
  Search,
  ExternalLink
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('history'); // 'history' | 'settings' | 'shortcuts'
  const [historyItems, setHistoryItems] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [config, setConfig] = useState({
    provider: 'groq',
    groq_api_key: '',
    groq_model: 'llama-3.3-70b-versatile',
    xai_api_key: '',
    xai_model: 'grok-beta',
    ollama_url: 'http://localhost:11434',
    ollama_model: 'qwen2.5-coder:7b'
  });
  const [saveStatus, setSaveStatus] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [systemStatus, setSystemStatus] = useState({
    audio_device: 'Detecting...',
    sample_rate: 16000,
    status: 'online'
  });

  // Audio spectrum visualizer animation
  const canvasRef = useRef(null);

  useEffect(() => {
    fetchHistory();
    fetchConfig();
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let tick = 0;

    const render = () => {
      tick++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barCount = 36;
      const barWidth = 4;
      const gap = (canvas.width - barCount * barWidth) / (barCount - 1);

      for (let i = 0; i < barCount; i++) {
        const x = i * (barWidth + gap);
        const centerDist = Math.sin((i / barCount) * Math.PI);
        const noise = Math.sin(tick * 0.15 + i * 0.5) * 0.5 + 0.5;
        const amplitude = isRecording 
          ? (centerDist * 28 + noise * 14 + 6)
          : (centerDist * 10 + noise * 4 + 2);

        // DeepSeek Electric Gradient: Cyan to Blue
        const gradient = ctx.createLinearGradient(0, canvas.height, 0, 0);
        gradient.addColorStop(0, '#00d2ff');
        gradient.addColorStop(0.7, '#3b82f6');
        gradient.addColorStop(1, '#a855f7');

        ctx.fillStyle = gradient;
        ctx.fillRect(x, canvas.height - amplitude, barWidth, amplitude);
      }
      animationId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationId);
  }, [isRecording]);

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/history');
      if (res.ok) {
        const data = await res.json();
        setHistoryItems(data);
        if (data.length > 0 && !selectedItem) {
          setSelectedItem(data[0]);
        }
      }
    } catch (e) {
      console.log('Running in standalone mode');
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch (e) {
      console.log('Using default config');
    }
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (e) {
      console.log('Status check failed');
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      if (res.ok) {
        setSaveStatus('SUCCESS // SETTINGS COMMITTED');
        setTimeout(() => setSaveStatus(''), 3000);
      }
    } catch (e) {
      setSaveStatus('ERROR // LOCAL SAVE ONLY');
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClearHistory = async () => {
    if (confirm('Clear all transcription history?')) {
      try {
        await fetch('/api/history/clear', { method: 'POST' });
        setHistoryItems([]);
        setSelectedItem(null);
      } catch (e) {}
    }
  };

  const triggerHud = async () => {
    try {
      await fetch('/api/trigger', { method: 'POST' });
    } catch (e) {}
  };

  const filteredHistory = historyItems.filter(item => 
    (item.formatted_text || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.raw_text || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex flex-col h-screen bg-[#070a12] text-slate-100 font-sans selection:bg-cyan-500/20 selection:text-cyan-300">
      
      {/* 1. DeepSeek Hardware Top Telemetry Chassis */}
      <header className="h-16 border-b border-[#1b253b] bg-[#0b101c]/90 backdrop-blur-md px-6 flex items-center justify-between z-10 shrink-0">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-cyan-500"></span>
            </span>
            <span className="font-mono text-xs font-bold tracking-widest text-slate-200">
              DEEPSEEK <span className="text-cyan-400">//</span> JARVIS CORE
            </span>
          </div>

          <div className="hidden md:flex items-center space-x-2 border-l border-[#1b253b] pl-4">
            <span className="bg-[#121a2c] text-cyan-400 text-[10px] font-mono px-2 py-0.5 rounded border border-cyan-500/20">
              16kHz MONO
            </span>
            <span className="bg-[#121a2c] text-slate-300 text-[10px] font-mono px-2 py-0.5 rounded border border-[#1b253b] max-w-[240px] truncate" title={systemStatus.audio_device}>
              MIC: {systemStatus.audio_device}
            </span>
            <span className="bg-[#121a2c] text-emerald-400 text-[10px] font-mono px-2 py-0.5 rounded border border-emerald-500/20">
              AI: {config.provider.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Action Button & Visualizer Header */}
        <div className="flex items-center space-x-4">
          <canvas ref={canvasRef} width={120} height={28} className="rounded bg-[#070a12]/50 border border-[#1b253b]" />
          
          <button 
            onClick={triggerHud}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono text-xs font-bold transition shadow-lg shadow-cyan-500/10 active:scale-95"
          >
            <Mic className="w-3.5 h-3.5" />
            <span>TRIGGER HUD</span>
          </button>
        </div>
      </header>

      {/* 2. Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* Left Hardware Navigation Rail */}
        <nav className="w-56 border-r border-[#1b253b] bg-[#090d18] flex flex-col justify-between p-3 shrink-0">
          <div className="space-y-1">
            <div className="px-3 py-2 text-[10px] font-mono font-bold tracking-wider text-slate-500 uppercase">
              Modules
            </div>

            <button
              onClick={() => setActiveTab('history')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-xs font-mono transition ${
                activeTab === 'history' 
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-bold' 
                  : 'text-slate-400 hover:bg-[#121a2c] hover:text-slate-200'
              }`}
            >
              <History className="w-4 h-4" />
              <span>CLIPBOARD HISTORY</span>
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-xs font-mono transition ${
                activeTab === 'settings' 
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-bold' 
                  : 'text-slate-400 hover:bg-[#121a2c] hover:text-slate-200'
              }`}
            >
              <Sliders className="w-4 h-4" />
              <span>AI SETTINGS & KEYS</span>
            </button>

            <button
              onClick={() => setActiveTab('shortcuts')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded text-xs font-mono transition ${
                activeTab === 'shortcuts' 
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-bold' 
                  : 'text-slate-400 hover:bg-[#121a2c] hover:text-slate-200'
              }`}
            >
              <Terminal className="w-4 h-4" />
              <span>KEYCAPS & GUIDE</span>
            </button>
          </div>

          {/* Bottom Telemetry Card */}
          <div className="bg-[#0e1422] p-3 rounded border border-[#1b253b] text-[10px] font-mono space-y-1 text-slate-400">
            <div className="text-cyan-400 font-bold flex items-center justify-between">
              <span>SYSTEM READY</span>
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
            </div>
            <div>STT // Whistle 16k</div>
            <div>LATENCY // ~240ms</div>
            <div className="text-slate-500 pt-1">HOTKEY: Super+Shift+J</div>
          </div>
        </nav>

        {/* Center Dynamic Content Area */}
        <main className="flex-1 bg-[#070a12] flex flex-col overflow-hidden">
          
          {/* TAB 1: CLIPBOARD HISTORY */}
          {activeTab === 'history' && (
            <div className="flex-1 flex overflow-hidden">
              
              {/* History Master List */}
              <div className="w-80 border-r border-[#1b253b] bg-[#080c16] flex flex-col">
                <div className="p-3 border-b border-[#1b253b] flex items-center justify-between gap-2">
                  <div className="relative flex-1">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Filter history..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full bg-[#0e1422] border border-[#1b253b] rounded pl-8 pr-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono placeholder:text-slate-600"
                    />
                  </div>
                  <button 
                    onClick={fetchHistory}
                    className="p-1.5 bg-[#0e1422] border border-[#1b253b] rounded text-slate-400 hover:text-cyan-400"
                    title="Refresh"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                  <button 
                    onClick={handleClearHistory}
                    className="p-1.5 bg-[#0e1422] border border-[#1b253b] rounded text-slate-400 hover:text-rose-400"
                    title="Clear All"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto divide-y divide-[#1b253b]/50">
                  {filteredHistory.length === 0 ? (
                    <div className="p-6 text-center text-xs font-mono text-slate-500">
                      NO DICTATION RECORDS FOUND
                    </div>
                  ) : (
                    filteredHistory.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => setSelectedItem(item)}
                        className={`p-3 cursor-pointer transition ${
                          selectedItem?.id === item.id 
                            ? 'bg-[#121929] border-l-2 border-cyan-400' 
                            : 'hover:bg-[#0c111f]'
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 mb-1">
                          <span className="text-cyan-400/80 font-bold uppercase">{item.mode || 'DICTATE'}</span>
                          <span>{new Date(item.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                        </div>
                        <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                          {item.formatted_text || item.raw_text}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* History Detail Inspector Pane */}
              <div className="flex-1 bg-[#070a12] p-6 flex flex-col overflow-y-auto">
                {selectedItem ? (
                  <div className="space-y-6 max-w-3xl">
                    <div className="flex items-center justify-between pb-4 border-b border-[#1b253b]">
                      <div>
                        <h2 className="text-sm font-mono font-bold text-slate-200">
                          TRANSCRIPT DETAIL // #{selectedItem.id}
                        </h2>
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(selectedItem.timestamp * 1000).toLocaleString()} · ENGINE: {selectedItem.provider || 'GROQ'}
                        </span>
                      </div>
                      
                      <button
                        onClick={() => copyToClipboard(selectedItem.formatted_text || selectedItem.raw_text, selectedItem.id)}
                        className="flex items-center space-x-2 px-3 py-1.5 rounded bg-[#121a2c] hover:bg-[#18233c] text-cyan-400 border border-cyan-500/30 text-xs font-mono font-bold transition"
                      >
                        {copiedId === selectedItem.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedId === selectedItem.id ? 'COPIED TO CLIPBOARD' : 'COPY BUFFER'}</span>
                      </button>
                    </div>

                    {/* AI Polished Final Text Card */}
                    <div className="bg-[#0b101c] rounded-lg p-5 border border-[#1b253b] shadow-xl space-y-2">
                      <div className="flex items-center space-x-2 text-[10px] font-mono text-cyan-400 font-bold">
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>WHISPERFLOW AI FORMATTED OUTPUT</span>
                      </div>
                      <div className="text-sm text-slate-100 font-sans leading-relaxed whitespace-pre-wrap select-all">
                        {selectedItem.formatted_text}
                      </div>
                    </div>

                    {/* Raw Audio Transcript Comparison */}
                    {selectedItem.raw_text && (
                      <div className="bg-[#090d18] rounded-lg p-4 border border-[#1b253b]/60 space-y-2">
                        <div className="text-[10px] font-mono text-slate-500 font-bold">
                          RAW WHISTLE STT INPUT
                        </div>
                        <div className="text-xs text-slate-400 font-mono leading-relaxed whitespace-pre-wrap">
                          {selectedItem.raw_text}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col items-center justify-center text-slate-600 font-mono text-xs space-y-2">
                    <Mic className="w-8 h-8 stroke-1 text-slate-700" />
                    <span>SELECT AN ITEM OR PRESS SUPER+SHIFT+J TO DICTATE</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: HARDWARE SETTINGS */}
          {activeTab === 'settings' && (
            <div className="flex-1 p-8 overflow-y-auto max-w-2xl space-y-6">
              <div className="pb-4 border-b border-[#1b253b]">
                <h1 className="text-base font-mono font-bold text-slate-100">
                  DEEPSEEK // HARDWARE ENGINE CONFIGURATION
                </h1>
                <p className="text-xs text-slate-400 mt-1">
                  Configure free cloud inference (Groq/xAI) or local models without GPU overhead.
                </p>
              </div>

              <form onSubmit={handleSaveConfig} className="space-y-6">
                
                {/* Engine Selector */}
                <div className="bg-[#0b101c] p-5 rounded-lg border border-[#1b253b] space-y-3">
                  <label className="block text-xs font-mono text-cyan-400 font-bold">
                    SELECT AI FORMATTING PROVIDER
                  </label>
                  <select
                    value={config.provider}
                    onChange={(e) => setConfig({ ...config, provider: e.target.value })}
                    className="w-full bg-[#070a12] border border-[#1b253b] rounded p-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="groq">Groq Cloud (Sub-second, Free Tier - Recommended)</option>
                    <option value="ollama">Local Ollama (qwen2.5-coder:7b)</option>
                    <option value="xai">xAI / Grok</option>
                    <option value="deterministic">Local Deterministic Rules (Instant, Offline)</option>
                  </select>
                </div>

                {/* Groq Cloud Settings */}
                <div className="bg-[#0b101c] p-5 rounded-lg border border-[#1b253b] space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-slate-200 flex items-center space-x-2">
                      <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                      <span>GROQ CLOUD (FREE API)</span>
                    </span>
                    <a 
                      href="https://console.groq.com/keys" 
                      target="_blank" 
                      rel="noreferrer"
                      className="text-[10px] font-mono text-cyan-400 hover:underline flex items-center space-x-1"
                    >
                      <span>GET FREE KEY</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>

                  <div className="space-y-2">
                    <label className="block text-[11px] font-mono text-slate-400">API Key</label>
                    <div className="relative">
                      <input
                        type={showKey ? "text" : "password"}
                        value={config.groq_api_key}
                        onChange={(e) => setConfig({ ...config, groq_api_key: e.target.value })}
                        placeholder="gsk_..."
                        className="w-full bg-[#070a12] border border-[#1b253b] rounded p-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500 placeholder:text-slate-700"
                      />
                      <button
                        type="button"
                        onClick={() => setShowKey(!showKey)}
                        className="absolute right-2.5 top-2 text-[10px] font-mono text-slate-500 hover:text-slate-300"
                      >
                        {showKey ? "HIDE" : "SHOW"}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="block text-[11px] font-mono text-slate-400">Model ID</label>
                    <input
                      type="text"
                      value={config.groq_model}
                      onChange={(e) => setConfig({ ...config, groq_model: e.target.value })}
                      className="w-full bg-[#070a12] border border-[#1b253b] rounded p-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>

                {/* Local Ollama Settings */}
                <div className="bg-[#0b101c] p-5 rounded-lg border border-[#1b253b] space-y-4">
                  <span className="text-xs font-mono font-bold text-slate-200 flex items-center space-x-2">
                    <Layers className="w-3.5 h-3.5 text-blue-400" />
                    <span>LOCAL OLLAMA INSTANCE</span>
                  </span>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[10px] font-mono text-slate-400">Host URL</label>
                      <input
                        type="text"
                        value={config.ollama_url}
                        onChange={(e) => setConfig({ ...config, ollama_url: e.target.value })}
                        className="w-full bg-[#070a12] border border-[#1b253b] rounded p-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-mono text-slate-400">Model Name</label>
                      <input
                        type="text"
                        value={config.ollama_model}
                        onChange={(e) => setConfig({ ...config, ollama_model: e.target.value })}
                        className="w-full bg-[#070a12] border border-[#1b253b] rounded p-2 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-4">
                  <button
                    type="submit"
                    className="px-6 py-2 rounded bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-mono text-xs font-bold transition shadow-lg shadow-cyan-500/10 active:scale-95"
                  >
                    COMMIT SETTINGS
                  </button>
                  {saveStatus && (
                    <span className="text-xs font-mono font-bold text-emerald-400 animate-pulse">
                      {saveStatus}
                    </span>
                  )}
                </div>
              </form>
            </div>
          )}

          {/* TAB 3: KEYCAPS & SHORTCUTS GUIDE */}
          {activeTab === 'shortcuts' && (
            <div className="flex-1 p-8 overflow-y-auto max-w-2xl space-y-6">
              <div className="pb-4 border-b border-[#1b253b]">
                <h1 className="text-base font-mono font-bold text-slate-100">
                  DEEPSEEK // TACTILE KEYBOARD SHORTCUTS
                </h1>
                <p className="text-xs text-slate-400 mt-1">
                  Global desktop bindings configured with Wayland & GNOME Mutter.
                </p>
              </div>

              <div className="space-y-4">
                <div className="bg-[#0b101c] p-5 rounded-lg border border-[#1b253b] space-y-3">
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1.5 font-mono text-xs font-bold">
                      <span className="bg-[#161f33] text-cyan-400 px-2.5 py-1 rounded border border-[#223150] shadow-inner">SUPER</span>
                      <span className="text-slate-500 py-1">+</span>
                      <span className="bg-[#161f33] text-cyan-400 px-2.5 py-1 rounded border border-[#223150] shadow-inner">SHIFT</span>
                      <span className="text-slate-500 py-1">+</span>
                      <span className="bg-[#161f33] text-cyan-400 px-2.5 py-1 rounded border border-[#223150] shadow-inner">J</span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">
                    <strong>Hold-to-Talk Dictation:</strong> Press and hold while speaking your thoughts. Release to automatically format via WhisperFlow AI and insert directly into your active window.
                  </p>
                </div>

                <div className="bg-[#0b101c] p-5 rounded-lg border border-[#1b253b] space-y-3">
                  <div className="flex items-center space-x-2 font-mono text-xs font-bold">
                    <span className="bg-[#161f33] text-purple-400 px-2.5 py-1 rounded border border-[#223150] shadow-inner">TAB</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">
                    <strong>Mode Toggle:</strong> Press Tab while the HUD is open to flip between pure <em>WhisperFlow Dictation</em> and <em>JARVIS Command Assistant</em>.
                  </p>
                </div>

                <div className="bg-[#0b101c] p-5 rounded-lg border border-[#1b253b] space-y-3">
                  <div className="flex items-center space-x-2 font-mono text-xs font-bold">
                    <span className="bg-[#161f33] text-slate-400 px-2.5 py-1 rounded border border-[#223150] shadow-inner">ESC</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">
                    <strong>Abort Action:</strong> Cancels recording or closes the confirmation HUD immediately.
                  </p>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
