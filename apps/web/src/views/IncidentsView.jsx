import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, ShieldAlert, Clock, ArrowRight, Zap } from 'lucide-react';

export default function IncidentsView({ incidents, onNavigate }) {
  const [filter, setFilter] = useState("ALL");

  const filtered = filter === "ALL"
    ? incidents
    : incidents.filter(i => i.status === filter);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
            Correlated Incidents & Alert Compression
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Temporal proximity clustering and lineage topology alert compression engine
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {["ALL", "INVESTIGATING", "OPEN", "RESOLVED"].map(st => (
            <button
              key={st}
              className={`btn btn-sm ${filter === st ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {filtered.map(inc => (
          <div
            key={inc.id}
            className="card"
            style={{
              cursor: 'pointer',
              borderLeft: `4px solid ${inc.severity === 'CRITICAL' ? 'var(--status-critical)' : 'var(--status-warning)'}`
            }}
            onClick={() => onNavigate('rootcause', { incidentId: inc.id })}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                  <span className={`badge badge-${inc.severity === 'CRITICAL' ? 'critical' : 'warning'}`}>
                    {inc.severity}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {inc.id}
                  </span>
                  <span className="badge badge-info">{inc.status}</span>
                </div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>{inc.title}</h3>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className="badge badge-passed" style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
                  <Zap size={14} /> {inc.compression_ratio} Alert Compression
                </span>
                <button className="btn btn-outline btn-sm">
                  Investigate <ArrowRight size={14} />
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '28px', fontSize: '0.82rem', color: 'var(--text-muted)', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
              <span>Detected: <strong>{inc.start_time}</strong></span>
              <span>Compressed Alerts: <strong>{inc.anomaly_count}</strong></span>
              <span>Affected Lineage: <strong>{inc.affected_nodes.join(' → ')}</strong></span>
              <span>Predicted Root Cause: <strong style={{ color: 'var(--accent-cyan)' }}>{inc.top_root_cause.type}</strong> ({Math.round(inc.top_root_cause.confidence * 100)}% confidence)</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
