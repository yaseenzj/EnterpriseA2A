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
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* Left Panel — Branding */}
      <div style={{
        flex: 1,
        background: 'linear-gradient(135deg, #1e3a5f 0%, #0b0f19 100%)',
        display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
        padding: '48px', borderRight: '1px solid var(--surface-border)'
      }}>
        <div style={{ width: 64, height: 64, borderRadius: 16, background: 'var(--primary)', display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 24, boxShadow: '0 0 40px var(--primary-glow)' }}>
          <Building2 size={36} color="white" />
        </div>
        <h1 style={{ fontSize: '2rem', fontWeight: 800, textAlign: 'center', marginBottom: 8, color: 'white' }}>Enterprise A2A</h1>
        <p style={{ textAlign: 'center', color: 'var(--text-secondary)', maxWidth: 280, lineHeight: 1.6 }}>
          Multi-Agent AI Platform. Role-based access for Employees, Managers, and Admins.
        </p>
        <div style={{ marginTop: 48, display: 'flex', flexDirection: 'column', gap: 16, width: '100%', maxWidth: 260 }}>
          {['Employee → Chat & Request', 'Manager → Approvals Dashboard', 'Admin → Full System Control'].map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              <ChevronRight size={16} color="var(--primary)" /> {item}
            </div>
          ))}
        </div>
      </div>

      {/* Right Panel — Form */}
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 48 }}>
        <div className="glass-panel animate-fade-in" style={{ width: '100%', maxWidth: 420, padding: '40px' }}>
          {/* Toggle Tabs */}
          <div style={{ display: 'flex', background: 'rgba(0,0,0,0.3)', borderRadius: 10, padding: 4, marginBottom: 32 }}>
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

          <h2 style={{ marginBottom: 8 }}>{mode === 'login' ? 'Welcome back' : 'Create account'}</h2>
          <p style={{ marginBottom: 28, fontSize: '0.9rem' }}>{mode === 'login' ? 'Sign in to your Enterprise account.' : 'New accounts start as Employee. An Admin can upgrade your role.'}</p>

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
                <input className="input-field" style={{ paddingLeft: 42 }} placeholder="e.g. alice_smith" value={form.username} onChange={set('username')} required />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input className="input-field" style={{ paddingLeft: 42 }} type="password" placeholder="••••••••" value={form.password} onChange={set('password')} required />
              </div>
            </div>

            {mode === 'signup' && (
              <div>
                <label style={{ display: 'block', marginBottom: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Department</label>
                <select className="input-field" value={form.department} onChange={set('department')}>
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
    </div>
  );
}
