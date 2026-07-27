import React, { useState, useEffect } from 'react';
import { fetchNotifications } from '../services/api';
import { Bell, Info, CheckCircle, AlertTriangle, X } from 'lucide-react';

export default function Notifications({ userId }) {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    if (!userId) return;

    // Poll every 5 seconds for demo purposes
    const interval = setInterval(async () => {
      try {
        const data = await fetchNotifications(userId);
        // Only keep the latest 5 to avoid clutter
        setNotifications(data.notifications.slice(0, 5));
      } catch (err) {
        console.error("Failed to fetch notifications");
      }
    }, 5000);

    // Initial fetch
    fetchNotifications(userId).then(data => setNotifications(data.notifications.slice(0, 5))).catch(() => {});

    return () => clearInterval(interval);
  }, [userId]);

  if (notifications.length === 0) return null;

  return (
    <div style={{ position: 'fixed', top: '80px', right: '24px', zIndex: 1000, display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '350px' }}>
      {notifications.map((n) => {
        let bgColor = 'var(--surface)';
        let borderColor = 'var(--surface-border)';
        let Icon = Info;
        let iconColor = 'var(--primary)';

        if (n.type === 'SUCCESS') {
          bgColor = 'rgba(16, 185, 129, 0.1)';
          borderColor = 'var(--success)';
          Icon = CheckCircle;
          iconColor = 'var(--success)';
        } else if (n.type === 'ALERT') {
          bgColor = 'rgba(245, 158, 11, 0.1)';
          borderColor = 'var(--warning)';
          Icon = AlertTriangle;
          iconColor = 'var(--warning)';
        }

        return (
          <div key={n.id} className="glass-card animate-fade-in" style={{ 
            background: bgColor, 
            border: `1px solid ${borderColor}`,
            padding: '16px',
            display: 'flex',
            gap: '12px',
            alignItems: 'flex-start',
            boxShadow: '0 10px 25px rgba(0,0,0,0.5)'
          }}>
            <Icon size={20} color={iconColor} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                {new Date(n.timestamp).toLocaleTimeString()}
              </div>
              <div style={{ fontSize: '0.95rem' }}>{n.message}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
