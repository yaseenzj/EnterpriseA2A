import React, { useState } from 'react';
import { MessageSquare, ClipboardList, ShieldCheck, History } from 'lucide-react';
import ChatTab from '../components/ChatTab';
import MyRequestsTab from '../components/MyRequestsTab';
import PendingApprovalsTab from '../components/PendingApprovalsTab';
import MyActionsTab from '../components/MyActionsTab';
import { DashboardShell } from './EmployeeDashboard';

const TABS = [
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'requests', label: 'My Requests', icon: ClipboardList },
  { id: 'pending', label: 'Pending Approvals', icon: ShieldCheck },
  { id: 'my-actions', label: 'My Actions', icon: History },
];

export default function ManagerDashboard({ user }) {
  const [tab, setTab] = useState('pending');
  return (
    <DashboardShell tabs={TABS} activeTab={tab} onTab={setTab}>
      {tab === 'chat' && <ChatTab user={user} />}
      {tab === 'requests' && <MyRequestsTab />}
      {tab === 'pending' && <PendingApprovalsTab user={user} />}
      {tab === 'my-actions' && <MyActionsTab />}
    </DashboardShell>
  );
}
