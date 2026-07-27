import React, { useState } from 'react';
import { approvePendingWorkflow } from '../services/api';
import { ShieldCheck, Loader2, CheckCircle2 } from 'lucide-react';

export default function ManagerDashboard({ user }) {
  const [threadId, setThreadId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleApprove = async (e) => {
    e.preventDefault();
    if (!threadId.trim()) return;
    
    setLoading(true);
    setResult(null);
    try {
      const response = await approvePendingWorkflow(threadId.trim(), user.userId);
      setResult({ success: true, message: `Workflow ${threadId} successfully approved and resumed.` });
      setThreadId('');
    } catch (err) {
      setResult({ success: false, message: `Approval failed. Is the thread ID correct? (${err.message})` });
    } finally {
      setLoading(false);
    }
  };

  if (user?.role !== 'Manager' && user?.role !== 'Admin') {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <div className="glass-card" style={{ padding: '40px', textAlign: 'center', maxWidth: '400px' }}>
          <ShieldCheck size={48} color="var(--danger)" style={{ marginBottom: '16px' }} />
          <h2 style={{ color: 'var(--danger)' }}>Access Denied</h2>
          <p>You must be logged in as a Manager or Admin to access the Approval Dashboard.</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '600px', margin: '40px auto' }}>
      <div className="glass-panel animate-fade-in" style={{ padding: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px', borderBottom: '1px solid var(--surface-border)', paddingBottom: '24px' }}>
          <div style={{ background: 'var(--success-glow)', padding: '12px', borderRadius: '12px' }}>
            <ShieldCheck size={32} color="var(--success)" />
          </div>
          <div>
            <h2 style={{ margin: 0 }}>Manager Approval Dashboard</h2>
            <p style={{ margin: 0, fontSize: '0.9rem' }}>Human-in-the-Loop Gateway</p>
          </div>
        </div>

        <p style={{ marginBottom: '24px' }}>
          Enter the Thread ID of the paused workflow to inject your managerial approval signature and resume the DAG execution.
        </p>

        {result && (
          <div style={{ 
            background: result.success ? 'var(--success-glow)' : 'rgba(239, 68, 68, 0.2)', 
            border: `1px solid ${result.success ? 'var(--success)' : 'var(--danger)'}`,
            padding: '16px', 
            borderRadius: '8px', 
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            {result.success && <CheckCircle2 color="var(--success)" />}
            {result.message}
          </div>
        )}

        <form onSubmit={handleApprove} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-secondary)' }}>Paused Thread ID</label>
            <input 
              type="text" 
              className="input-field" 
              placeholder="e.g., test_appr_123" 
              value={threadId} 
              onChange={(e) => setThreadId(e.target.value)} 
              required
            />
          </div>
          
          <button type="submit" className="btn btn-success" disabled={loading || !threadId.trim()} style={{ padding: '12px', marginTop: '8px' }}>
            {loading ? <Loader2 size={18} className="animate-pulse" style={{ animation: 'spin 1s linear infinite' }} /> : 'Approve Transaction'}
          </button>
        </form>
      </div>
    </div>
  );
}
