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
  RotateCcw
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

  // Clean, subtle audio visualizer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let tick = 0;

    const render = () => {
      tick++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const count = 16;
      const width = 3;
      const gap = (canvas.width - count * width) / (count - 1);

      for (let i = 0; i < count; i++) {
        const x = i * (width + gap);
        const center = Math.sin((i / count) * Math.PI);
        const noise = Math.sin(tick * 0.1 + i * 0.5) * 0.5 + 0.5;
        const h = Math.max(2, center * 8 + noise * 4);

        ctx.fillStyle = '#64748b';
        ctx.fillRect(x, (canvas.height - h) / 2, width, h);
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
        setSaveStatus('Saved');
        setTimeout(() => setSaveStatus(''), 2000);
      }
    } catch (e) {
      setSaveStatus('Error saving');
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
    <div className="flex h-screen w-screen bg-[#0e1015] text-[#e2e8f0] font-sans antialiased overflow-hidden select-none">
      
      {/* 1. SIDEBAR */}
      <aside className="w-72 bg-[#14171f] border-r border-[#222734] flex flex-col shrink-0">
        
        {/* App Title & Quick Add */}
        <div className="p-4 border-b border-[#222734] flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center text-white font-semibold text-xs shadow-sm">
              W
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-white leading-none">Whistle</h1>
              <p className="text-[11px] text-slate-400 mt-0.5">Voice Dictation</p>
            </div>
          </div>

          <button 
            onClick={triggerVoiceHud}
            title="Start voice dictation (Super + Shift + J)"
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition active:scale-95 shadow-sm"
          >
            <Mic className="w-3.5 h-3.5" />
            <span>Dictate</span>
          </button>
        </div>

        {/* Search */}
        <div className="px-3 pt-3 pb-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input 
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search transcript history..."
              className="w-full bg-[#1b202c] border border-[#2b3345] rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1 py-1">
          {filtered.length === 0 ? (
            <div className="p-6 text-center text-xs text-slate-500">
              No transcripts yet. Hold <kbd className="px-1 py-0.5 bg-[#1b202c] rounded border border-[#2b3345] text-slate-400 font-mono text-[10px]">Super+Shift+J</kbd> to record.
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
                  className={`group px-3 py-2.5 rounded-lg cursor-pointer transition text-xs flex items-start justify-between ${
                    isSelected 
                      ? 'bg-[#222a3b] text-white font-medium shadow-sm' 
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#181c26]'
                  }`}
                >
                  <div className="min-w-0 pr-2">
                    <p className="truncate text-slate-200 leading-snug">{title}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">
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
        <div className="p-3 border-t border-[#222734] bg-[#11141b] flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center space-x-2 min-w-0 pr-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>
            <span className="truncate text-[11px]" title={systemStatus.audio_device}>
              {systemStatus.audio_device.replace("Core Ultra 200H/200V Series Processors HD Audio ", "")}
            </span>
          </div>

          <button 
            onClick={() => setShowSettings(true)}
            className="p-1.5 hover:text-white rounded-md hover:bg-[#1c2230] transition shrink-0"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

      </aside>

      {/* 2. MAIN DOCUMENT WORKSPACE */}
      <main className="flex-1 flex flex-col bg-[#0e1015] overflow-hidden select-text">
        
        {/* Document Header Bar */}
        <header className="h-13 border-b border-[#222734] px-6 flex items-center justify-between bg-[#12151d] shrink-0 select-none">
          <div className="flex items-center space-x-4">
            <span className="text-xs text-slate-400 font-mono">
              {wordCount} words • {charCount} characters
            </span>
            {activeItem?.duration_sec && (
              <span className="text-[11px] text-slate-500 font-mono">
                Duration: {activeItem.duration_sec.toFixed(1)}s
              </span>
            )}
          </div>

          <div className="flex items-center space-x-3">
            {/* Raw Audio / Polished toggle */}
            {activeItem?.raw_text && (
              <button 
                onClick={() => setShowRaw(!showRaw)}
                className={`px-2.5 py-1 rounded text-xs transition border ${
                  showRaw 
                    ? 'bg-[#222a3b] border-[#3b4763] text-white' 
                    : 'border-[#222734] text-slate-400 hover:text-slate-200'
                }`}
              >
                {showRaw ? 'Show Formatted' : 'View Raw Speech'}
              </button>
            )}

            {/* Visualizer bar */}
            <canvas ref={canvasRef} width={60} height={16} className="opacity-70" />

            {/* Copy Button */}
            <button 
              onClick={() => handleCopyText(activeContent)}
              disabled={!activeContent}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 text-white text-xs font-medium transition active:scale-95 shadow-sm"
            >
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Text'}</span>
            </button>
          </div>
        </header>

        {/* Text Canvas */}
        <div className="flex-1 overflow-y-auto p-8 max-w-3xl mx-auto w-full">
          {activeItem ? (
            <div className="space-y-6">
              {showRaw ? (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                    Raw Acoustic Transcript
                  </h3>
                  <div className="p-4 rounded-xl bg-[#141720] border border-[#222734] font-mono text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
                    {activeItem.raw_text}
                  </div>
                </div>
              ) : (
                <div className="font-sans text-base text-slate-100 leading-relaxed whitespace-pre-wrap">
                  {activeItem.formatted_text || activeItem.raw_text}
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-3">
              <FileText className="w-8 h-8 text-slate-600" />
              <p className="text-sm">No dictation selected</p>
              <p className="text-xs text-slate-600 max-w-xs">
                Hold <kbd className="px-1.5 py-0.5 bg-[#171a23] rounded border border-[#252a39] text-slate-400 font-mono">Super + Shift + J</kbd> anywhere on your system to dictate.
              </p>
            </div>
          )}
        </div>

        {/* Bottom Quick Test Bar */}
        <div className="p-4 border-t border-[#222734] bg-[#12151d] select-none">
          <form onSubmit={handleManualSubmit} className="max-w-3xl mx-auto flex items-center space-x-2">
            <input 
              type="text"
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
              placeholder="Test WhisperFlow formatting directly (type raw text or Hinglish)..."
              className="flex-1 bg-[#181c26] border border-[#272f40] rounded-lg px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            <button
              type="submit"
              disabled={!manualText.trim() || isProcessing}
              className="px-3.5 py-2 rounded-lg bg-[#222a3b] hover:bg-[#2c374d] text-slate-200 text-xs font-medium disabled:opacity-40 transition"
            >
              Format
            </button>
          </form>
          <div className="text-center text-[11px] text-slate-500 mt-2 font-sans">
            Shortcut: <span className="text-slate-300">Super + Shift + J</span> (Hold to speak, release to insert into focused window)
          </div>
        </div>

      </main>

      {/* 3. SETTINGS MODAL */}
      {showSettings && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#141720] border border-[#272f40] rounded-xl shadow-2xl overflow-hidden flex flex-col">
            <div className="px-5 py-4 border-b border-[#222734] flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Whistle Settings</h2>
              <button 
                onClick={() => setShowSettings(false)}
                className="p-1 text-slate-400 hover:text-white rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveConfig} className="p-5 space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1.5">Formatting Provider</label>
                <select
                  value={config.provider}
                  onChange={(e) => setConfig({ ...config, provider: e.target.value })}
                  className="w-full bg-[#1b202c] border border-[#2b3345] rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                >
                  <option value="groq">Groq Cloud (Fastest inference)</option>
                  <option value="ollama">Ollama (Local offline)</option>
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
                    className="w-full bg-[#1b202c] border border-[#2b3345] rounded-lg px-3 py-2 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500"
                  />
                  <p className="text-[10px] text-slate-500 mt-1">
                    Used for Whisper-large-v3-turbo transcription and LLM text polishing.
                  </p>
                </div>
              )}

              {config.provider === 'ollama' && (
                <div>
                  <label className="block text-slate-300 font-medium mb-1.5">Ollama URL</label>
                  <input 
                    type="text"
                    value={config.ollama_url || 'http://localhost:11434'}
                    onChange={(e) => setConfig({ ...config, ollama_url: e.target.value })}
                    className="w-full bg-[#1b202c] border border-[#2b3345] rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                  />
                </div>
              )}

              <div className="pt-2 flex items-center justify-between">
                <span className="text-emerald-400 font-medium">{saveStatus}</span>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium transition"
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
