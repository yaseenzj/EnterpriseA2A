import React, { useState, useRef, useEffect } from 'react';
import { orchestrateRequest } from '../services/api';
import { Send, Loader2, Bot, User, AlertCircle } from 'lucide-react';

export default function ChatInterface({ user }) {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem(`chat_${user.userId}`);
    if (saved) return JSON.parse(saved);
    return [{ role: 'system', content: 'Welcome to the Enterprise Orchestrator. How can I assist you today?' }];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
    localStorage.setItem(`chat_${user.userId}`, JSON.stringify(messages));
  }, [messages, user.userId]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setInput('');
    setLoading(true);

    try {
      const response = await orchestrateRequest(userMessage, messages);
      
      let replyContent = "Request processed.";
      if (response.status === 'PENDING_APPROVAL') {
        replyContent = `Workflow paused for Manager Approval.\nThread ID: ${response.thread_id}\n\nPlease ask a manager to approve this transaction in the Approvals dashboard.`;
      } else if (response.status === 'COMPLETED' || response.status === 'APPROVED_AND_COMPLETED') {
        replyContent = response.response.conversational_reply || `Workflow completed successfully.\nFinal Result:\n${JSON.stringify(response.response.results, null, 2)}`;
      } else if (response.status === 'FAILED') {
        replyContent = `Workflow failed.\nError: ${response.error || 'Unknown error'}`;
      }

      setMessages(prev => [...prev, { 
        role: 'system', 
        content: replyContent,
        status: response.status 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'system', 
        content: `Error connecting to Orchestrator: ${err.message}`,
        status: 'FAILED'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', maxWidth: '900px', margin: '0 auto', gap: '16px' }}>
      
      <div className="glass-panel" style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ 
            display: 'flex', 
            gap: '16px', 
            alignItems: 'flex-start',
            flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
          }}>
            <div style={{ 
              width: '40px', 
              height: '40px', 
              borderRadius: '50%', 
              background: msg.role === 'user' ? 'var(--primary)' : 'var(--surface-border)',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              flexShrink: 0
            }}>
              {msg.role === 'user' ? <User size={20} color="white" /> : <Bot size={20} color="var(--primary)" />}
            </div>
            
            <div style={{ 
              background: msg.role === 'user' ? 'var(--primary-glow)' : 'var(--surface)', 
              padding: '16px', 
              borderRadius: '12px',
              border: msg.status === 'PENDING_APPROVAL' ? '1px solid var(--warning)' : 
                      msg.status === 'FAILED' ? '1px solid var(--danger)' : 
                      msg.role === 'user' ? '1px solid var(--primary)' : '1px solid var(--surface-border)',
              maxWidth: '80%',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              fontFamily: msg.content.includes('{') ? 'monospace' : 'inherit',
              fontSize: msg.content.includes('{') ? '0.85rem' : '1rem'
            }}>
              {msg.status === 'PENDING_APPROVAL' && <div style={{ color: 'var(--warning)', fontWeight: 'bold', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}><AlertCircle size={16}/> HUMAN-IN-THE-LOOP PAUSE</div>}
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
             <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--surface-border)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
              <Bot size={20} color="var(--primary)" />
            </div>
            <div style={{ background: 'var(--surface)', padding: '16px', borderRadius: '12px', display: 'flex', gap: '8px', alignItems: 'center', color: 'var(--text-secondary)' }}>
              <Loader2 size={16} className="animate-pulse" style={{ animation: 'spin 1s linear infinite' }} /> Orchestrating workflow...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="glass-panel" style={{ padding: '16px', display: 'flex', gap: '12px' }}>
        <input 
          type="text" 
          className="input-field" 
          placeholder="Ask the Orchestrator to do something (e.g., 'Book a flight' or 'Buy a software license')..." 
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={loading}
          style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: 'none' }}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()} style={{ padding: '0 24px' }}>
          <Send size={18} /> Send
        </button>
      </form>
      
    </div>
  );
}
