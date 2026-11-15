import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, 
  Settings, 
  Search, 
  Copy, 
  Check, 
  Trash2, 
  Sliders, 
  Volume2, 
  FileText, 
  X,
  Sparkles,
  Command,
  Activity,
  Layers,
  Radio,
  Clock,
  ArrowRight,
  ShieldCheck,
  Cpu
} from 'lucide-react';

export default function App() {
  const [historyItems, setHistoryItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [copied, setCopied] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [viewMode, setViewMode] = useState('formatted'); // 'formatted' | 'diff' | 'raw'
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
    audio_device: 'PipeWire Default Mic',
    status: 'online'
  });

  const spectrumCanvasRef = useRef(null);

  useEffect(() => {
    fetchHistory();
    fetchConfig();
    fetchStatus();

    const interval = setInterval(() => {
      fetchStatus();
      fetchHistory(true);
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Machined Multi-band Audio Spectrum Visualizer (32 Bands with Phosphor Decay)
  useEffect(() => {
    const canvas = spectrumCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let tick = 0;
    const bands = 28;
    const heights = new Array(bands).fill(4);

    const render = () => {
      tick++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barWidth = 3;
      const spacing = (canvas.width - bands * barWidth) / (bands - 1);

      for (let i = 0; i < bands; i++) {
        // Organic simulated acoustic response with low-frequency emphasis
        const freqWeight = Math.sin((i / bands) * Math.PI * 0.95);
        const wave1 = Math.sin(tick * 0.07 + i * 0.4);
        const wave2 = Math.cos(tick * 0.04 + i * 0.25);
        const targetH = Math.max(3, freqWeight * 20 + (wave1 + wave2) * 5 + Math.random() * 2);
        heights[i] += (targetH - heights[i]) * 0.18;

        const x = i * (barWidth + spacing);
        const y = canvas.height - heights[i];

        // Phosphorescent Chromatic-Teal gradient with amber peak highlights
        const grad = ctx.createLinearGradient(0, canvas.height, 0, y);
        grad.addColorStop(0, 'oklch(55% 0.14 185)');
        grad.addColorStop(0.7, 'oklch(75% 0.12 185)');
        grad.addColorStop(1, heights[i] > 18 ? 'oklch(82% 0.095 68)' : 'oklch(88% 0.08 185)');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, heights[i], 1.5);
        ctx.fill();

        // Subtle peak retention dot
        ctx.fillStyle = heights[i] > 18 ? 'oklch(82% 0.095 68)' : 'oklch(75% 0.12 185 / 0.8)';
        ctx.fillRect(x, Math.max(0, y - 2.5), barWidth, 1.5);
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
        setSaveStatus('Studio settings saved');
        setTimeout(() => setSaveStatus(''), 2500);
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
  const durationSec = activeItem?.duration_sec || 2.4;
  const estWpm = durationSec > 0 && wordCount > 0 ? Math.round((wordCount / durationSec) * 60) : 0;

  return (
    <div className="flex h-screen w-screen bg-[oklch(12%_0.02_258)] text-[oklch(93.5%_0.012_85)] font-body antialiased overflow-hidden select-none">
      
      {/* 1. LEFT RACK: SESSION REEL & INPUT MONITOR */}
      <aside className="w-80 bg-[oklch(14%_0.022_258)] border-r border-[oklch(24%_0.02_258)] flex flex-col shrink-0">
        
        {/* Studio Machine Header */}
        <div className="p-4 border-b border-[oklch(24%_0.02_258)] bg-[oklch(15.5%_0.022_258)]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-b from-[oklch(75%_0.12_185)] to-[oklch(55%_0.14_185)] flex items-center justify-center text-[oklch(12%_0.02_258)] font-display font-semibold text-sm shadow-md border border-[oklch(85%_0.1_185/0.4)]">
                W
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <h1 className="text-sm font-display font-semibold text-white tracking-tight leading-none">Whistle Studio</h1>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-[oklch(22%_0.025_258)] text-[oklch(75%_0.12_185)] border border-[oklch(30%_0.03_258)]">
                    v1.0
                  </span>
                </div>
                <p className="text-[11px] text-[oklch(65%_0.02_255)] mt-0.5">WhisperFlow Dictation</p>
              </div>
            </div>

            <button 
              onClick={triggerVoiceHud}
              title="Dictate with Global Hotkey (Super + Shift + J)"
              className="btn-accent px-3 py-1.5 rounded-lg text-xs flex items-center space-x-1.5 cursor-pointer"
            >
              <Mic className="w-3.5 h-3.5" />
              <span>Record</span>
            </button>
          </div>

          {/* Machined Audio Level Decibel Meter */}
          <div className="machined-well p-2 rounded-lg">
            <div className="flex items-center justify-between text-[10px] font-mono text-[oklch(60%_0.02_255)] mb-1">
              <span className="flex items-center space-x-1">
                <Radio className="w-3 h-3 text-[oklch(75%_0.12_185)] animate-pulse" />
                <span>INPUT LEVEL</span>
              </span>
              <span>-18 dB</span>
            </div>
            <div className="h-2 w-full bg-[oklch(10%_0.02_258)] rounded overflow-hidden flex items-center px-0.5">
              <div className="h-1 bg-gradient-to-r from-[oklch(60%_0.14_185)] via-[oklch(75%_0.12_185)] to-[oklch(82%_0.095_68)] rounded-full w-[65%] transition-all duration-75"></div>
            </div>
            <div className="flex justify-between text-[8px] font-mono text-[oklch(45%_0.015_255)] mt-1 px-0.5">
              <span>-48dB</span>
              <span>-24dB</span>
              <span>-12dB</span>
              <span>-6dB</span>
              <span className="text-[oklch(82%_0.095_68)]">0dB</span>
            </div>
          </div>
        </div>

        {/* Search Input */}
        <div className="px-3 pt-3 pb-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[oklch(55%_0.02_255)] absolute left-3 top-2.5" />
            <input 
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search session transcripts..."
              className="w-full bg-[oklch(12%_0.02_258)] border border-[oklch(24%_0.02_258)] rounded-lg pl-8 pr-3 py-1.5 text-xs text-[oklch(90%_0.015_85)] placeholder-[oklch(50%_0.015_255)] focus:outline-none focus:border-[oklch(75%_0.12_185)] transition"
            />
          </div>
        </div>

        {/* Session Reel / History Cards */}
        <div className="flex-1 overflow-y-auto px-2 space-y-1.5 py-1">
          {filtered.length === 0 ? (
            <div className="p-8 text-center text-xs text-[oklch(55%_0.02_255)]">
              No audio transcripts recorded yet.<br/>
              Hold <kbd className="px-1.5 py-0.5 bg-[oklch(18%_0.02_258)] rounded border border-[oklch(28%_0.02_258)] text-[oklch(75%_0.12_185)] font-mono text-[10px]">Super+Shift+J</kbd> to dictate.
            </div>
          ) : (
            filtered.map((item, idx) => {
              const isSelected = item.id === selectedId;
              const textSnippet = item.formatted_text || item.raw_text || 'Empty recording';
              const timeDisplay = item.created_at ? item.created_at.slice(11, 16) : 'Now';

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={`group px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-120 flex flex-col relative overflow-hidden border ${
                    isSelected 
                      ? 'machined-plate border-[oklch(75%_0.12_185/0.6)] shadow-lg' 
                      : 'bg-[oklch(13%_0.02_258)] hover:bg-[oklch(16%_0.022_258)] border-[oklch(22%_0.015_258)]'
                  }`}
                >
                  {/* Active Studio Marker */}
                  {isSelected && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-[oklch(75%_0.12_185)]"></div>
                  )}

                  <div className="flex items-center justify-between text-[10px] font-mono text-[oklch(55%_0.02_255)] mb-1 pl-1">
                    <span className="flex items-center space-x-1.5">
                      <span className="text-[oklch(75%_0.12_185)] font-semibold">REC #{String(filtered.length - idx).padStart(2, '0')}</span>
                      <span>•</span>
                      <span>{timeDisplay}</span>
                    </span>
                    <div className="flex items-center space-x-1">
                      <span className="px-1.5 py-0.2 rounded bg-[oklch(18%_0.02_258)] text-[oklch(70%_0.02_255)] border border-[oklch(26%_0.02_258)]">
                        {item.duration_sec ? `${item.duration_sec.toFixed(1)}s` : '1.8s'}
                      </span>
                      <button 
                        onClick={(e) => handleDelete(item.id, e)}
                        className="opacity-0 group-hover:opacity-100 p-0.5 text-[oklch(50%_0.015_255)] hover:text-red-400 rounded transition"
                        title="Delete recording"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-[oklch(88%_0.015_85)] line-clamp-2 leading-relaxed pl-1 font-body">
                    {textSnippet}
                  </p>
                </div>
              );
            })
          )}
        </div>

        {/* Hardware Status Footer */}
        <div className="p-3 border-t border-[oklch(24%_0.02_258)] bg-[oklch(12%_0.02_258)] flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2 min-w-0 pr-2">
            <span className="w-2 h-2 rounded-full bg-[oklch(75%_0.14_150)] shrink-0 shadow-sm"></span>
            <span className="truncate text-[11px] font-mono text-[oklch(60%_0.02_255)]" title={systemStatus.audio_device}>
              {systemStatus.audio_device.replace("Core Ultra 200H/200V Series Processors HD Audio ", "")}
            </span>
          </div>

          <button 
            onClick={() => setShowSettings(true)}
            className="p-1.5 hover:text-white rounded-lg hover:bg-[oklch(20%_0.025_258)] transition shrink-0 text-[oklch(65%_0.02_255)]"
            title="Studio Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

      </aside>

      {/* 2. MAIN WORKSPACE: STUDIO CONSOLE & TRANSCRIPTION CANVAS */}
      <main className="flex-1 flex flex-col bg-[oklch(11%_0.02_258)] overflow-hidden select-text studio-grid">
        
        {/* Top Studio Control Rack */}
        <header className="h-14 border-b border-[oklch(24%_0.02_258)] px-6 flex items-center justify-between bg-[oklch(13.5%_0.022_258)] shrink-0 select-none">
          
          {/* Audio Metrics */}
          <div className="flex items-center space-x-4 text-xs font-mono text-[oklch(65%_0.02_255)]">
            <div className="flex items-center space-x-1.5">
              <span className="text-[oklch(75%_0.12_185)] font-semibold">{wordCount}</span>
              <span>words</span>
            </div>
            <span>•</span>
            <div className="flex items-center space-x-1.5">
              <span className="text-white font-semibold">{charCount}</span>
              <span>chars</span>
            </div>
            <span>•</span>
            <div className="flex items-center space-x-1.5">
              <span className="text-[oklch(82%_0.095_68)] font-semibold">{estWpm}</span>
              <span>WPM</span>
            </div>
            <span>•</span>
            <span className="text-[oklch(55%_0.02_255)]">{durationSec.toFixed(1)}s audio</span>
          </div>

          {/* Center Spectrum Visualizer */}
          <div className="flex items-center space-x-2">
            <canvas ref={spectrumCanvasRef} width={120} height={22} className="rounded" />
          </div>

          {/* Right Action Tools */}
          <div className="flex items-center space-x-3">
            
            {/* View Mode Toggle: Formatted vs Acoustic Diff */}
            <div className="bg-[oklch(10%_0.02_258)] p-0.5 rounded-lg border border-[oklch(22%_0.02_258)] flex items-center text-xs">
              <button
                onClick={() => setViewMode('formatted')}
                className={`px-2.5 py-1 rounded-md transition cursor-pointer font-medium ${
                  viewMode === 'formatted'
                    ? 'bg-[oklch(22%_0.025_258)] text-[oklch(75%_0.12_185)] shadow'
                    : 'text-[oklch(60%_0.02_255)] hover:text-white'
                }`}
              >
                Polished
              </button>
              <button
                onClick={() => setViewMode('diff')}
                className={`px-2.5 py-1 rounded-md transition cursor-pointer font-medium ${
                  viewMode === 'diff'
                    ? 'bg-[oklch(22%_0.025_258)] text-[oklch(75%_0.12_185)] shadow'
                    : 'text-[oklch(60%_0.02_255)] hover:text-white'
                }`}
              >
                Acoustic Diff
              </button>
            </div>

            {/* Tactile Copy Button */}
            <button 
              onClick={() => handleCopyText(activeContent)}
              disabled={!activeContent}
              className="btn-accent flex items-center space-x-1.5 px-3 py-1.5 rounded-lg disabled:opacity-40 text-xs font-semibold cursor-pointer"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[oklch(20%_0.03_62)]" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Text'}</span>
            </button>
          </div>
        </header>

        {/* Central Transcription Studio Board */}
        <div className="flex-1 overflow-y-auto p-10 max-w-4xl mx-auto w-full flex flex-col justify-center">
          {activeItem ? (
            <div className="space-y-6">
              
              {/* Studio Plate */}
              <div className="machined-plate p-8 rounded-2xl relative">
                
                {/* Header Tape Marker */}
                <div className="flex items-center justify-between pb-4 mb-6 border-b border-[oklch(24%_0.02_258)]">
                  <div className="flex items-center space-x-2">
                    <span className="w-2.5 h-2.5 rounded-sm bg-[oklch(75%_0.12_185)]"></span>
                    <span className="font-mono text-xs text-[oklch(65%_0.02_255)] uppercase tracking-wider">
                      Transcription Console • Track {selectedId || 1}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-xs font-mono text-[oklch(60%_0.02_255)]">
                    <span className="px-2 py-0.5 rounded bg-[oklch(12%_0.02_258)] border border-[oklch(24%_0.02_258)]">
                      Engine: {config.provider.toUpperCase()}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-[oklch(12%_0.02_258)] border border-[oklch(24%_0.02_258)]">
                      16.0 kHz Mono
                    </span>
                  </div>
                </div>

                {/* Content View Modes */}
                {viewMode === 'formatted' && (
                  <div className="font-body text-lg text-[oklch(95%_0.01_85)] leading-relaxed whitespace-pre-wrap selection:bg-[oklch(75%_0.12_185/0.3)] selection:text-[oklch(95%_0.01_85)]">
                    {activeItem.formatted_text || activeItem.raw_text}
                  </div>
                )}

                {viewMode === 'diff' && (
                  <div className="space-y-4">
                    <div className="machined-well p-4 rounded-xl">
                      <div className="text-[11px] font-mono uppercase text-[oklch(60%_0.02_255)] mb-1.5 flex items-center space-x-1.5">
                        <Activity className="w-3.5 h-3.5 text-[oklch(82%_0.095_68)]" />
                        <span>Raw ASR Acoustic Stream (Pre-LLM)</span>
                      </div>
                      <div className="font-mono text-xs text-[oklch(75%_0.02_255)] leading-relaxed whitespace-pre-wrap">
                        {activeItem.raw_text || 'No raw transcript recorded.'}
                      </div>
                    </div>

                    <div className="machined-well p-4 rounded-xl border-l-2 border-[oklch(75%_0.12_185)]">
                      <div className="text-[11px] font-mono uppercase text-[oklch(75%_0.12_185)] mb-1.5 flex items-center space-x-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-[oklch(75%_0.12_185)]" />
                        <span>WhisperFlow Normalization & Technical Repair</span>
                      </div>
                      <div className="font-body text-sm text-white leading-relaxed whitespace-pre-wrap">
                        {activeItem.formatted_text || activeItem.raw_text}
                      </div>
                    </div>
                  </div>
                )}

                {/* Simulated Audio Scrubber Bar */}
                <div className="mt-8 pt-4 border-t border-[oklch(22%_0.02_258)] flex items-center space-x-3 text-xs font-mono text-[oklch(55%_0.02_255)]">
                  <span>0:00</span>
                  <div className="flex-1 h-1.5 bg-[oklch(12%_0.02_258)] rounded-full overflow-hidden relative">
                    <div className="h-full bg-[oklch(75%_0.12_185)] w-[100%] rounded-full"></div>
                  </div>
                  <span>0:{String(Math.round(durationSec)).padStart(2, '0')}</span>
                </div>

              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
              <div className="w-14 h-14 rounded-2xl machined-plate flex items-center justify-center text-[oklch(75%_0.12_185)] shadow-xl">
                <Mic className="w-6 h-6 animate-pulse" />
              </div>
              <h2 className="text-base font-display font-medium text-white">Whistle Audio Studio Ready</h2>
              <p className="text-xs text-[oklch(65%_0.02_255)] max-w-sm leading-relaxed">
                Hold <kbd className="px-2 py-0.5 bg-[oklch(16%_0.02_258)] rounded border border-[oklch(28%_0.02_258)] text-[oklch(75%_0.12_185)] font-mono">Super + Shift + J</kbd> anywhere on your system to dictate. Release to inject directly into your active window.
              </p>
            </div>
          )}
        </div>

        {/* Bottom Studio Test & Dictation Deck */}
        <div className="p-4 border-t border-[oklch(24%_0.02_258)] bg-[oklch(13.5%_0.022_258)] select-none">
          <form onSubmit={handleManualSubmit} className="max-w-3xl mx-auto flex items-center space-x-2">
            <input 
              type="text"
              value={manualText}
              onChange={(e) => setManualText(e.target.value)}
              placeholder="Test WhisperFlow normalization (e.g. 'check this crawl configuration theek hai bhai')..."
              className="flex-1 bg-[oklch(10%_0.02_258)] border border-[oklch(24%_0.02_258)] rounded-xl px-4 py-2.5 text-xs text-[oklch(92%_0.012_85)] placeholder-[oklch(50%_0.015_255)] focus:outline-none focus:border-[oklch(75%_0.12_185)] transition shadow-inner font-body"
            />
            <button
              type="submit"
              disabled={!manualText.trim() || isProcessing}
              className="btn-instrument px-4 py-2.5 rounded-xl text-xs font-semibold disabled:opacity-40 cursor-pointer"
            >
              Normalize Text
            </button>
          </form>

          <div className="text-center text-[11px] text-[oklch(55%_0.02_255)] mt-2 font-mono flex items-center justify-center space-x-2">
            <span>Global Push-to-Talk Shortcut:</span>
            <span className="text-[oklch(75%_0.12_185)] font-semibold">Super + Shift + J</span>
            <span>•</span>
            <span>Hold to record, release to paste</span>
          </div>
        </div>

      </main>

      {/* 3. STUDIO SETTINGS MODAL */}
      {showSettings && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-lg machined-plate rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-[oklch(28%_0.02_258)]">
            
            <div className="px-6 py-4 border-b border-[oklch(24%_0.02_258)] bg-[oklch(16%_0.022_258)] flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Sliders className="w-4 h-4 text-[oklch(75%_0.12_185)]" />
                <h2 className="text-sm font-display font-semibold text-white">Whistle Studio Preferences</h2>
              </div>
              <button 
                onClick={() => setShowSettings(false)}
                className="p-1 text-[oklch(55%_0.02_255)] hover:text-white rounded-lg transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveConfig} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block text-[oklch(85%_0.015_85)] font-medium mb-1.5">Transcription & Formatting Engine</label>
                <select
                  value={config.provider}
                  onChange={(e) => setConfig({ ...config, provider: e.target.value })}
                  className="w-full bg-[oklch(12%_0.02_258)] border border-[oklch(26%_0.02_258)] rounded-xl px-3 py-2 text-[oklch(90%_0.015_85)] focus:outline-none focus:border-[oklch(75%_0.12_185)]"
                >
                  <option value="groq">Groq Cloud (Whisper Large v3 Turbo + Fast Inference)</option>
                  <option value="ollama">Ollama (Local Offline LLM)</option>
                </select>
              </div>

              {config.provider === 'groq' && (
                <div>
                  <label className="block text-[oklch(85%_0.015_85)] font-medium mb-1.5">Groq Cloud API Key</label>
                  <input 
                    type="password"
                    value={config.groq_api_key || ''}
                    onChange={(e) => setConfig({ ...config, groq_api_key: e.target.value })}
                    placeholder="gsk_..."
                    className="w-full bg-[oklch(12%_0.02_258)] border border-[oklch(26%_0.02_258)] rounded-xl px-3 py-2 text-[oklch(90%_0.015_85)] placeholder-[oklch(45%_0.015_255)] focus:outline-none focus:border-[oklch(75%_0.12_185)] font-mono"
                  />
                  <p className="text-[10px] text-[oklch(55%_0.02_255)] mt-1">
                    Enables ultra-fast Whisper-large-v3-turbo cloud transcription and intelligent Hinglish auto-correction.
                  </p>
                </div>
              )}

              {config.provider === 'ollama' && (
                <div>
                  <label className="block text-[oklch(85%_0.015_85)] font-medium mb-1.5">Ollama Server Endpoint</label>
                  <input 
                    type="text"
                    value={config.ollama_url || 'http://localhost:11434'}
                    onChange={(e) => setConfig({ ...config, ollama_url: e.target.value })}
                    className="w-full bg-[oklch(12%_0.02_258)] border border-[oklch(26%_0.02_258)] rounded-xl px-3 py-2 text-[oklch(90%_0.015_85)] focus:outline-none focus:border-[oklch(75%_0.12_185)] font-mono"
                  />
                </div>
              )}

              <div className="machined-well p-3 rounded-xl text-[11px] text-[oklch(60%_0.02_255)] space-y-1">
                <div className="flex items-center space-x-1.5 text-[oklch(75%_0.12_185)] font-medium">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Privacy & Local Fallback</span>
                </div>
                <p>
                  Transcripts are cached locally in your SQLite database. If network access drops, Whistle switches automatically to local deterministic tech homophone repair.
                </p>
              </div>

              <div className="pt-2 flex items-center justify-between">
                <span className="text-[oklch(75%_0.14_150)] font-medium font-mono text-[11px]">{saveStatus}</span>
                <button
                  type="submit"
                  className="btn-accent px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer"
                >
                  Save Preferences
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
