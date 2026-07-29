import React, { useState, useEffect } from 'react';
import { MessageSquare, ClipboardList, ShieldCheck, History, BarChart3, Users, RefreshCw, Loader2, ChevronDown } from 'lucide-react';
import ChatTab from '../components/ChatTab';
import MyRequestsTab from '../components/MyRequestsTab';
import PendingApprovalsTab from '../components/PendingApprovalsTab';
import MyActionsTab from '../components/MyActionsTab';
import { DashboardShell } from './EmployeeDashboard';
import { fetchAllApprovals, fetchMetrics, fetchAllUsers, updateUserRole, updateUserDepartment } from '../services/api';

const TABS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'requests', label: 'My Requests', icon: ClipboardList },
  { id: 'pending', label: 'Pending Approvals', icon: ShieldCheck },
  { id: 'all-approvals', label: 'All Approvals', icon: History },
  { id: 'metrics', label: 'Metrics', icon: BarChart3 },
  { id: 'users', label: 'Users', icon: Users },
];

function MetricsTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const load = async () => { setLoading(true); try { setData(await fetchMetrics()); } catch (e) {} finally { setLoading(false); } };
  useEffect(() => { load(); }, []);
  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} /></div>;
  if (!data) return <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>Failed to load metrics.</div>;
  const successRate = data.total_workflows > 0 ? ((data.successful_workflows / data.total_workflows) * 100).toFixed(0) : 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>System Metrics</h3>
        <button className="btn btn-outline" onClick={load} style={{ padding: '8px 14px' }}><RefreshCw size={15} /></button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
        {[
          { label: 'Total Workflows', value: data.total_workflows, color: 'var(--primary)' },
          { label: 'Success Rate', value: `${successRate}%`, color: 'var(--success)' },
          { label: 'Failed', value: data.failed_workflows, color: 'var(--danger)' },
          { label: 'Pending', value: data.pending_workflows, color: 'var(--warning)' },
          { label: 'Avg Time', value: `${data.avg_execution_time_seconds}s`, color: 'var(--text-secondary)' },
        ].map((m, i) => (
          <div key={i} className="glass-card" style={{ padding: '20px', textAlign: 'center' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 8 }}>{m.label}</div>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>
      <div className="glass-panel" style={{ padding: 20, flex: 1, overflowY: 'auto' }}>
        <h4 style={{ marginBottom: 16 }}>Recent Workflows</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
          <thead><tr style={{ borderBottom: '1px solid var(--surface-border)' }}>{['Thread ID', 'User', 'Status', 'Duration'].map(h => <th key={h} style={{ padding: '10px 12px', textAlign: 'left', color: 'var(--text-secondary)', fontWeight: 500 }}>{h}</th>)}</tr></thead>
          <tbody>
            {(data.recent_workflows || []).map((w, i) => (
              <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{w.thread_id}</td>
                <td style={{ padding: '10px 12px' }}>{w.user_id || '—'}</td>
                <td style={{ padding: '10px 12px' }}><span style={{ background: w.status === 'COMPLETED' ? 'rgba(16,185,129,0.15)' : w.status === 'PENDING_APPROVAL' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)', color: w.status === 'COMPLETED' ? 'var(--success)' : w.status === 'PENDING_APPROVAL' ? 'var(--warning)' : 'var(--danger)', padding: '3px 10px', borderRadius: 12, fontSize: '0.8rem' }}>{w.status}</span></td>
                <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{w.duration_seconds != null ? `${w.duration_seconds}s` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AllApprovalsTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = async () => { setLoading(true); try { setItems(await fetchAllApprovals()); } catch (e) {} finally { setLoading(false); } };
  useEffect(() => { load(); }, []);
  const STATUS_COLORS = { APPROVED: 'var(--success)', FAILED: 'var(--danger)', PENDING: 'var(--warning)' };
  return (
    <div className="glass-panel" style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h3 style={{ margin: 0 }}>All Approvals (System-wide)</h3>
        <button className="btn btn-outline" onClick={load} style={{ padding: '8px 14px' }}><RefreshCw size={15} /></button>
      </div>
      {loading ? <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} /></div> : items.length === 0 ? <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>No approval records found.</div> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((item, i) => (
            <div key={i} className="glass-card" style={{ padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.85rem' }}>By <strong>{item.requested_by}</strong></span>
                  {item.actioned_by && <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>→ actioned by <strong>{item.actioned_by}</strong></span>}
                </div>
                {item.request_summary && <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontStyle: 'italic', marginBottom: 4 }}>"{item.request_summary}"</div>}
                <div style={{ fontFamily: 'monospace', fontSize: '0.78rem', color: 'var(--text-muted)' }}>{item.thread_id}</div>
              </div>
              <span style={{ background: item.status === 'APPROVED' ? 'rgba(16,185,129,0.15)' : item.status === 'PENDING' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)', color: STATUS_COLORS[item.status] || 'var(--text-secondary)', padding: '5px 12px', borderRadius: 20, fontSize: '0.8rem', fontWeight: 600, flexShrink: 0 }}>{item.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function UsersTab() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(null);
  const load = async () => { setLoading(true); try { setUsers(await fetchAllUsers()); } catch (e) {} finally { setLoading(false); } };
  useEffect(() => { load(); }, []);

  const changeRole = async (userId, newRole) => {
    setSaving(userId);
    try {
      await updateUserRole(userId, newRole);
      setUsers(u => u.map(x => x.id === userId ? { ...x, role: newRole } : x));
    } catch (e) { alert(`Failed: ${e.response?.data?.detail || e.message}`); }
    finally { setSaving(null); }
  };

  const changeDept = async (userId, newDept) => {
    setSaving(userId + '_dept');
    try {
      await updateUserDepartment(userId, newDept);
      setUsers(u => u.map(x => x.id === userId ? { ...x, department: newDept } : x));
    } catch (e) { alert(`Failed: ${e.response?.data?.detail || e.message}`); }
    finally { setSaving(null); }
  };

  return (
    <div className="glass-panel" style={{ padding: 24, height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
        <h3 style={{ margin: 0 }}>User Management</h3>
        <button className="btn btn-outline" onClick={load} style={{ padding: '8px 14px' }}><RefreshCw size={15} /></button>
      </div>
      {loading ? <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}><Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} /></div> : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {users.map((u, i) => (
            <div key={i} className="glass-card" style={{ padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600 }}>{u.username}</div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{u.department} · Joined {new Date(u.created_at).toLocaleDateString()}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                {(saving === u.id || saving === u.id + '_dept') && <Loader2 size={16} style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} />}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right' }}>Role</div>
                  <select
                    className="input-field"
                    style={{ width: 130, padding: '7px 10px', fontSize: '0.85rem' }}
                    value={u.role}
                    onChange={e => changeRole(u.id, e.target.value)}
                    disabled={!!saving}
                  >
                    {['Employee', 'Manager', 'Admin'].map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right' }}>Department</div>
                  <select
                    className="input-field"
                    style={{ width: 140, padding: '7px 10px', fontSize: '0.85rem' }}
                    value={u.department}
                    onChange={e => changeDept(u.id, e.target.value)}
                    disabled={!!saving}
                  >
                    {['Sales', 'IT', 'Finance', 'HR', 'Operations', 'Marketing'].map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AdminDashboard({ user }) {
  const [tab, setTab] = useState('pending');
  return (
    <DashboardShell tabs={TABS} activeTab={tab} onTab={setTab}>
      {tab === 'chat' && <ChatTab user={user} />}
      {tab === 'requests' && <MyRequestsTab />}
      {tab === 'pending' && <PendingApprovalsTab user={user} />}
      {tab === 'all-approvals' && <AllApprovalsTab />}
      {tab === 'metrics' && <MetricsTab />}
      {tab === 'users' && <UsersTab />}
    </DashboardShell>
  );
}
