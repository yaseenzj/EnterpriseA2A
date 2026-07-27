import React, { useState, useEffect } from 'react';
import { Building2, LogOut, Bell, CheckCircle, AlertTriangle, Info } from 'lucide-react';
import { getAuthData, clearAuthData } from './services/api';
import AuthPage from './pages/AuthPage';
import EmployeeDashboard from './pages/EmployeeDashboard';
import ManagerDashboard from './pages/ManagerDashboard';
import AdminDashboard from './pages/AdminDashboard';
import './index.css';

const ROLE_COLORS = { Admin: '#a855f7', Manager: 'var(--success)', Employee: 'var(--primary)' };

function NotificationToasts({ userId }) {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    if (!userId) return;
    const poll = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:9006/api/v1/notifications?user_id=${userId}`, {
          headers: { Authorization: `Bearer ${getAuthData()?.access_token}` }
        });
        const data = await res.json();
        setNotifications((data.notifications || []).slice(0, 4));
      } catch (e) {}
    };
    poll();
    const iv = setInterval(poll, 6000);
    return () => clearInterval(iv);
  }, [userId]);

  return (
    <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1000, display: 'flex', flexDirection: 'column-reverse', gap: 10, maxWidth: 340 }}>
      {notifications.map((n, i) => {
        const isSuccess = n.type === 'SUCCESS';
        const isAlert = n.type === 'ALERT';
        return (
          <div key={n.id || i} className="glass-card animate-fade-in" style={{
            padding: '14px 18px', display: 'flex', gap: 12, alignItems: 'flex-start',
            background: isSuccess ? 'rgba(16,185,129,0.12)' : isAlert ? 'rgba(245,158,11,0.12)' : 'rgba(59,130,246,0.12)',
            borderColor: isSuccess ? 'var(--success)' : isAlert ? 'var(--warning)' : 'var(--primary)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)'
          }}>
            {isSuccess ? <CheckCircle size={18} color="var(--success)" style={{ flexShrink: 0 }} /> : isAlert ? <AlertTriangle size={18} color="var(--warning)" style={{ flexShrink: 0 }} /> : <Info size={18} color="var(--primary)" style={{ flexShrink: 0 }} />}
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 3 }}>{new Date(n.timestamp || n.created_at).toLocaleTimeString()}</div>
              <div style={{ fontSize: '0.9rem', lineHeight: 1.4 }}>{n.message}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(() => getAuthData()?.user || null);

  const handleAuth = (userObj) => setUser(userObj);
  const handleLogout = () => { clearAuthData(); setUser(null); };

  if (!user) return <AuthPage onAuth={handleAuth} />;

  const DashboardComponent = user.role === 'Admin' ? AdminDashboard : user.role === 'Manager' ? ManagerDashboard : EmployeeDashboard;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100%' }}>
      {/* Top Nav */}
      <nav className="glass-panel" style={{ margin: '12px 16px 0', padding: '12px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 34, height: 34, borderRadius: 8, background: 'var(--primary)', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Building2 size={18} color="white" />
          </div>
          <span style={{ fontWeight: 700, fontSize: '1.05rem' }}>Enterprise A2A</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{user.username}</div>
            <div style={{ fontSize: '0.75rem' }}>
              <span style={{ color: ROLE_COLORS[user.role] || 'var(--text-muted)', fontWeight: 600 }}>{user.role}</span>
              {user.department && <span style={{ color: 'var(--text-muted)' }}> · {user.department}</span>}
            </div>
          </div>
          <button className="btn btn-outline" onClick={handleLogout} style={{ padding: '8px 14px', fontSize: '0.85rem' }}>
            <LogOut size={15} /> Logout
          </button>
        </div>
      </nav>

      {/* Dashboard */}
      <main style={{ flex: 1, padding: '16px', minHeight: 0, overflow: 'hidden' }}>
        <DashboardComponent user={user} />
      </main>

      {/* Global Notification Toasts */}
      <NotificationToasts userId={user.id} />
    </div>
  );
}
