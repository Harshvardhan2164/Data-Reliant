import React, { useState } from 'react';
import { GitFork, Layers, Database, Layout, ShieldAlert, CheckCircle, Info } from 'lucide-react';
import { LINEAGE_GRAPH_DATA } from '../data/mockData';

export default function LineageView({ onNavigate }) {
  const [selectedNode, setSelectedNode] = useState("transactions");
  const { nodes, edges } = LINEAGE_GRAPH_DATA;

  const currentNode = nodes.find(n => n.id === selectedNode) || nodes[2];

  // Upstream / Downstream calculation
  const upstreamNodes = edges.filter(e => e.target === selectedNode).map(e => e.source);
  const downstreamNodes = edges.filter(e => e.source === selectedNode).map(e => e.target);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 700 }}>
            Enterprise Pipeline Lineage DAG
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Directed Acyclic Graph (NetworkX engine) with ancestor traversal and blast radius propagation
          </p>
        </div>

        <button
          className="btn btn-outline btn-sm"
          onClick={() => onNavigate('blast_radius', { nodeId: selectedNode })}
        >
          <ShieldAlert size={14} color="var(--status-critical)" /> Analyze Blast Radius
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: '20px' }}>
        {/* Interactive SVG DAG Canvas */}
        <div className="dag-canvas">
          <svg width="100%" height="100%" viewBox="0 0 1150 500">
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="28"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="rgba(255, 255, 255, 0.4)" />
              </marker>
              <marker
                id="arrowhead-active"
                markerWidth="10"
                markerHeight="7"
                refX="28"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#06b6d4" />
              </marker>
            </defs>

            {/* Edges */}
            {edges.map((edge, idx) => {
              const src = nodes.find(n => n.id === edge.source);
              const tgt = nodes.find(n => n.id === edge.target);
              if (!src || !tgt) return null;
              const isHighlighted = edge.source === selectedNode || edge.target === selectedNode;

              return (
                <path
                  key={idx}
                  d={`M ${src.x} ${src.y} C ${(src.x + tgt.x) / 2} ${src.y}, ${(src.x + tgt.x) / 2} ${tgt.y}, ${tgt.x} ${tgt.y}`}
                  fill="none"
                  className={`dag-edge ${isHighlighted ? 'highlighted' : ''}`}
                  markerEnd={isHighlighted ? "url(#arrowhead-active)" : "url(#arrowhead)"}
                />
              );
            })}

            {/* Nodes */}
            {nodes.map(node => {
              const isSelected = node.id === selectedNode;
              const isUpstream = upstreamNodes.includes(node.id);
              const isDownstream = downstreamNodes.includes(node.id);

              let strokeColor = "rgba(255, 255, 255, 0.15)";
              if (isSelected) strokeColor = "#06b6d4";
              else if (isUpstream) strokeColor = "#6366f1";
              else if (isDownstream) strokeColor = "#f43f5e";

              return (
                <g
                  key={node.id}
                  className="dag-node"
                  transform={`translate(${node.x - 90}, ${node.y - 45})`}
                  onClick={() => setSelectedNode(node.id)}
                >
                  <rect
                    width="180"
                    height="90"
                    rx="12"
                    fill={isSelected ? "rgba(6, 182, 212, 0.15)" : "rgba(15, 23, 42, 0.9)"}
                    stroke={strokeColor}
                    strokeWidth={isSelected ? "2.5" : "1.5"}
                  />
                  <circle
                    cx="24"
                    cy="28"
                    r="6"
                    fill={node.status === "CRITICAL" ? "var(--status-critical)" : node.status === "WARNING" ? "var(--status-warning)" : "var(--status-passed)"}
                  />
                  <text
                    x="40"
                    y="32"
                    fill="#f8fafc"
                    fontSize="13"
                    fontWeight="600"
                    fontFamily="Inter, sans-serif"
                  >
                    {node.id}
                  </text>
                  <text
                    x="20"
                    y="56"
                    fill="#94a3b8"
                    fontSize="11"
                    fontFamily="Inter, sans-serif"
                  >
                    Type: {node.type.toUpperCase()}
                  </text>
                  <text
                    x="20"
                    y="74"
                    fill="#64748b"
                    fontSize="10"
                    fontFamily="JetBrains Mono, monospace"
                  >
                    Rows: {node.rows}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Node Inspector Sidebar */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card-header" style={{ marginBottom: 0 }}>
            <h3 className="card-title">
              <Layers size={16} color="var(--accent-cyan)" />
              Node Inspector
            </h3>
            <span className={`badge badge-${currentNode.status === 'CRITICAL' ? 'critical' : currentNode.status === 'WARNING' ? 'warning' : 'passed'}`}>
              {currentNode.status}
            </span>
          </div>

          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '2px' }}>{currentNode.name}</h4>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>ID: {currentNode.id}</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Lineage Category</span>
              <strong style={{ textTransform: 'capitalize' }}>{currentNode.type}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Estimated Rows</span>
              <strong>{currentNode.rows}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Direct Upstream</span>
              <strong style={{ color: 'var(--accent-indigo)' }}>{upstreamNodes.length ? upstreamNodes.join(', ') : 'None (Source)'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
              <span style={{ color: 'var(--text-muted)' }}>Direct Downstream</span>
              <strong style={{ color: 'var(--status-critical)' }}>{downstreamNodes.length ? downstreamNodes.join(', ') : 'None (Sink)'}</strong>
            </div>
          </div>

          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              className="btn btn-primary btn-sm"
              style={{ width: '100%' }}
              onClick={() => onNavigate('blast_radius', { nodeId: currentNode.id })}
            >
              Simulate Failure Impact
            </button>
            <button
              className="btn btn-outline btn-sm"
              style={{ width: '100%' }}
              onClick={() => onNavigate('profile', { datasetName: currentNode.id })}
            >
              View Dataset Profile
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
