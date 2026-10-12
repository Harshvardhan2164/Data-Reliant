import React, { useState } from 'react';
import { Activity, Filter, Eye, AlertTriangle } from 'lucide-react';

const DETECTORS = ["all", "zscore", "robust_zscore", "iqr", "ewma", "cusum", "isolation_forest", "ks_test", "psi", "schema_drift"];

export default function AnomalyView({ anomalies, onNavigate }) {
  const [selectedDetector, setSelectedDetector] = useState("all");

  const filtered = selectedDetector === "all"
    ? anomalies
    : anomalies.filter(a => a.detector.toLowerCase() === selectedDetector.toLowerCase());

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
            Statistical & Temporal Anomaly Explorer
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Point detectors & distribution shift metrics evaluated across streaming micro-batches
          </p>
        </div>

        <button
          className="btn btn-outline btn-sm"
          onClick={() => onNavigate('incidents')}
        >
          Correlate into Incidents →
        </button>
      </div>

      {/* Detector Filter Chips */}
      <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
        {DETECTORS.map(d => (
          <button
            key={d}
            className={`btn btn-sm ${selectedDetector === d ? 'btn-primary' : 'btn-outline'}`}
            style={{ fontSize: '0.75rem', textTransform: 'uppercase' }}
            onClick={() => setSelectedDetector(d)}
          >
            {d}
          </button>
        ))}
      </div>

      {/* Anomalies Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Anomaly ID</th>
                <th>Detector</th>
                <th>Dataset</th>
                <th>Metric / Column</th>
                <th>Observed Value</th>
                <th>Expected / Baseline</th>
                <th>Anomaly Score</th>
                <th>Severity</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(a => (
                <tr key={a.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{a.id}</td>
                  <td>
                    <span className="badge badge-info">{a.detector}</span>
                  </td>
                  <td><strong>{a.dataset}</strong></td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{a.metric}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{a.observed}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{a.expected}</td>
                  <td>
                    <span style={{ fontWeight: 700, color: a.anomaly_score >= 4.0 ? 'var(--status-critical)' : 'var(--status-warning)' }}>
                      {a.anomaly_score}σ
                    </span>
                  </td>
                  <td>
                    <span className={`badge badge-${a.severity === 'HIGH' ? 'critical' : 'warning'}`}>
                      {a.severity}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{a.detected_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
