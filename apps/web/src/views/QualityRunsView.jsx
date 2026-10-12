import React from 'react';
import { CheckCircle, XCircle, Clock, Play, ArrowRight } from 'lucide-react';

export default function QualityRunsView({ onNavigate }) {
  const RUNS = [
    {
      id: "RUN-10492",
      suite: "transactions_enterprise_suite",
      dataset: "transactions",
      total_rules: 10,
      passed: 9,
      failed: 1,
      duration_ms: 24.5,
      timestamp: "2026-10-10 15:10:00 UTC",
      status: "FAILED",
      violations: [
        { rule: "not_null", column: "amount", observed: "1,120 nulls (0.45%)", threshold: "0.0%", severity: "HIGH" }
      ]
    },
    {
      id: "RUN-10491",
      suite: "customers_core_suite",
      dataset: "customers",
      total_rules: 6,
      passed: 6,
      failed: 0,
      duration_ms: 12.1,
      timestamp: "2026-10-10 14:20:00 UTC",
      status: "PASSED",
      violations: []
    },
    {
      id: "RUN-10490",
      suite: "payments_pipeline_suite",
      dataset: "payments",
      total_rules: 5,
      passed: 5,
      failed: 0,
      duration_ms: 18.2,
      timestamp: "2026-10-10 14:15:00 UTC",
      status: "PASSED",
      violations: []
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
            Quality Suite Execution Runs
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Historical assertion validation and violated records breakdown
          </p>
        </div>

        <button className="btn btn-primary btn-sm">
          <Play size={14} /> Execute All Suites Now
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {RUNS.map(run => (
          <div key={run.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className={`badge badge-${run.status === 'PASSED' ? 'passed' : 'critical'}`}>
                  {run.status === 'PASSED' ? <CheckCircle size={12} /> : <XCircle size={12} />} {run.status}
                </span>
                <strong style={{ fontSize: '1rem' }}>{run.suite}</strong>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>{run.id}</span>
              </div>
              <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span>Target: <strong>{run.dataset}</strong></span>
                <span>Latency: <strong>{run.duration_ms} ms</strong></span>
                <span>{run.timestamp}</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '24px', fontSize: '0.85rem', marginBottom: run.violations.length ? '14px' : '0' }}>
              <span>Total Assertions: <strong>{run.total_rules}</strong></span>
              <span style={{ color: 'var(--status-passed)' }}>Passed: <strong>{run.passed}</strong></span>
              <span style={{ color: run.failed > 0 ? 'var(--status-critical)' : 'var(--text-muted)' }}>Failed: <strong>{run.failed}</strong></span>
            </div>

            {run.violations.length > 0 && (
              <div style={{ background: 'rgba(244, 63, 94, 0.05)', border: '1px solid rgba(244, 63, 94, 0.2)', borderRadius: 'var(--radius-sm)', padding: '12px' }}>
                <h4 style={{ fontSize: '0.8rem', color: 'var(--status-critical)', fontWeight: 600, marginBottom: '6px' }}>
                  Violated Assertions:
                </h4>
                {run.violations.map((v, i) => (
                  <div key={i} style={{ fontSize: '0.8rem', display: 'flex', gap: '16px' }}>
                    <span>Rule: <strong>{v.rule}</strong></span>
                    <span>Column: <strong>{v.column}</strong></span>
                    <span>Observed: <strong>{v.observed}</strong></span>
                    <span>Threshold: <strong>{v.threshold}</strong></span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
