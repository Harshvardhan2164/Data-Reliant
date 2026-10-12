import React, { useState } from 'react';
import { ShieldCheck, Plus, Code, CheckCircle, Play, FileCode } from 'lucide-react';

const RULE_CATALOG = [
  { type: "not_null", name: "Not Null Constraint", desc: "Asserts non-null percentage strictly equals 100% or threshold" },
  { type: "uniqueness", name: "Uniqueness Rule", desc: "Verifies column values are strictly distinct without collision" },
  { type: "duplicate_rows", name: "Duplicate Rows", desc: "Verifies complete record uniqueness across all or key dimensions" },
  { type: "range", name: "Numeric Range Bound", desc: "Enforces continuous values lie strictly between [min, max]" },
  { type: "categorical_values", name: "Allowed Set Domain", desc: "Restricts discrete categorical elements to explicit allowed enum" },
  { type: "schema", name: "Schema Contract", desc: "Validates field presence, types, and schema drift compatibility" },
  { type: "freshness", name: "Temporal Freshness", desc: "Ensures latest timestamp is within expected SLA hours" },
  { type: "row_count", name: "Volume Threshold", desc: "Guarantees row count meets absolute or relative volume SLAs" },
  { type: "referential_integrity", name: "Foreign Key Integrity", desc: "Ensures child keys exist in parent upstream tables without orphans" },
  { type: "custom_expression", name: "Polars Custom Expression", desc: "Evaluates arbitrary Polars DSL expressions on datasets" }
];

export default function QualityRulesView({ rules, onNavigate }) {
  const [activeTab, setActiveTab] = useState("rules");
  const [yamlContent, setYamlContent] = useState(`name: transactions_enterprise_suite
dataset: transactions
rules:
  - type: not_null
    column: transaction_id
    severity: CRITICAL
  - type: not_null
    column: customer_id
    severity: HIGH
  - type: range
    column: amount
    min: 0.01
    max: 25000.0
    severity: HIGH
  - type: categorical_values
    column: channel
    allowed_values: [WEB, MOBILE_APP, PARTNER_API, IN_STORE]
  - type: freshness
    column: timestamp
    max_age_hours: 24
`);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
            Quality Rules & Test Suites
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            10-rule pluggable verification engine running natively on Polars
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className={`btn btn-sm ${activeTab === 'rules' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('rules')}
          >
            Active Rules ({rules.length})
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'catalog' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('catalog')}
          >
            Rule Catalog
          </button>
          <button
            className={`btn btn-sm ${activeTab === 'yaml' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setActiveTab('yaml')}
          >
            <FileCode size={14} /> YAML Suite Editor
          </button>
        </div>
      </div>

      {activeTab === 'rules' && (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Rule ID</th>
                  <th>Rule Type</th>
                  <th>Target Dataset</th>
                  <th>Target Column / Expr</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {rules.map(r => (
                  <tr key={r.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{r.id}</td>
                    <td>
                      <span className="badge badge-info">{r.type}</span>
                    </td>
                    <td><strong>{r.dataset}</strong></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                      {r.column || (r.params && r.params.expr) || 'Full Dataset'}
                    </td>
                    <td>
                      <span className={`badge badge-${r.severity === 'CRITICAL' ? 'critical' : 'warning'}`}>
                        {r.severity}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-passed">
                        <CheckCircle size={12} /> {r.status}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => onNavigate('quality_runs')}
                      >
                        <Play size={12} /> Run Test
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'catalog' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {RULE_CATALOG.map(cat => (
            <div key={cat.type} className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <ShieldCheck size={18} color="var(--accent-indigo)" />
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{cat.name}</h4>
              </div>
              <span className="badge badge-info" style={{ marginBottom: '10px' }}>{cat.type}</span>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{cat.desc}</p>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'yaml' && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">YAML Declarative Suite Definition</h3>
            <button className="btn btn-primary btn-sm">Save & Register Suite</button>
          </div>
          <textarea
            value={yamlContent}
            onChange={e => setYamlContent(e.target.value)}
            rows={14}
            style={{
              width: '100%',
              background: '#090e1a',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '16px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.85rem',
              color: 'var(--text-main)',
              lineHeight: 1.6
            }}
          />
        </div>
      )}
    </div>
  );
}
