import React, { useState, useEffect } from 'react';
import { fetchMyActions } from '../services/api';
import { History, Loader2, RefreshCw } from 'lucide-react';

const STATUS_COLORS = { APPROVED: 'var(--success)', FAILED: 'var(--danger)', PENDING: 'var(--warning)' };
const STATUS_BG = { APPROVED: 'rgba(16,185,129,0.15)', FAILED: 'rgba(239,68,68,0.15)', PENDING: 'rgba(245,158,11,0.15)' };

export default function MyActionsTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setItems(await fetchMyActions()); }
    catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="glass-panel" style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}><History size={20} color="var(--primary)" /> My Approval Actions</h3>
        <button className="btn btn-outline" onClick={load} style={{ padding: '8px 14px' }}><RefreshCw size={15} /></button>
      </div>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} /></div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>You haven't actioned any approvals yet.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {items.map((item, i) => (
            <div key={i} className="glass-card" style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 500, marginBottom: 4 }}>Request by <span style={{ color: 'var(--primary)' }}>{item.requested_by}</span></div>
                {item.request_summary && <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', fontStyle: 'italic', marginBottom: 4 }}>"{item.request_summary}"</div>}
                <div style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{item.thread_id}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{item.action_time ? new Date(item.action_time).toLocaleString() : '—'}</div>
              </div>
              <div style={{ background: STATUS_BG[item.status] || 'var(--surface)', color: STATUS_COLORS[item.status] || 'var(--text-secondary)', padding: '6px 14px', borderRadius: 20, fontSize: '0.8rem', fontWeight: 600 }}>
                {item.status}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
