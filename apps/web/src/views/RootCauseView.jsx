import React from 'react';
import { ArrowLeft, Cpu, ShieldCheck, Activity, GitFork, Clock, History, CheckCircle } from 'lucide-react';

export default function RootCauseView({ incidents, selectedIncidentId, onNavigate }) {
  const inc = incidents.find(i => i.id === selectedIncidentId) || incidents[0];
  const rc = inc.top_root_cause;

  const evidenceWeights = [
    { name: "Schema", weight: "25%", score: rc.evidence_breakdown.schema || 0.0, icon: ShieldCheck },
    { name: "Lineage Graph", weight: "20%", score: rc.evidence_breakdown.graph || 0.0, icon: GitFork },
    { name: "Statistical", weight: "20%", score: rc.evidence_breakdown.statistical || 0.0, icon: Activity },
    { name: "Temporal", weight: "15%", score: rc.evidence_breakdown.temporal || 0.0, icon: Clock },
    { name: "Propagation", weight: "10%", score: rc.evidence_breakdown.propagation || 0.0, icon: GitFork },
    { name: "Historical", weight: "10%", score: rc.evidence_breakdown.historical || 0.0, icon: History },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button
            className="btn btn-outline btn-sm"
            onClick={() => onNavigate('incidents')}
          >
            <ArrowLeft size={14} /> Back to Incidents
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
              <span className={`badge badge-${inc.severity === 'CRITICAL' ? 'critical' : 'warning'}`}>
                {inc.severity}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-faint)' }}>
                {inc.id}
              </span>
              <span className="badge badge-info">{inc.status}</span>
            </div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.3rem', fontWeight: 700 }}>
              {inc.title}
            </h2>
          </div>
        </div>

        <button className="btn btn-primary btn-sm">
          <CheckCircle size={14} /> Acknowledge & Mark Resolved
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '22px' }}>
        {/* Ranked Root Cause Candidates */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <Cpu size={18} color="var(--accent-cyan)" />
              Ranked Candidate Root Causes
            </h3>
            <span className="badge badge-info">Deterministic + ML Model</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{
              background: 'linear-gradient(145deg, rgba(6, 182, 212, 0.08), rgba(99, 102, 241, 0.04))',
              border: '1px solid var(--accent-cyan)',
              borderRadius: 'var(--radius-sm)',
              padding: '18px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span className="badge badge-passed" style={{ fontSize: '0.75rem' }}>RANK 1 (TOP CANDIDATE)</span>
                <span style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-cyan)', fontFamily: 'var(--font-heading)' }}>
                  {Math.round(rc.confidence * 100)}% Confidence
                </span>
              </div>
              <h4 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '6px' }}>{rc.type}</h4>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Deterministic multi-signal reasoning and random forest classifier agree this failure originates from anomalous null injection during producer ETL.
              </p>
            </div>

            <div style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '14px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span className="badge badge-info" style={{ fontSize: '0.72rem' }}>RANK 2</span>
                <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                  38% Confidence
                </span>
              </div>
              <h5 style={{ fontSize: '0.95rem', fontWeight: 600 }}>UPSTREAM_FAILURE</h5>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-faint)' }}>
                Secondary probability of upstream source failure propagating null values.
              </p>
            </div>
          </div>
        </div>

        {/* Explainable Evidence Breakdown (6 Categories) */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Explainable Evidence Breakdown</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-faint)' }}>Normalized Category Scores</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {evidenceWeights.map(ev => {
              const Icon = ev.icon;
              const pct = Math.round(ev.score * 100);
              return (
                <div key={ev.name}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Icon size={14} color="var(--accent-indigo)" />
                      <span style={{ fontWeight: 600 }}>{ev.name}</span>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-faint)' }}>(Weight: {ev.weight})</span>
                    </div>
                    <strong style={{ fontFamily: 'var(--font-mono)' }}>{pct}%</strong>
                  </div>
                  <div style={{ height: '6px', background: 'rgba(255, 255, 255, 0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${pct}%`,
                        height: '100%',
                        background: pct > 70 ? 'var(--accent-cyan)' : 'var(--accent-indigo)',
                        borderRadius: '3px',
                        transition: 'width 300ms ease'
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Concrete Supporting Evidence Items */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Concrete Audit Trail & Supporting Evidence</h3>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {rc.evidence_items.map((item, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 14px',
                background: 'rgba(255, 255, 255, 0.015)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.85rem'
              }}
            >
              <CheckCircle size={16} color="var(--accent-cyan)" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
