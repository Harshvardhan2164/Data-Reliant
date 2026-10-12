import React from 'react';
import { Database, AlertTriangle, CheckCircle, Cpu, Activity, ArrowUpRight, TrendingUp } from 'lucide-react';

export default function OverviewView({ datasets, incidents, anomalies, onNavigate }) {
  const healthyCount = datasets.filter(d => d.status === "HEALTHY").length;
  const criticalIncidents = incidents.filter(i => i.severity === "CRITICAL" && i.status !== "RESOLVED").length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* KPI Cards Grid */}
      <div className="metric-grid">
        <div className="metric-card accent-indigo">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="metric-label">Monitored Datasets</span>
            <Database size={18} color="var(--accent-indigo)" />
          </div>
          <span className="metric-value">{datasets.length}</span>
          <div className="metric-footer">
            <span style={{ color: 'var(--status-passed)' }}>● {healthyCount} Healthy</span>
            <span>· 1 Warning</span>
          </div>
        </div>

        <div className="metric-card accent-rose">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="metric-label">Active Incidents</span>
            <AlertTriangle size={18} color="var(--status-critical)" />
          </div>
          <span className="metric-value" style={{ color: 'var(--status-critical)' }}>{criticalIncidents}</span>
          <div className="metric-footer">
            <span>Alert Compression: <strong>2.5x</strong></span>
          </div>
        </div>

        <div className="metric-card accent-emerald">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="metric-label">Quality Pass Rate</span>
            <CheckCircle size={18} color="var(--status-passed)" />
          </div>
          <span className="metric-value" style={{ color: 'var(--status-passed)' }}>98.4%</span>
          <div className="metric-footer">
            <span>10 Active Rule Suites</span>
          </div>
        </div>

        <div className="metric-card accent-cyan">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="metric-label">Root-Cause Accuracy</span>
            <Cpu size={18} color="var(--accent-cyan)" />
          </div>
          <span className="metric-value" style={{ color: 'var(--accent-cyan)' }}>92.3%</span>
          <div className="metric-footer">
            <span>Top-3 Research Benchmark</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Active Incidents & Live Detections */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px' }}>
        {/* Active Incidents */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <AlertTriangle size={18} color="var(--status-critical)" />
              Active Incident Intelligence
            </h2>
            <button
              id="btn-goto-incidents"
              className="btn btn-outline btn-sm"
              onClick={() => onNavigate('incidents')}
            >
              View All <ArrowUpRight size={14} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {incidents.slice(0, 3).map(inc => (
              <div
                key={inc.id}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '16px',
                  cursor: 'pointer',
                  transition: 'border-color 150ms ease'
                }}
                onClick={() => onNavigate('rootcause', { incidentId: inc.id })}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span className={`badge badge-${inc.severity === 'CRITICAL' ? 'critical' : 'warning'}`}>
                      {inc.severity}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {inc.id}
                    </span>
                  </div>
                  <span className="badge badge-info">{inc.compression_ratio} Compressed</span>
                </div>
                <h4 style={{ fontSize: '0.92rem', fontWeight: 600, marginBottom: '6px' }}>{inc.title}</h4>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-faint)', display: 'flex', gap: '12px' }}>
                  <span>Affected: {inc.affected_nodes.join(', ')}</span>
                  <span>· Root Cause: <strong style={{ color: 'var(--accent-cyan)' }}>{inc.top_root_cause.type}</strong> ({Math.round(inc.top_root_cause.confidence * 100)}%)</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Live Anomaly Stream */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              <Activity size={18} color="var(--accent-cyan)" />
              Live Anomaly Detections
            </h2>
            <button
              id="btn-goto-anomalies"
              className="btn btn-outline btn-sm"
              onClick={() => onNavigate('anomalies')}
            >
              Explorer <ArrowUpRight size={14} />
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {anomalies.map(anom => (
              <div
                key={anom.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  background: 'rgba(255, 255, 255, 0.015)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{anom.metric}</span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
                      [{anom.detector}]
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Dataset: {anom.dataset} · Score: {anom.anomaly_score}σ
                  </span>
                </div>
                <span className={`badge badge-${anom.severity === 'HIGH' ? 'critical' : 'warning'}`}>
                  {anom.severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
