import React, { useState, useEffect } from 'react';
import { fetchMetrics } from '../services/api';
import { BarChart3, Clock, CheckCircle2, XCircle, RefreshCw } from 'lucide-react';

export default function AdminMetrics() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMetrics = async () => {
    setLoading(true);
    try {
      const data = await fetchMetrics();
      setMetrics(data);
    } catch (err) {
      console.error("Failed to load metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  if (loading && !metrics) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <RefreshCw size={32} className="animate-pulse" style={{ animation: 'spin 1s linear infinite' }} />
      </div>
    );
  }

  if (!metrics) {
    return <div>Error loading metrics</div>;
  }

  return (
    <div style={{ maxWidth: '1000px', margin: '24px auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '12px' }}>
          <BarChart3 color="var(--primary)" /> Enterprise Execution Metrics
        </h2>
        <button className="btn btn-outline" onClick={loadMetrics}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px' }}>
        <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>Total Workflows</div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'white' }}>{metrics.total_workflows}</div>
        </div>

        <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={16} color="var(--success)" /> Success Rate
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--success)' }}>
            {((metrics.successful_workflows / Math.max(1, metrics.total_workflows)) * 100).toFixed(0)}%
          </div>
        </div>

        <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
            <XCircle size={16} color="var(--danger)" /> Failed Workflows
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--danger)' }}>{metrics.failed_workflows}</div>
        </div>

        <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
            <Clock size={16} color="var(--warning)" /> Avg Execution Time
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--warning)' }}>
            {metrics.avg_execution_time_seconds.toFixed(2)}s
          </div>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3>Recent Workflows</h3>
        <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--surface-border)' }}>
              <th style={{ padding: '12px', color: 'var(--text-secondary)' }}>Thread ID</th>
              <th style={{ padding: '12px', color: 'var(--text-secondary)' }}>User</th>
              <th style={{ padding: '12px', color: 'var(--text-secondary)' }}>Status</th>
              <th style={{ padding: '12px', color: 'var(--text-secondary)' }}>Duration (s)</th>
            </tr>
          </thead>
          <tbody>
            {metrics.recent_workflows.map((wf, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '12px', fontFamily: 'monospace' }}>{wf.thread_id}</td>
                <td style={{ padding: '12px' }}>{wf.user_id}</td>
                <td style={{ padding: '12px' }}>
                  <span style={{ 
                    background: wf.status === 'COMPLETED' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                    color: wf.status === 'COMPLETED' ? 'var(--success)' : 'var(--danger)',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '0.85rem'
                  }}>
                    {wf.status}
                  </span>
                </td>
                <td style={{ padding: '12px' }}>{wf.duration_seconds?.toFixed(2) || '-'}</td>
              </tr>
            ))}
            {metrics.recent_workflows.length === 0 && (
              <tr><td colSpan="4" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>No workflows recorded yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
