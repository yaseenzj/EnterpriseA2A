import React, { useState } from 'react';
import { authenticate } from '../services/api';
import { Fingerprint, Loader2 } from 'lucide-react';

export default function Login({ onLogin }) {
  const [userId, setUserId] = useState('usr_9921');
  const [role, setRole] = useState('Employee');
  const [department, setDepartment] = useState('Sales_Team');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      await authenticate(userId, role, department);
      onLogin({ userId, role, department });
    } catch (err) {
      setError('Authentication failed. Backend might be unreachable.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', width: '100vw' }}>
      <div className="glass-panel animate-fade-in" style={{ padding: '40px', width: '100%', maxWidth: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ background: 'var(--surface-hover)', width: '64px', height: '64px', borderRadius: '50%', display: 'flex', justifyContent: 'center', alignItems: 'center', margin: '0 auto 16px', color: 'var(--primary)' }}>
            <Fingerprint size={32} />
          </div>
          <h2>Enterprise Portal</h2>
          <p style={{ margin: 0 }}>Simulate User Identity</p>
        </div>

        {error && (
          <div style={{ background: 'var(--danger)', color: 'white', padding: '12px', borderRadius: '8px', marginBottom: '16px', fontSize: '0.9rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>User ID</label>
            <input 
              type="text" 
              className="input-field" 
              value={userId} 
              onChange={(e) => setUserId(e.target.value)} 
              required
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Role</label>
            <select className="input-field" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="Employee">Employee</option>
              <option value="Manager">Manager</option>
              <option value="Admin">Admin</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Department</label>
            <select className="input-field" value={department} onChange={(e) => setDepartment(e.target.value)}>
              <option value="Sales_Team">Sales Team</option>
              <option value="IT_Team">IT Team</option>
              <option value="Finance_Team">Finance Team</option>
            </select>
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: '16px', width: '100%', padding: '12px' }}>
            {loading ? <Loader2 size={18} className="animate-pulse" style={{ animation: 'spin 1s linear infinite' }} /> : 'Authenticate'}
          </button>
        </form>
      </div>
    </div>
  );
}
