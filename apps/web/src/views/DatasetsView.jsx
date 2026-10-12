import React, { useState } from 'react';
import { Database, Search, FileText, BarChart2, Plus, ArrowRight } from 'lucide-react';

export default function DatasetsView({ datasets, onNavigate }) {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = datasets.filter(d =>
    d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.format.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Filter Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
        <div style={{ position: 'relative', width: '320px' }}>
          <Search size={16} color="var(--text-faint)" style={{ position: 'absolute', left: '12px', top: '10px' }} />
          <input
            id="input-dataset-search"
            type="text"
            placeholder="Search datasets, schemas, formats..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-main)',
              fontSize: '0.85rem'
            }}
          />
        </div>

        <button id="btn-ingest-dataset" className="btn btn-primary btn-sm">
          <Plus size={16} /> Register New Dataset
        </button>
      </div>

      {/* Datasets Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Dataset Name</th>
                <th>Storage Format</th>
                <th>Row Count</th>
                <th>Columns</th>
                <th>Null Rate</th>
                <th>Health Status</th>
                <th>Last Profiled</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(ds => (
                <tr key={ds.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <Database size={16} color="var(--accent-indigo)" />
                      <div>
                        <strong style={{ display: 'block', fontSize: '0.9rem' }}>{ds.name}</strong>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>{ds.id}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="badge badge-info">{ds.format.toUpperCase()}</span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{ds.row_count.toLocaleString()}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{ds.column_count} cols</td>
                  <td>
                    <span style={{ color: ds.null_rate > 0.02 ? 'var(--status-critical)' : 'var(--status-passed)' }}>
                      {(ds.null_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <span className={`badge badge-${ds.status === 'HEALTHY' ? 'passed' : 'warning'}`}>
                      {ds.status}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{ds.last_profiled}</td>
                  <td>
                    <button
                      id={`btn-profile-${ds.name}`}
                      className="btn btn-outline btn-sm"
                      onClick={() => onNavigate('profile', { datasetName: ds.name })}
                    >
                      <BarChart2 size={14} /> Profile <ArrowRight size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
