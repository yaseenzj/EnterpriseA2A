import React, { useState, useEffect } from 'react';
import { fetchMyHistory } from '../services/api';
import { Clock, CheckCircle2, XCircle, Loader2, RefreshCw, AlertTriangle } from 'lucide-react';

const STATUS_META = {
  COMPLETED:           { color: 'var(--success)', bg: 'rgba(16,185,129,0.15)', Icon: CheckCircle2 },
  APPROVED_AND_COMPLETED: { color: 'var(--success)', bg: 'rgba(16,185,129,0.15)', Icon: CheckCircle2 },
  PENDING_APPROVAL:    { color: 'var(--warning)', bg: 'rgba(245,158,11,0.15)', Icon: AlertTriangle },
  RUNNING:             { color: 'var(--primary)', bg: 'rgba(59,130,246,0.15)', Icon: Loader2 },
  FAILED:              { color: 'var(--danger)', bg: 'rgba(239,68,68,0.15)', Icon: XCircle },
};

export default function MyRequestsTab() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await fetchMyHistory();
      setHistory(data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="glass-panel" style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ margin: 0 }}>My Request History</h3>
        <button className="btn btn-outline" onClick={load} style={{ padding: '8px 14px' }}><RefreshCw size={15} /></button>
      </div>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} /></div>
      ) : history.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No requests submitted yet.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {history.map((wf, i) => {
            const meta = STATUS_META[wf.status] || STATUS_META.FAILED;
            return (
              <div key={i} className="glass-card" style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 4 }}>{wf.thread_id}</div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Started: {wf.start_time ? new Date(wf.start_time).toLocaleString() : '—'}</div>
                  {wf.duration_seconds && <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Duration: {wf.duration_seconds}s</div>}
                </div>
                <div style={{ background: meta.bg, color: meta.color, padding: '6px 14px', borderRadius: 20, fontSize: '0.8rem', fontWeight: 600 }}>
                  {wf.status}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
