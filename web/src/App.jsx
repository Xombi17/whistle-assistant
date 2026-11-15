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
  Radio, 
  Layers,
  ChevronRight,
  ChevronDown,
  Search,
  ExternalLink,
  Plus,
  Puzzle,
  Clock,
  Folder,
  MessageSquare,
  Send,
  Volume2,
  Terminal,
  Columns,
  MoreHorizontal,
  X
} from 'lucide-react';

const DeepSeekLogo = ({ className = "w-5 h-5" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path fill="#4D6BFE" d="M23.748 4.482c-.254-.124-.364.113-.512.234-.051.039-.094.09-.137.136-.372.397-.806.657-1.373.626-.829-.046-1.537.214-2.163.848-.133-.782-.575-1.248-1.247-1.548-.352-.156-.708-.311-.955-.65-.172-.241-.219-.51-.305-.774-.055-.16-.11-.323-.293-.35-.2-.031-.278.136-.356.276-.313.572-.434 1.202-.422 1.84.027 1.436.633 2.58 1.838 3.393.137.093.172.187.129.323-.082.28-.18.552-.266.833-.055.179-.137.217-.329.14a5.526 5.526 0 0 1-1.736-1.18c-.857-.828-1.631-1.742-2.597-2.458a11.365 11.365 0 0 0-.689-.471c-.985-.957.13-1.743.388-1.836.27-.098.093-.432-.779-.428-.872.004-1.67.295-2.687.684a3.055 3.055 0 0 1-.465.137 9.597 9.597 0 0 0-2.883-.102c-1.885.21-3.39 1.102-4.497 2.623C.082 8.606-.231 10.684.152 12.85c.403 2.284 1.569 4.175 3.36 5.653 1.858 1.533 3.997 2.284 6.438 2.14 1.482-.085 3.133-.284 4.994-1.86.47.234.962.327 1.78.397.63.059 1.236-.03 1.705-.128.735-.156.684-.837.419-.961-2.155-1.004-1.682-.595-2.113-.926 1.096-1.296 2.746-2.642 3.392-7.003.05-.347.007-.565 0-.845-.004-.17.035-.237.23-.256a4.173 4.173 0 0 0 1.545-.475c1.396-.763 1.96-2.015 2.093-3.517.02-.23-.004-.467-.247-.588zM11.581 18c-2.089-1.642-3.102-2.183-3.52-2.16-.392.024-.321.471-.235.763.09.288.207.486.371.739.114.167.192.416-.113.603-.673.416-1.842-.14-1.897-.167-1.361-.802-2.5-1.86-3.301-3.307-.774-1.393-1.224-2.887-1.298-4.482-.02-.386.093-.522.477-.592a4.696 4.696 0 0 1 1.529-.039c2.132.312 3.946 1.265 5.468 2.774.868.86 1.525 1.887 2.202 2.891.72 1.066 1.494 2.082 2.48 2.914.348.292.625.514.891.677-.802.09-2.14.11-3.054-.614zm1-6.44a.306.306 0 0 1 .415-.287.302.302 0 0 1 .2.288.306.306 0 0 1-.31.307.303.303 0 0 1-.304-.308zm3.11 1.596c-.2.081-.399.151-.59.16a1.245 1.245 0 0 1 0 0z"/>
  </svg>
);

export default function App() {
  const [selectedSessionId, setSelectedSessionId] = useState('welcome');
  const [historyItems, setHistoryItems] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const [thoughtOpen, setThoughtOpen] = useState(true);
  const [activeModal, setActiveModal] = useState(null); // 'plugins' | 'automation' | null
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

  const [config, setConfig] = useState({
    provider: 'deepseek',
    deepseek_api_key: '',
    deepseek_model: 'deepseek-chat',
    groq_api_key: '',
    groq_model: 'llama-3.3-70b-versatile',
    xai_api_key: '',
    xai_model: 'grok-beta',
    ollama_url: 'http://localhost:11434',
    ollama_model: 'qwen2.5-coder:7b'
  });
  const [saveStatus, setSaveStatus] = useState('');
  const [systemStatus, setSystemStatus] = useState({
    audio_device: 'Detecting audio...',
    sample_rate: 16000,
    status: 'online'
  });

  const canvasRef = useRef(null);
  const chatBottomRef = useRef(null);

  useEffect(() => {
    fetchHistory();
    fetchConfig();
    fetchStatus();
    const interval = setInterval(() => {
      fetchStatus();
      fetchHistory(true);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  // 60fps Visualizer animation
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let tick = 0;

    const render = () => {
      tick++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barCount = 28;
      const barWidth = 3;
      const gap = (canvas.width - barCount * barWidth) / (barCount - 1);

      for (let i = 0; i < barCount; i++) {
        const x = i * (barWidth + gap);
        const centerDist = Math.sin((i / barCount) * Math.PI);
        const noise = Math.sin(tick * 0.12 + i * 0.4) * 0.5 + 0.5;
        const amplitude = centerDist * 12 + noise * 6 + 2;

        const gradient = ctx.createLinearGradient(0, canvas.height, 0, 0);
        gradient.addColorStop(0, '#4D6BFE');
        gradient.addColorStop(1, '#818cf8');

        ctx.fillStyle = gradient;
        ctx.fillRect(x, canvas.height - amplitude, barWidth, amplitude);
      }
      animationId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animationId);
  }, []);

  const fetchHistory = async (silent = false) => {
    try {
      const res = await fetch('/api/history');
      if (res.ok) {
        const data = await res.json();
        setHistoryItems(data);
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
        setSaveStatus('Plugin settings committed');
        setTimeout(() => setSaveStatus(''), 2500);
      }
    } catch (e) {
      setSaveStatus('Error saving settings');
    }
  };

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const triggerVoiceHud = async () => {
    try {
      await fetch('/api/trigger', { method: 'POST' });
    } catch (e) {}
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || isProcessing) return;

    const userText = inputText.trim();
    setInputText('');
    setIsProcessing(true);

    try {
      const res = await fetch('/api/format', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userText })
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

  const handleDeleteItem = async (id, e) => {
    e.stopPropagation();
    if (confirm('Delete this transcript session?')) {
      try {
        await fetch('/api/history/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        setHistoryItems(prev => prev.filter(i => i.id !== id));
        if (selectedSessionId === id) {
          setSelectedSessionId('welcome');
        }
      } catch (e) {}
    }
  };

  const filteredHistory = historyItems.filter(item => 
    (item.formatted_text || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.raw_text || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedItem = historyItems.find(i => i.id === selectedSessionId);

  return (
    <div className="flex h-screen w-screen bg-[#111215] text-[#d4d4d8] font-sans antialiased selection:bg-[#4D6BFE]/30 selection:text-[#93c5fd] overflow-hidden">
      
      {/* 1. LEFT SIDEBAR (DeepSeek Harness style) */}
      <aside className="w-64 bg-[#141518] border-r border-[#222327] flex flex-col shrink-0 select-none">
        
        {/* Top Window Dots & Header */}
        <div className="pt-3.5 px-4 pb-2">
          {/* Traffic lights macOS style */}
          <div className="flex items-center space-x-2 mb-3">
            <span className="w-3 h-3 rounded-full bg-[#ff5f56] inline-block shadow-sm"></span>
            <span className="w-3 h-3 rounded-full bg-[#febc2e] inline-block shadow-sm"></span>
            <span className="w-3 h-3 rounded-full bg-[#28c840] inline-block shadow-sm"></span>
          </div>

          {/* DeepSeek Logo + HARNESS Badge */}
          <div className="flex items-center space-x-2">
            <DeepSeekLogo className="w-5 h-5" />
            <span className="text-white font-semibold text-[15px] tracking-tight">deepseek</span>
            <span className="bg-[#26282f] text-slate-200 text-[10px] font-bold px-1.5 py-0.5 rounded tracking-wider uppercase border border-[#31333b]">
              HARNESS
            </span>
          </div>
        </div>

        {/* Action: New Session button */}
        <div className="px-3 pt-2 pb-3">
          <button 
            onClick={() => setSelectedSessionId('welcome')}
            className="w-full bg-[#1e2025] hover:bg-[#252830] text-slate-200 border border-[#2b2d35] rounded-xl py-2 px-3 flex items-center justify-center space-x-2 text-xs font-medium transition shadow-sm"
          >
            <Plus className="w-4 h-4 text-slate-300" />
            <span>New Session</span>
          </button>
        </div>

        {/* Primary Navigation Items */}
        <div className="px-3 space-y-1">
          <button 
            onClick={() => setActiveModal('plugins')}
            className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs transition ${
              activeModal === 'plugins' 
                ? 'bg-[#23252b] text-white font-medium' 
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#1a1b1f]'
            }`}
          >
            <div className="flex items-center space-x-2.5">
              <Puzzle className="w-4 h-4 text-[#4D6BFE]" />
              <span>Plugins</span>
            </div>
            <span className="text-[10px] text-zinc-500 font-mono">Cordis v4</span>
          </button>

          <button 
            onClick={() => setActiveModal('automation')}
            className={`w-full flex items-center justify-between px-3 py-1.5 rounded-lg text-xs transition ${
              activeModal === 'automation' 
                ? 'bg-[#23252b] text-white font-medium' 
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#1a1b1f]'
            }`}
          >
            <div className="flex items-center space-x-2.5">
              <Clock className="w-4 h-4 text-emerald-400" />
              <span>Automation</span>
            </div>
            <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.2 rounded font-mono">
              Hotkeys
            </span>
          </button>
        </div>

        {/* Workspace Section Header */}
        <div className="mt-5 px-4 flex items-center justify-between">
          <span className="text-[11px] font-semibold text-zinc-400 tracking-wider">Workspace</span>
          <div className="flex items-center space-x-1 text-zinc-500">
            <button 
              onClick={() => {
                const el = document.getElementById('sidebar-search');
                if (el) el.focus();
              }}
              className="p-1 hover:text-zinc-300 rounded hover:bg-[#1f2025]"
            >
              <Search className="w-3.5 h-3.5" />
            </button>
            <button className="p-1 hover:text-zinc-300 rounded hover:bg-[#1f2025]">
              <Columns className="w-3.5 h-3.5" />
            </button>
            <button className="p-1 hover:text-zinc-300 rounded hover:bg-[#1f2025]">
              <MoreHorizontal className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Search input in sidebar */}
        <div className="px-3 mt-2">
          <input 
            id="sidebar-search"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search transcripts..."
            className="w-full bg-[#1a1b20] border border-[#262830] rounded-lg px-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-[#4D6BFE]/60"
          />
        </div>

        {/* Workspace Sessions List */}
        <div className="mt-2 px-2 flex-1 overflow-y-auto space-y-0.5">
          {/* Default workspace folder item */}
          <div className="flex items-center space-x-2 px-2 py-1.5 text-xs text-zinc-400 font-medium">
            <Folder className="w-3.5 h-3.5 text-zinc-500" />
            <span>Default workspace</span>
          </div>

          {/* Intro item (Meet DeepSeek Harness) */}
          <div 
            onClick={() => setSelectedSessionId('welcome')}
            className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition ${
              selectedSessionId === 'welcome' 
                ? 'bg-[#24262c] text-white font-medium' 
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#1b1c21]'
            }`}
          >
            <span className="truncate">Meet DeepSeek Harness</span>
          </div>

          {/* History transcript sessions */}
          {filteredHistory.map((item) => {
            const preview = (item.formatted_text || item.raw_text || 'Voice session').slice(0, 32);
            const isSelected = selectedSessionId === item.id;
            return (
              <div 
                key={item.id}
                onClick={() => setSelectedSessionId(item.id)}
                className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition ${
                  isSelected 
                    ? 'bg-[#24262c] text-white font-medium' 
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#1b1c21]'
                }`}
              >
                <div className="flex items-center space-x-2 min-w-0">
                  <MessageSquare className="w-3.5 h-3.5 shrink-0 text-zinc-500" />
                  <span className="truncate">{preview}</span>
                </div>
                <button 
                  onClick={(e) => handleDeleteItem(item.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-0.5 text-zinc-500 hover:text-red-400 rounded transition"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })}
        </div>

        {/* Bottom Audio & Hardware Telemetry */}
        <div className="p-3 border-t border-[#222327] bg-[#121316]">
          <div className="flex items-center space-x-2 text-[11px] text-zinc-400 font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="truncate" title={systemStatus.audio_device}>
              {systemStatus.audio_device.replace("Core Ultra 200H/200V Series Processors HD Audio ", "")}
            </span>
          </div>
          <div className="mt-1 flex items-center justify-between text-[10px] text-zinc-500 font-mono">
            <span>16kHz Mono</span>
            <span className="text-blue-400 font-semibold uppercase">{config.provider}</span>
          </div>
        </div>

      </aside>

      {/* 2. MAIN CONVERSATION / WORKSPACE AREA */}
      <main className="flex-1 flex flex-col bg-[#111215] overflow-hidden">
        
        {/* Top Header Bar */}
        <header className="h-12 border-b border-[#222327] flex items-center justify-between px-6 bg-[#131417]/80 backdrop-blur shrink-0 select-none">
          <div className="flex items-center space-x-3">
            <h1 className="text-xs font-semibold text-zinc-200 tracking-wide">
              {selectedSessionId === 'welcome' 
                ? 'Meet DeepSeek Harness' 
                : (selectedItem?.formatted_text?.slice(0, 48) || 'Voice Session')}
            </h1>
            <span className="text-[10px] bg-[#1d1f25] text-zinc-400 px-2 py-0.5 rounded border border-[#2a2c34] font-mono">
              v0.4.0-preview
            </span>
          </div>

          <div className="flex items-center space-x-4">
            {/* 60fps Real-Time Audio Spectrum Visualizer */}
            <div className="flex items-center space-x-2 bg-[#17181d] px-2.5 py-1 rounded-lg border border-[#252730]">
              <canvas ref={canvasRef} width={90} height={20} className="rounded" />
              <span className="text-[10px] text-blue-400 font-mono font-medium">LIVE VU</span>
            </div>

            {/* Quick Hold-to-Talk HUD trigger */}
            <button 
              onClick={triggerVoiceHud}
              className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-[#1f2128] hover:bg-[#282a33] text-zinc-200 text-xs font-medium border border-[#2c2f38] transition active:scale-95"
            >
              <Mic className="w-3.5 h-3.5 text-[#4D6BFE]" />
              <span>Voice HUD</span>
            </button>

            {/* Layout icons */}
            <div className="flex items-center space-x-1 text-zinc-400">
              <button className="p-1 hover:text-white rounded hover:bg-[#1e2025]">
                <Columns className="w-4 h-4" />
              </button>
              <button 
                onClick={() => setActiveModal('plugins')}
                className="p-1 hover:text-white rounded hover:bg-[#1e2025]"
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Message Feed / Chat Canvas */}
        <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
          
          {selectedSessionId === 'welcome' ? (
            /* EXACT REPRODUCTION OF THE SCREENSHOT CONVERSATION */
            <div className="max-w-3xl mx-auto space-y-6">
              
              {/* User message on the right (Pill Capsule) */}
              <div className="flex justify-end">
                <div className="bg-[#24252a] text-zinc-100 px-4 py-2.5 rounded-2xl text-sm font-normal shadow-sm border border-[#2e3037]">
                  Could you introduce yourself?
                </div>
              </div>

              {/* Assistant Message on the left */}
              <div className="space-y-3">
                {/* Collapsible 'Thought for a while' block */}
                <div className="border border-[#22242a] bg-[#16171b] rounded-xl overflow-hidden">
                  <button 
                    onClick={() => setThoughtOpen(!thoughtOpen)}
                    className="w-full px-3 py-2 flex items-center justify-between text-xs text-zinc-400 hover:text-zinc-200 transition bg-[#18191e]"
                  >
                    <div className="flex items-center space-x-2">
                      <Sparkles className="w-3.5 h-3.5 text-[#4D6BFE]" />
                      <span className="font-mono text-[11px]">Thought for 1.4 seconds</span>
                    </div>
                    {thoughtOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                  </button>

                  {thoughtOpen && (
                    <div className="p-3 text-xs text-zinc-400 font-mono border-t border-[#22242a] bg-[#131417]/80 space-y-1">
                      <p className="text-zinc-500">// Cordis Plugin Architecture Pipeline Execution</p>
                      <p className="text-emerald-400">✓ Loaded: @whistle/pipeline-audio (16kHz mono PipeWire)</p>
                      <p className="text-cyan-400">✓ Loaded: @deepseek/harness-whisperflow (Speech Normalizer)</p>
                      <p className="text-blue-400">✓ Active Provider: {config.provider.toUpperCase()} ({config.provider === 'deepseek' ? config.deepseek_model : config.groq_model})</p>
                    </div>
                  )}
                </div>

                {/* Assistant formatted text output */}
                <div className="text-zinc-200 text-sm leading-relaxed space-y-3 font-normal">
                  <p>
                    I'm <strong>DeepSeek Harness</strong>, an open-source harness from DeepSeek built on Cordis's <em>"everything is a plugin"</em> architecture. Run me as a desktop app or launch the web UI from code.
                  </p>
                  <p className="font-medium text-zinc-300">I can help with:</p>
                  <ol className="list-decimal pl-5 space-y-1.5 text-zinc-300">
                    <li><strong className="text-white">Everyday work</strong> — Organize files, analyze data, draft docs, and create slides.</li>
                    <li><strong className="text-white">Coding</strong> — Explore repos, fix bugs, build features, and run tests.</li>
                    <li><strong className="text-white">Research</strong> — Find information, verify facts, and cite sources.</li>
                  </ol>
                  <div className="p-3 mt-4 rounded-xl bg-[#191a20] border border-[#272932] text-xs text-zinc-300 space-y-1">
                    <div className="font-semibold text-blue-400 flex items-center space-x-1.5">
                      <Radio className="w-3.5 h-3.5" />
                      <span>Live JARVIS Voice Integration</span>
                    </div>
                    <p className="text-zinc-400">
                      Press and hold <kbd className="px-1.5 py-0.5 bg-[#252832] rounded border border-[#323642] text-white font-mono">Super</kbd> + <kbd className="px-1.5 py-0.5 bg-[#252832] rounded border border-[#323642] text-white font-mono">Shift</kbd> + <kbd className="px-1.5 py-0.5 bg-[#252832] rounded border border-[#323642] text-white font-mono">J</kbd> from any application to dictate with automated WhisperFlow formatting.
                    </p>
                  </div>
                </div>

              </div>

            </div>
          ) : (
            /* Selected Voice Transcript Thread */
            <div className="max-w-3xl mx-auto space-y-6">
              {/* User Voice Input Bubble */}
              <div className="flex justify-end">
                <div className="bg-[#24252a] text-zinc-100 px-4 py-3 rounded-2xl text-sm font-normal shadow-sm border border-[#2e3037] max-w-xl space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-zinc-400 font-mono mb-1">
                    <span className="flex items-center space-x-1 text-cyan-400">
                      <Mic className="w-3 h-3" />
                      <span>RAW VOICE AUDIO</span>
                    </span>
                    <span>{selectedItem?.created_at?.slice(11, 19) || 'Just now'}</span>
                  </div>
                  <p className="italic text-zinc-300">"{selectedItem?.raw_text}"</p>
                </div>
              </div>

              {/* Formatted Assistant Output */}
              <div className="space-y-3">
                <div className="border border-[#22242a] bg-[#16171b] rounded-xl overflow-hidden">
                  <div className="px-3 py-2 flex items-center justify-between text-xs text-zinc-400 bg-[#18191e]">
                    <div className="flex items-center space-x-2">
                      <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="font-mono text-[11px]">WhisperFlow AI Formatting Applied</span>
                    </div>
                    <span className="text-[10px] font-mono text-zinc-500">
                      Duration: {selectedItem?.duration_sec?.toFixed(1) || '1.2'}s
                    </span>
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-[#17181d] border border-[#262831] text-zinc-100 text-sm leading-relaxed space-y-3">
                  <div className="whitespace-pre-wrap font-sans text-base">
                    {selectedItem?.formatted_text}
                  </div>

                  {/* Actions bar */}
                  <div className="pt-3 border-t border-[#23252d] flex items-center justify-between">
                    <div className="text-[11px] font-mono text-zinc-500">
                      Formatted with {config.provider.toUpperCase()}
                    </div>
                    <div className="flex items-center space-x-2">
                      <button 
                        onClick={() => handleCopy(selectedItem?.formatted_text, selectedItem?.id)}
                        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-[#22242c] hover:bg-[#2b2d37] text-zinc-200 text-xs font-medium border border-[#2e313c] transition active:scale-95"
                      >
                        {copiedId === selectedItem?.id ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5 text-zinc-400" />
                            <span>Copy Text</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Bottom Floating Bar / Input Capsule */}
        <div className="p-4 bg-gradient-to-t from-[#111215] via-[#111215]/90 to-transparent shrink-0">
          <form 
            onSubmit={handleSendMessage}
            className="max-w-3xl mx-auto bg-[#1a1b20] border border-[#2a2c35] rounded-2xl p-2 pl-3 flex items-center space-x-2 shadow-2xl focus-within:border-[#4D6BFE]/60 transition"
          >
            {/* Mic Dictate Button */}
            <button
              type="button"
              onClick={triggerVoiceHud}
              className="p-2.5 rounded-xl bg-gradient-to-tr from-[#4D6BFE] to-[#6366f1] text-white hover:brightness-110 active:scale-95 transition shadow-lg shadow-blue-500/20"
              title="Hold <Super><Shift>J or click to trigger Voice HUD"
            >
              <Mic className="w-4 h-4" />
            </button>

            {/* Input field */}
            <input 
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Hold Super + Shift + J to speak, or type here to format..."
              className="flex-1 bg-transparent text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none"
            />

            {/* Provider pill indicator */}
            <div className="hidden sm:flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-[#22242c] border border-[#2c2e38] text-[11px] text-zinc-400 font-mono">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
              <span>{config.provider}</span>
            </div>

            {/* Send button */}
            <button
              type="submit"
              disabled={!inputText.trim() || isProcessing}
              className="p-2.5 rounded-xl bg-[#252730] hover:bg-[#30333e] text-zinc-300 disabled:opacity-40 transition"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-2 text-center text-[10px] text-zinc-500 font-mono">
            Press and hold <span className="text-zinc-300">Super + Shift + J</span> to dictate anywhere on your desktop
          </div>
        </div>

      </main>

      {/* 3. PLUGINS MODAL (Cordis "Everything is a Plugin" Framework) */}
      {activeModal === 'plugins' && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-[#16171b] border border-[#2a2c35] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            
            {/* Header */}
            <div className="px-6 py-4 border-b border-[#252730] flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Puzzle className="w-5 h-5 text-[#4D6BFE]" />
                <h2 className="text-sm font-semibold text-white">Cordis Plugins & Model Providers</h2>
              </div>
              <button 
                onClick={() => setActiveModal(null)}
                className="p-1 text-zinc-400 hover:text-white rounded-lg hover:bg-[#202127]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto space-y-5">
              <form onSubmit={handleSaveConfig} className="space-y-4">
                
                {/* Active Provider Selector */}
                <div>
                  <label className="block text-xs font-semibold text-zinc-300 mb-2">
                    Active LLM Plugin Engine
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {[
                      { id: 'deepseek', label: 'DeepSeek', sub: 'api.deepseek.com' },
                      { id: 'groq', label: 'Groq Cloud', sub: 'Llama 3.3 70B' },
                      { id: 'ollama', label: 'Ollama', sub: 'Local Qwen 2.5' },
                      { id: 'grok', label: 'xAI Grok', sub: 'grok-beta' }
                    ].map((prov) => (
                      <button
                        key={prov.id}
                        type="button"
                        onClick={() => setConfig({ ...config, provider: prov.id })}
                        className={`p-2.5 rounded-xl border text-left transition ${
                          config.provider === prov.id
                            ? 'bg-[#1f222b] border-[#4D6BFE] text-white shadow-md'
                            : 'bg-[#131418] border-[#252730] text-zinc-400 hover:border-zinc-700'
                        }`}
                      >
                        <div className="text-xs font-semibold">{prov.label}</div>
                        <div className="text-[10px] text-zinc-500 truncate">{prov.sub}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* DeepSeek API Configuration */}
                <div className="p-4 rounded-xl bg-[#131418] border border-[#252730] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-white flex items-center space-x-1.5">
                      <DeepSeekLogo className="w-4 h-4" />
                      <span>DeepSeek Official API</span>
                    </span>
                    <span className="text-[10px] text-blue-400 font-mono">api.deepseek.com</span>
                  </div>
                  <div>
                    <label className="text-[11px] text-zinc-400 block mb-1">DeepSeek API Key</label>
                    <input 
                      type="password"
                      value={config.deepseek_api_key || ''}
                      onChange={(e) => setConfig({ ...config, deepseek_api_key: e.target.value })}
                      placeholder="sk-..."
                      className="w-full bg-[#1b1c22] border border-[#282a33] rounded-lg px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-[#4D6BFE]"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-zinc-400 block mb-1">Model Name</label>
                    <select
                      value={config.deepseek_model || 'deepseek-chat'}
                      onChange={(e) => setConfig({ ...config, deepseek_model: e.target.value })}
                      className="w-full bg-[#1b1c22] border border-[#282a33] rounded-lg px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-[#4D6BFE]"
                    >
                      <option value="deepseek-chat">deepseek-chat (DeepSeek V3)</option>
                      <option value="deepseek-reasoner">deepseek-reasoner (DeepSeek R1)</option>
                    </select>
                  </div>
                </div>

                {/* Groq Cloud Configuration */}
                <div className="p-4 rounded-xl bg-[#131418] border border-[#252730] space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">Groq Fast Inference</span>
                    <span className="text-[10px] text-emerald-400 font-mono">Sub-200ms</span>
                  </div>
                  <div>
                    <label className="text-[11px] text-zinc-400 block mb-1">Groq API Key</label>
                    <input 
                      type="password"
                      value={config.groq_api_key || ''}
                      onChange={(e) => setConfig({ ...config, groq_api_key: e.target.value })}
                      placeholder="gsk_..."
                      className="w-full bg-[#1b1c22] border border-[#282a33] rounded-lg px-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-[#4D6BFE]"
                    />
                  </div>
                </div>

                {/* Save button */}
                <div className="pt-2 flex items-center justify-between">
                  <span className="text-xs font-mono text-emerald-400">{saveStatus}</span>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-xl bg-[#4D6BFE] hover:bg-[#3d5bfe] text-white text-xs font-semibold shadow-lg shadow-blue-500/20 transition active:scale-95"
                  >
                    Save & Mount Plugins
                  </button>
                </div>

              </form>
            </div>

          </div>
        </div>
      )}

      {/* 4. AUTOMATION MODAL */}
      {activeModal === 'automation' && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#16171b] border border-[#2a2c35] rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            
            <div className="px-6 py-4 border-b border-[#252730] flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <Clock className="w-5 h-5 text-emerald-400" />
                <h2 className="text-sm font-semibold text-white">System Automation & Hotkeys</h2>
              </div>
              <button 
                onClick={() => setActiveModal(null)}
                className="p-1 text-zinc-400 hover:text-white rounded-lg hover:bg-[#202127]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              <div className="p-3.5 rounded-xl bg-[#131418] border border-[#262831] space-y-2">
                <div className="font-semibold text-white">Global Hold-to-Talk</div>
                <div className="flex items-center space-x-2">
                  <kbd className="px-2 py-1 bg-[#252732] rounded border border-[#323642] text-zinc-200 font-mono font-bold">Super</kbd>
                  <span className="text-zinc-500">+</span>
                  <kbd className="px-2 py-1 bg-[#252732] rounded border border-[#323642] text-zinc-200 font-mono font-bold">Shift</kbd>
                  <span className="text-zinc-500">+</span>
                  <kbd className="px-2 py-1 bg-[#252732] rounded border border-[#323642] text-zinc-200 font-mono font-bold">J</kbd>
                </div>
                <p className="text-zinc-400 text-[11px]">
                  Monitored via Linux kernel event interface with hardware key-release detection.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#131418] border border-[#262831] space-y-1.5">
                <div className="font-semibold text-white">Wayland Paste Injection</div>
                <p className="text-zinc-400 text-[11px]">
                  Formatted dictation is automatically copied to system clipboard via <code className="text-blue-400">wl-copy</code> and injected using virtual keyboard <code className="text-blue-400">Ctrl+V</code>.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#131418] border border-[#262831] space-y-1.5">
                <div className="font-semibold text-white">Audio Capture Engine</div>
                <p className="text-zinc-400 text-[11px]">
                  Current active device: <span className="text-emerald-400 font-mono">{systemStatus.audio_device}</span>
                </p>
              </div>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
