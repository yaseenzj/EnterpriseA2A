import React, { useState } from 'react';
import { MessageSquare, ClipboardList } from 'lucide-react';
import ChatTab from '../components/ChatTab';
import MyRequestsTab from '../components/MyRequestsTab';

const TABS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'requests', label: 'My Requests', icon: ClipboardList },
];

export default function EmployeeDashboard({ user }) {
  const [tab, setTab] = useState('chat');
  return (
    <DashboardShell tabs={TABS} activeTab={tab} onTab={setTab}>
      {tab === 'chat' && <ChatTab user={user} />}
      {tab === 'requests' && <MyRequestsTab />}
    </DashboardShell>
  );
}

export function DashboardShell({ tabs, activeTab, onTab, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 0 }}>
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, background: 'rgba(0,0,0,0.3)', padding: 4, borderRadius: 12, width: 'fit-content' }}>
        {tabs.map(t => {
          const Icon = t.icon;
          const active = activeTab === t.id;
          return (
            <button key={t.id} onClick={() => onTab(t.id)} style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '9px 18px', borderRadius: 9, border: 'none',
              cursor: 'pointer', fontFamily: 'var(--font-sans)', fontWeight: 500, fontSize: '0.9rem',
              background: active ? 'var(--primary)' : 'transparent',
              color: active ? 'white' : 'var(--text-secondary)',
              transition: 'all 0.2s ease'
            }}>
              <Icon size={16} /> {t.label}
            </button>
          );
        })}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        {children}
      </div>
    </div>
  );
}
