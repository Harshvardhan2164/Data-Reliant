import React, { useState } from 'react';
import { BarChart2, Layers, Hash, AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react';

export default function ProfileView({ datasets, selectedDatasetName = "transactions", onNavigate }) {
  const [activeTab, setActiveTab] = useState("columns");
  const ds = datasets.find(d => d.name === selectedDatasetName) || datasets[0];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* Top Breadcrumb & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            id="btn-back-to-datasets"
            className="btn btn-outline btn-sm"
            onClick={() => onNavigate('datasets')}
          >
            <ArrowLeft size={14} /> Back
          </button>
          <div>
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
              Dataset Profile: <span style={{ color: 'var(--accent-cyan)' }}>{ds.name}</span>
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Profiled using Polars High-Performance Engine · {ds.row_count.toLocaleString()} rows · {ds.columns.length} columns
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn btn-sm ${activeTab === 'columns' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('columns')}
          >
            Column Statistics
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'schema' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('schema')}
          >
            Schema & Types
          </button>
        </div>
      </div>

      {/* Summary Stat Cards */}
      <div className="metric-grid">
        <div className="metric-card">
          <span className="metric-label">Total Rows</span>
          <span className="metric-value">{ds.row_count.toLocaleString()}</span>
          <span className="metric-footer">0 duplicates detected</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Total Columns</span>
          <span className="metric-value">{ds.column_count}</span>
          <span className="metric-footer">4 Categorical / 2 Numeric / 1 Temporal</span>
        </div>
        <div className="metric-card accent-rose">
          <span className="metric-label">Missing Values</span>
          <span className="metric-value" style={{ color: ds.null_rate > 0.02 ? 'var(--status-critical)' : 'var(--text-main)' }}>
            {(ds.null_rate * 100).toFixed(2)}%
          </span>
          <span className="metric-footer">Primary null spike on 'amount'</span>
        </div>
        <div className="metric-card accent-cyan">
          <span className="metric-label">Memory Footprint</span>
          <span className="metric-value">{ds.size_mb} MB</span>
          <span className="metric-footer">Optimized Parquet compression</span>
        </div>
      </div>

      {/* Tab 1: Column Statistics */}
      {activeTab === 'columns' && (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Column Name</th>
                  <th>Data Type</th>
                  <th>Null Count</th>
                  <th>Null Ratio</th>
                  <th>Distinct Values</th>
                  <th>Range / Quantiles (Min / Mean / Max)</th>
                </tr>
              </thead>
              <tbody>
                {ds.columns.map(col => {
                  const nullRatio = ((col.null_count / ds.row_count) * 100).toFixed(2);
                  return (
                    <tr key={col.name}>
                      <td>
                        <strong>{col.name}</strong>
                        {col.is_key && <span className="badge badge-info" style={{ marginLeft: '8px', fontSize: '0.65rem' }}>PRIMARY KEY</span>}
                      </td>
                      <td>
                        <span className="badge badge-info" style={{ fontFamily: 'var(--font-mono)' }}>
                          {col.type}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{col.null_count.toLocaleString()}</td>
                      <td>
                        <span style={{ color: col.null_count > 0 ? 'var(--status-critical)' : 'var(--text-muted)' }}>
                          {nullRatio}%
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{col.distinct ? col.distinct.toLocaleString() : 'N/A'}</td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {col.min !== undefined ? (
                          <span>
                            [{col.min} → <strong style={{ color: 'var(--text-main)' }}>{col.mean ?? '-'}</strong> → {col.max}]
                          </span>
                        ) : (
                          <span>Categorical / Non-numeric domain</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Schema & Types */}
      {activeTab === 'schema' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Polars Strict Schema Definition</h3>
          </div>
          <pre style={{
            background: 'rgba(0, 0, 0, 0.4)',
            padding: '16px',
            borderRadius: 'var(--radius-sm)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.85rem',
            color: 'var(--accent-cyan)',
            overflowX: 'auto'
          }}>
{JSON.stringify(ds.columns.reduce((acc, c) => ({ ...acc, [c.name]: c.type }), {}), null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
