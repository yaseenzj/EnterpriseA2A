import React, { useState } from 'react';
import { login, signup } from '../services/api';
import { Building2, User, Lock, Loader2, ChevronRight } from 'lucide-react';

const DEPARTMENTS = ['Sales', 'IT', 'Finance', 'HR', 'Operations', 'Marketing'];

export default function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login'); // 'login' | 'signup'
  const [form, setForm] = useState({ username: '', password: '', department: 'Sales' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = mode === 'login'
        ? await login(form.username, form.password)
        : await signup(form.username, form.password, form.department);
      onAuth(data.user);
    } catch (err) {
      setError(err.response?.data?.detail || (mode === 'login' ? 'Invalid credentials.' : 'Signup failed. Username may be taken.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', justifyContent: 'center', alignItems: 'center', background: 'linear-gradient(135deg, #1e3a5f 0%, #0b0f19 100%)' }}>
      
      <div className="glass-panel animate-fade-in" style={{ width: '100%', maxWidth: 420, padding: '40px', background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(20px)', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 32 }}>
          <div style={{ width: 56, height: 56, borderRadius: 14, background: 'var(--primary)', display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 16, boxShadow: '0 0 30px var(--primary-glow)' }}>
            <Building2 size={32} color="white" />
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, textAlign: 'center', margin: 0, color: 'white' }}>Enterprise A2A</h1>
          <p style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: 8 }}>Multi-Agent AI Platform</p>
        </div>

        {/* Toggle Tabs */}
        <div style={{ display: 'flex', background: 'rgba(0,0,0,0.4)', borderRadius: 10, padding: 4, marginBottom: 24 }}>
          {['login', 'signup'].map(m => (
            <button key={m} onClick={() => { setMode(m); setError(''); }} style={{
              flex: 1, padding: '10px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600,
              background: mode === m ? 'var(--primary)' : 'transparent',
              color: mode === m ? 'white' : 'var(--text-secondary)',
              transition: 'all 0.2s ease', fontFamily: 'var(--font-sans)', fontSize: '0.95rem',
              textTransform: 'capitalize'
            }}>
              {m === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
          ))}
        </div>

        {error && (
          <div style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid var(--danger)', color: '#fca5a5', padding: '12px 16px', borderRadius: 8, marginBottom: 20, fontSize: '0.9rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Username</label>
            <div style={{ position: 'relative' }}>
              <User size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input className="input-field" style={{ paddingLeft: 42, background: 'rgba(255,255,255,0.05)' }} placeholder="e.g. alice_smith" value={form.username} onChange={set('username')} required />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Password</label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input className="input-field" style={{ paddingLeft: 42, background: 'rgba(255,255,255,0.05)' }} type="password" placeholder="••••••••" value={form.password} onChange={set('password')} required />
            </div>
          </div>

          {mode === 'signup' && (
            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Department</label>
              <select className="input-field" style={{ background: 'rgba(255,255,255,0.05)' }} value={form.department} onChange={set('department')}>
                {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
          )}

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ padding: '13px', marginTop: 8, width: '100%', fontSize: '1rem' }}>
            {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : (mode === 'login' ? 'Sign In' : 'Create Account')}
          </button>
        </form>
      </div>
    </div>
  );
}
