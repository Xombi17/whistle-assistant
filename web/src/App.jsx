import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, 
  Settings, 
  Search, 
  Copy, 
  Check, 
  Trash2, 
  Plus, 
  Sliders, 
  Volume2, 
  FileText, 
  X,
  Keyboard,
  RotateCcw,
  Sparkles,
  Command
} from 'lucide-react';

export default function App() {
  const [historyItems, setHistoryItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [manualText, setManualText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const [config, setConfig] = useState({
    provider: 'groq',
    groq_api_key: '',
    groq_model: 'openai/gpt-oss-120b',
    ollama_url: 'http://localhost:11434',
    ollama_model: 'qwen2.5-coder:7b'
  });
  const [saveStatus, setSaveStatus] = useState('');
  const [systemStatus, setSystemStatus] = useState({
    audio_device: 'Detecting microphone...',
    status: 'online'
  });

  const canvasRef = useRef(null);

  useEffect(() => {
    fetchHistory();
    fetchConfig();
    fetchStatus();

    const interval = setInterval(() => {
      fetchStatus();
      fetchHistory(true);
    }, 2500);

    return () => clearInterval(interval);
  }, []);

  // Smooth, organic 3D-feel audio wave
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let tick = 0;

    const render = () => {
      tick++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const count = 18;
      const width = 2.5;
      const gap = (canvas.width - count * width) / (count - 1);

      for (let i = 0; i < count; i++) {
        const x = i * (width + gap);
        const center = Math.sin((i / count) * Math.PI);
        const wave1 = Math.sin(tick * 0.08 + i * 0.35);
        const wave2 = Math.cos(tick * 0.05 + i * 0.2);
        const h = Math.max(3, center * 9 + (wave1 + wave2) * 2.5);

        // Smooth vertical gradient
        const grad = ctx.createLinearGradient(0, (canvas.height - h) / 2, 0, (canvas.height + h) / 2);
        grad.addColorStop(0, '#60a5fa');
        grad.addColorStop(1, '#2563eb');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(x, (canvas.height - h) / 2, width, h, 2);
        ctx.fill();
      }
      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, []);

  const fetchHistory = async (silent = false) => {
    try {
      const res = await fetch('/api/history');
      if (res.ok) {
        const data = await res.json();
        setHistoryItems(data);
        if (!selectedId && data.length > 0 && !silent) {
          setSelectedId(data[0].id);
        }
      }
    } catch (e) {}
  };

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(prev => ({ ...prev, ...data }));
      }
    } catch (e) {}
  };

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setSystemStatus(data);
      }
    } catch (e) {}
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
        setSaveStatus('Preferences saved');
        setTimeout(() => setSaveStatus(''), 2000);
      }
    } catch (e) {
      setSaveStatus('Error saving preferences');
    }
  };

  const triggerVoiceHud = async () => {
    try {
      await fetch('/api/trigger', { method: 'POST' });
    } catch (e) {}
  };

  const handleCopyText = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async (id, e) => {
    if (e) e.stopPropagation();
    try {
      await fetch('/api/history/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
      });
      const updated = historyItems.filter(item => item.id !== id);
      setHistoryItems(updated);
      if (selectedId === id) {
        setSelectedId(updated.length > 0 ? updated[0].id : null);
      }
    } catch (e) {}
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!manualText.trim() || isProcessing) return;

    const text = manualText.trim();
    setManualText('');
    setIsProcessing(true);

    try {
      const res = await fetch('/api/format', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      if (res.ok) {
        await fetchHistory();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsProcessing(false);
    }
  };

  const filtered = historyItems.filter(item => 
    (item.formatted_text || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.raw_text || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const activeItem = historyItems.find(item => item.id === selectedId) || historyItems[0];
  const activeContent = activeItem?.formatted_text || activeItem?.raw_text || '';
  const wordCount = activeContent.trim() ? activeContent.trim().split(/\s+/).length : 0;
  const charCount = activeContent.length;

  return (
    <div className="flex h-screen w-screen bg-[#0b0d13] text-[#e2e8f0] font-sans antialiased overflow-hidden select-none">
      
      {/* 1. LEFT SIDEBAR */}
      <aside className="w-72 bg-[#10131a] border-r border-[#1e2330] flex flex-col shrink-0">
        
        {/* App Title & Quick Add */}
        <div className="p-4 border-b border-[#1e2330] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-blue-700 via-blue-600 to-indigo-500 flex items-center justify-center text-white font-semibold text-xs shadow-md shadow-blue-500/20 border border-white/10">
              W
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-white leading-none">Whistle</h1>
              <p className="text-[10px] text-slate-400 mt-0.5 font-medium">Voice Dictation</p>
            </div>
          </div>

          <button 
            onClick={triggerVoiceHud}
            title="Start voice dictation (Super + Shift + J)"
            className="glass-button flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-white text-xs font-medium cursor-pointer"
          >
            <Mic className="w-3.5 h-3.5" />
            <span>Dictate</span>
          </button>
        </div>

        {/* Search */}
        <div className="px-3 pt-3 pb-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input 
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search transcript history..."
              className="w-full bg-[#151922] border border-[#222938] rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/70 transition"
            />
          </div>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1 py-1">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No transcripts yet. Hold <kbd className="px-1.5 py-0.5 bg-[#171c26] rounded border border-[#252c3c] text-slate-400 font-mono text-[10px]">Super+Shift+J</kbd> to record.
            </div>
          ) : (
            filtered.map((item) => {
              const isSelected = item.id === selectedId;
              const title = item.formatted_text?.slice(0, 38) || item.raw_text?.slice(0, 38) || 'Untitled';
              const dateStr = item.created_at ? item.created_at.slice(11, 16) : '';

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={`group px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-150 text-xs flex items-start justify-between relative overflow-hidden ${
                    isSelected 
                      ? 'bg-gradient-to-r from-[#1c2230] to-[#161a25] text-white font-medium border border-blue-500/30 shadow-md shadow-black/40' 
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#151922]/70 border border-transparent'
                  }`}
                >
                  {/* Subtle active left accent indicator */}
                  {isSelected && (
                    <div className="absolute left-0 top-1 bottom-1 w-0.5 bg-blue-500 rounded-r"></div>
                  )}

                  <div className="min-w-0 pr-2 pl-0.5">
                    <p className="truncate text-slate-200 leading-snug">{title}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5 font-mono">
                      {dateStr} • {item.duration_sec ? `${item.duration_sec.toFixed(1)}s` : 'Voice'}
                    </p>
                  </div>
                  <button 
                    onClick={(e) => handleDelete(item.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 rounded transition shrink-0"
                    title="Delete item"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Status & Settings Footer */}
        <div className="p-3 border-t border-[#1e2330] bg-[#0d0f15] flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2 min-w-0 pr-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0 shadow-sm shadow-emerald-500/30"></span>
            <span className="truncate text-[11px] font-mono text-slate-400" title={systemStatus.audio_device}>
              {systemStatus.audio_device.replace("Core Ultra 200H/200V Series Processors HD Audio ", "")}
            </span>
          </div>

          <button 
            onClick={() => setShowSettings(true)}
            className="p-1.5 hover:text-white rounded-lg hover:bg-[#181d28] transition shrink-0 text-slate-400"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

      </aside>

      {/* 2. MAIN DOCUMENT WORKSPACE */}
      <main className="flex-1 flex flex-col bg-[#0b0d13] overflow-hidden select-text">
        
        {/* Document Header Bar */}
        <header className="h-12 border-b border-[#1e2330] px-6 flex items-center justify-between bg-[#0e1117] shrink-0 select-none">
          <div className="flex items-center space-x-3 text-xs text-slate-400 font-mono">
            <span>{wordCount} words</span>
            <span className="text-slate-600">•</span>
            <span>{charCount} characters</span>
            {activeItem?.duration_sec && (
              <>
                <span className="text-slate-600">•</span>
                <span className="text-slate-500">{activeItem.duration_sec.toFixed(1)}s audio</span>
              </>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {/* Raw Audio / Polished toggle */}
            {activeItem?.raw_text && (
              <button 
                onClick={() => setShowRaw(!showRaw)}
                className={`px-2.5 py-1 rounded-lg text-xs transition border cursor-pointer ${
                  showRaw 
                    ? 'bg-[#1e2433] border-blue-500/30 text-blue-300' 
                    : 'border-[#222938] text-slate-400 hover:text-slate-200 hover:bg-[#161a24]'
                }`}
              >
                {showRaw ? 'Formatted' : 'Raw Speech'}
              </button>
            )}

            {/* Smooth 3D Canvas visualizer */}
            <canvas ref={canvasRef} width={64} height={16} className="opacity-80" />

            {/* Copy Button */}
            <button 
              onClick={() => handleCopyText(activeContent)}
              disabled={!activeContent}
              className="glass-button flex items-center space-x-1.5 px-3 py-1.5 rounded-lg disabled:opacity-40 text-white text-xs font-medium cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-300" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </header>

        {/* Text Canvas */}
        <div className="flex-1 overflow-y-auto p-10 max-w-3xl mx-auto w-full">
          {activeItem ? (
            <div className="space-y-6">
              {showRaw ? (
                <div className="glass-card p-5 rounded-2xl">
                  <h3 className="text-xs font-medium uppercase tracking-wider text-slate-400 mb-2">
                    Raw Acoustic Transcription
                  </h3>
                  <div className="font-mono text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {activeItem.raw_text}
                  </div>
                </div>
              ) : (
                <div className="glass-panel p-8 rounded-2xl">
                  <div className="font-sans text-base text-slate-100 leading-relaxed whitespace-pre-wrap selection:bg-blue-600/30 selection:text-blue-200">
                    {activeItem.formatted_text || activeItem.raw_text}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-[#141822] border border-[#222838] flex items-center justify-center text-slate-400 shadow-lg shadow-black/30">
                <FileText className="w-5 h-5" />
              </div>
              <p className="text-sm font-medium text-slate-300">Ready to dictate</p>
              <p className="text-xs text-slate-500 max-w-xs leading-normal">
                Press and hold <kbd className="px-1.5 py-0.5 bg-[#171c26] rounded border border-[#262f40] text-slate-300 font-mono">Super + Shift + J</kbd> anywhere on your system. Release to paste directly into your active window.
              </p>
            </div>
          )}
        </div>

        {/* Bottom Quick Test Bar */}
        <div className="p-4 border-t border-[#1e2330] bg-[#0e1117] select-none">
          <form onSubmit={handleManualSubmit} className="max-w-2xl mx-auto flex items-center space-x-2">
            <input 
              type="text"
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
              placeholder="Test WhisperFlow normalization (paste raw speech or Hinglish)..."
              className="flex-1 bg-[#151922] border border-[#232938] rounded-xl px-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/70 transition shadow-inner"
            />
            <button
              type="submit"
              disabled={!manualText.trim() || isProcessing}
              className="px-4 py-2 rounded-xl bg-[#1d2331] hover:bg-[#252c3d] text-slate-200 text-xs font-medium border border-[#2b3345] disabled:opacity-40 transition cursor-pointer active:scale-95"
            >
              Normalize
            </button>
          </form>
          <div className="text-center text-[10px] text-slate-500 mt-2 font-sans">
            Global Hotkey: <span className="text-slate-400 font-medium">Super + Shift + J</span> (Hold to speak, release to paste)
          </div>
        </div>

      </main>

      {/* 3. SETTINGS MODAL */}
      {showSettings && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-md glass-panel rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            <div className="px-5 py-4 border-b border-[#222938] flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Whistle Settings</h2>
              <button 
                onClick={() => setShowSettings(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveConfig} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Transcription & Formatting Engine</label>
                <select
                  value={config.provider}
                  onChange={(e) => setConfig({ ...config, provider: e.target.value })}
                  className="w-full bg-[#151922] border border-[#262f40] rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="groq">Groq Cloud (Whisper Large v3 + Fast Inference)</option>
                  <option value="ollama">Ollama (Local Offline LLM)</option>
                </select>
              </div>

              {config.provider === 'groq' && (
                <div>
                  <label className="block text-slate-300 font-medium mb-1.5">Groq API Key</label>
                  <input 
                    type="password"
                    value={config.groq_api_key || ''}
                    onChange={(e) => setConfig({ ...config, groq_api_key: e.target.value })}
                    placeholder="gsk_..."
                    className="w-full bg-[#151922] border border-[#262f40] rounded-xl px-3 py-2 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">
                    Enables Whisper-large-v3-turbo cloud transcription and intelligent Hinglish auto-correction.
                  </p>
                </div>
              )}

              {config.provider === 'ollama' && (
                <div>
                  <label className="block text-slate-300 font-medium mb-1.5">Ollama Server URL</label>
                  <input 
                    type="text"
                    value={config.ollama_url || 'http://localhost:11434'}
                    onChange={(e) => setConfig({ ...config, ollama_url: e.target.value })}
                    className="w-full bg-[#151922] border border-[#262f40] rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
              )}

              <div className="pt-2 flex items-center justify-between">
                <span className="text-emerald-400 font-medium font-mono text-[11px]">{saveStatus}</span>
                <button
                  type="submit"
                  className="glass-button px-4 py-2 rounded-xl text-white font-medium cursor-pointer"
                >
                  Save Settings
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
