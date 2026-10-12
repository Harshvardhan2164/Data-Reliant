import React, { useState } from 'react';
import { ShieldAlert, ArrowDown, ArrowUp, AlertCircle, Layers } from 'lucide-react';
import { LINEAGE_GRAPH_DATA } from '../data/mockData';

export default function BlastRadiusView({ selectedNodeId = "transactions" }) {
  const [nodeId, setNodeId] = useState(selectedNodeId);

  const { nodes, edges } = LINEAGE_GRAPH_DATA;

  // Compute blast radius
  const getDownstream = (startId) => {
    let visited = new Set();
    let queue = [startId];
    while (queue.length > 0) {
      let curr = queue.shift();
      edges.filter(e => e.source === curr).forEach(e => {
        if (!visited.has(e.target)) {
          visited.add(e.target);
          queue.push(e.target);
        }
      });
    }
    return Array.from(visited);
  };

  const getUpstream = (startId) => {
    let visited = new Set();
    let queue = [startId];
    while (queue.length > 0) {
      let curr = queue.shift();
      edges.filter(e => e.target === curr).forEach(e => {
        if (!visited.has(e.source)) {
          visited.add(e.source);
          queue.push(e.source);
        }
      });
    }
    return Array.from(visited);
  };

  const downstream = getDownstream(nodeId);
  const upstream = getUpstream(nodeId);
  const blastRatio = Math.round((downstream.length / (nodes.length - 1)) * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
            Blast Radius & Failure Impact Analyzer
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Simulate upstream outage propagation and quantify downstream impact percentage
          </p>
        </div>

        {/* Node Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Target Node:</span>
          <select
            value={nodeId}
            onChange={e => setNodeId(e.target.value)}
            style={{
              background: '#090e1a',
              color: 'var(--text-main)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 12px',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.85rem'
            }}
          >
            {nodes.map(n => (
              <option key={n.id} value={n.id}>{n.id} ({n.type})</option>
            ))}
          </select>
        </div>
      </div>

      {/* Blast Score Banner */}
      <div className="card" style={{
        background: 'linear-gradient(135deg, rgba(244, 63, 94, 0.12), rgba(15, 23, 42, 0.8))',
        borderColor: 'rgba(244, 63, 94, 0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '24px 28px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
          <div style={{
            width: '54px',
            height: '54px',
            borderRadius: '12px',
            background: 'rgba(244, 63, 94, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <ShieldAlert size={28} color="var(--status-critical)" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '4px' }}>
              Simulated Outage on: <span style={{ color: 'var(--accent-cyan)' }}>{nodeId}</span>
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              A failure at this stage cascades to <strong>{downstream.length}</strong> downstream consumer pipelines.
            </p>
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-faint)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Pipeline Blast Radius
          </span>
          <div style={{
            fontSize: '2.5rem',
            fontWeight: 800,
            fontFamily: 'var(--font-heading)',
            color: blastRatio > 40 ? 'var(--status-critical)' : 'var(--status-warning)'
          }}>
            {blastRatio}%
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Upstream Ancestors */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <ArrowUp size={16} color="var(--accent-indigo)" />
              Upstream Root Dependencies ({upstream.length})
            </h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {upstream.length === 0 ? (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-faint)' }}>Node is an independent root source.</p>
            ) : (
              upstream.map(u => (
                <div key={u} style={{
                  padding: '10px 14px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '0.85rem'
                }}>
                  <strong>{u}</strong>
                  <span className="badge badge-info">UPSTREAM</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Downstream Consumers */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <ArrowDown size={16} color="var(--status-critical)" />
              Downstream Impacted Assets ({downstream.length})
            </h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {downstream.length === 0 ? (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-faint)' }}>Node is an end sink (e.g. Dashboard).</p>
            ) : (
              downstream.map(d => (
                <div key={d} style={{
                  padding: '10px 14px',
                  background: 'rgba(244, 63, 94, 0.04)',
                  border: '1px solid rgba(244, 63, 94, 0.2)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: '0.85rem'
                }}>
                  <strong style={{ color: 'var(--status-critical)' }}>{d}</strong>
                  <span className="badge badge-critical">IMPACTED</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
