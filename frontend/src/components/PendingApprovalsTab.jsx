import React, { useState, useEffect } from 'react';
import { fetchPendingApprovals, approvePendingWorkflow } from '../services/api';
import { ShieldCheck, Loader2, RefreshCw, CheckCircle2, Clock, XCircle } from 'lucide-react';

export default function PendingApprovalsTab({ user }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(null);
  const [toast, setToast] = useState('');

  const load = async () => {
    setLoading(true);
    try { setItems(await fetchPendingApprovals()); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const handleAction = async (threadId, action) => {
    setApproving(threadId);
    try {
      await approvePendingWorkflow(threadId, user.username, action);
      setToast(action === 'APPROVE' ? `✅ Workflow ${threadId} approved and resumed!` : `✅ Workflow ${threadId} rejected!`);
      await load();
    } catch (e) {
      setToast(`❌ Failed to ${action.toLowerCase()}: ${e.response?.data?.detail || e.message}`);
    } finally {
      setApproving(null);
      setTimeout(() => setToast(''), 4000);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}><Clock size={20} color="var(--warning)" /> Pending Approvals</h3>
        <button className="btn btn-outline" onClick={load} style={{ padding: '8px 14px' }}><RefreshCw size={15} /></button>
      </div>

      {toast && (
        <div className="animate-fade-in" style={{ background: toast.startsWith('✅') ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', border: `1px solid ${toast.startsWith('✅') ? 'var(--success)' : 'var(--danger)'}`, padding: '12px 16px', borderRadius: 10, marginBottom: 16, fontSize: '0.9rem' }}>
          {toast}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} /></div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
          <ShieldCheck size={48} color="var(--success)" style={{ marginBottom: 12 }} />
          <p style={{ margin: 0 }}>No pending approvals. All clear!</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {items.map((item, i) => (
            <div key={i} className="glass-card animate-fade-in" style={{ padding: '20px', borderLeft: '3px solid var(--warning)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}><span style={{ color: 'var(--primary)' }}>{item.requested_by}</span> requested: {item.request_summary}</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 12, fontStyle: 'italic', background: 'rgba(255,255,255,0.05)', padding: '8px 12px', borderRadius: 6, borderLeft: '3px solid var(--primary)' }}>
                    "{item.raw_request || item.request_summary}"
                  </div>
                  <div style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)' }}>Thread: {item.thread_id}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Submitted: {new Date(item.created_at).toLocaleString()}</div>
                </div>
                <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                  <button
                    className="btn btn-outline"
                    disabled={approving === item.thread_id}
                    onClick={() => handleAction(item.thread_id, 'REJECT')}
                    style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}
                  >
                    {approving === item.thread_id
                      ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                      : <><XCircle size={16} /> Reject</>}
                  </button>
                  <button
                    className="btn btn-success"
                    disabled={approving === item.thread_id}
                    onClick={() => handleAction(item.thread_id, 'APPROVE')}
                  >
                    {approving === item.thread_id
                      ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                      : <><CheckCircle2 size={16} /> Approve</>}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
