import React, { useState, useRef, useEffect } from 'react';
import { orchestrateRequest } from '../services/api';
import { Send, Loader2, Bot, User, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function ChatTab({ user }) {
  const storageKey = `chat_${user.id}`;
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) return JSON.parse(saved);
    return [{ role: 'system', content: `Hi ${user.username}! I'm your Enterprise Orchestrator. What can I help you with today?` }];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
    localStorage.setItem(storageKey, JSON.stringify(messages));
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const text = input.trim();
    setMessages(m => [...m, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);
    try {
      const res = await orchestrateRequest(text);
      let content = 'Request processed.';
      let status = res.status;
      if (res.status === 'PENDING_APPROVAL') {
        content = `⏳ Your request requires manager approval.\n\nThread ID: ${res.thread_id}\n\nA manager will review and approve this shortly. You will be notified when it is done.`;
      } else if (res.status === 'COMPLETED' || res.status === 'APPROVED_AND_COMPLETED') {
        content = res.response?.conversational_reply || `✅ Request completed successfully!\n\n${JSON.stringify(res.response?.results, null, 2)}`;
      } else if (res.status === 'FAILED') {
        content = `❌ Request failed.\n\nReason: ${res.error || 'Unknown error'}`;
      }
      setMessages(m => [...m, { role: 'system', content, status }]);
    } catch (err) {
      setMessages(m => [...m, { role: 'system', content: `Connection error: ${err.message}`, status: 'FAILED' }]);
    } finally {
      setLoading(false);
    }
  };

  const getBubbleStyle = (msg) => {
    if (msg.role === 'user') return { background: 'rgba(59,130,246,0.15)', border: '1px solid var(--primary)' };
    if (msg.status === 'PENDING_APPROVAL') return { background: 'rgba(245,158,11,0.1)', border: '1px solid var(--warning)' };
    if (msg.status === 'FAILED') return { background: 'rgba(239,68,68,0.1)', border: '1px solid var(--danger)' };
    if (msg.status === 'COMPLETED' || msg.status === 'APPROVED_AND_COMPLETED') return { background: 'rgba(16,185,129,0.1)', border: '1px solid var(--success)' };
    return { background: 'var(--surface)', border: '1px solid var(--surface-border)' };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 16 }}>
      <div className="glass-panel" style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
        {messages.map((msg, i) => (
          <div key={i} className="animate-fade-in" style={{ display: 'flex', gap: 14, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
            <div style={{ width: 38, height: 38, borderRadius: '50%', background: msg.role === 'user' ? 'var(--primary)' : 'rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'center', alignItems: 'center', flexShrink: 0 }}>
              {msg.role === 'user' ? <User size={18} color="white" /> : <Bot size={18} color="var(--primary)" />}
            </div>
            <div style={{ ...getBubbleStyle(msg), padding: '14px 18px', borderRadius: 14, maxWidth: '78%', whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.65, fontSize: '0.95rem' }}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            <div style={{ width: 38, height: 38, borderRadius: '50%', background: 'rgba(255,255,255,0.08)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <Bot size={18} color="var(--primary)" />
            </div>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--surface-border)', padding: '14px 18px', borderRadius: 14, display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Agents working on it...
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form onSubmit={handleSubmit} className="glass-panel" style={{ padding: 14, display: 'flex', gap: 12 }}>
        <input className="input-field" style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: 'none' }} placeholder={`Ask me anything, ${user.username}... (e.g. 'Book a conference room for 3pm')`} value={input} onChange={e => setInput(e.target.value)} disabled={loading} />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()} style={{ padding: '0 22px' }}><Send size={17} /></button>
      </form>
    </div>
  );
}
