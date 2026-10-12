import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Database,
  BarChart2,
  ShieldCheck,
  CheckCircle,
  Activity,
  GitFork,
  AlertTriangle,
  Cpu,
  ShieldAlert,
  FlaskConical,
  RefreshCw,
  Sliders
} from 'lucide-react';

import OverviewView from './views/OverviewView';
import DatasetsView from './views/DatasetsView';
import ProfileView from './views/ProfileView';
import QualityRulesView from './views/QualityRulesView';
import QualityRunsView from './views/QualityRunsView';
import AnomalyView from './views/AnomalyView';
import LineageView from './views/LineageView';
import IncidentsView from './views/IncidentsView';
import RootCauseView from './views/RootCauseView';
import BlastRadiusView from './views/BlastRadiusView';
import EvaluationView from './views/EvaluationView';

import {
  INITIAL_DATASETS,
  INITIAL_QUALITY_RULES,
  INITIAL_ANOMALIES,
  INITIAL_INCIDENTS
} from './data/mockData';

export default function App() {
  const [currentView, setCurrentView] = useState('overview');
  const [viewParams, setViewParams] = useState({});
  const [datasets, setDatasets] = useState(INITIAL_DATASETS);
  const [rules, setRules] = useState(INITIAL_QUALITY_RULES);
  const [anomalies, setAnomalies] = useState(INITIAL_ANOMALIES);
  const [incidents, setIncidents] = useState(INITIAL_INCIDENTS);
  const [apiOnline, setApiOnline] = useState(false);

  // Check backend health
  useEffect(() => {
    fetch('/api/v1/health')
      .then(r => r.json())
      .then(d => {
        if (d.status === 'ok' || d.status === 'healthy' || d.healthy) setApiOnline(true);
      })
      .catch(() => setApiOnline(false));
  }, []);

  const navigate = (view, params = {}) => {
    setCurrentView(view);
    setViewParams(params);
  };

  const navSections = [
    {
      title: "Core Platform",
      items: [
        { id: "overview", label: "Mission Control", icon: LayoutDashboard },
        { id: "datasets", label: "Datasets", icon: Database },
        { id: "profile", label: "Data Profiling", icon: BarChart2 },
      ]
    },
    {
      title: "Data Quality & Anomaly",
      items: [
        { id: "rules", label: "Quality Rules", icon: ShieldCheck },
        { id: "quality_runs", label: "Quality Runs", icon: CheckCircle },
        { id: "anomalies", label: "Anomaly Explorer", icon: Activity },
      ]
    },
    {
      title: "Lineage & Blast Radius",
      items: [
        { id: "lineage", label: "Pipeline Lineage", icon: GitFork },
        { id: "blast_radius", label: "Blast Radius Impact", icon: ShieldAlert },
      ]
    },
    {
      title: "Root-Cause Intelligence",
      items: [
        { id: "incidents", label: "Incidents & Alerts", icon: AlertTriangle, badge: "2 Active" },
        { id: "rootcause", label: "Root-Cause Analysis", icon: Cpu },
      ]
    },
    {
      title: "Research & Benchmarks",
      items: [
        { id: "evaluation", label: "Benchmark Lab (13)", icon: FlaskConical },
      ]
    }
  ];

  const getPageTitle = () => {
    switch (currentView) {
      case 'overview': return { title: "Mission Control", desc: "Autonomous data quality & incident operations" };
      case 'datasets': return { title: "Datasets Explorer", desc: "Registered tabular assets & storage adapters" };
      case 'profile': return { title: "Profiling & Schema Report", desc: "Statistical distributions and null rate analysis" };
      case 'rules': return { title: "Quality Rules & Suites", desc: "10-rule verification engine catalog" };
      case 'quality_runs': return { title: "Quality Assertion Runs", desc: "Execution history and violated constraint logs" };
      case 'anomalies': return { title: "Multi-Signal Anomaly Explorer", desc: "Statistical, temporal, and drift detection" };
      case 'lineage': return { title: "Pipeline Lineage DAG", desc: "Dependency graph and ancestor/descendant traversal" };
      case 'blast_radius': return { title: "Blast Radius Impact", desc: "Failure simulation and downstream vulnerability analysis" };
      case 'incidents': return { title: "Correlated Incidents", desc: "Topology-aware incident clustering & alert compression" };
      case 'rootcause': return { title: "Root-Cause Intelligence", desc: "6-category explainable evidence weighting & ranking" };
      case 'evaluation': return { title: "Research Benchmark Lab", desc: "Evaluation of 13 failure scenarios vs ground truth" };
      default: return { title: "DataReliant Platform", desc: "Autonomous data reliability" };
    }
  };

  const headerInfo = getPageTitle();

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-shield">
            <span style={{ fontSize: '18px' }}>🛡️</span>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="logo-text">DataReliant</span>
              <span className="version-pill">v1.0</span>
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-faint)' }}>Root-Cause Intelligence</span>
          </div>
        </div>

        <nav className="nav-menu">
          {navSections.map(sec => (
            <div key={sec.title}>
              <div className="nav-section-title">{sec.title}</div>
              {sec.items.map(item => {
                const Icon = item.icon;
                const isActive = currentView === item.id;
                return (
                  <div
                    key={item.id}
                    id={`nav-${item.id}`}
                    className={`nav-item ${isActive ? 'active' : ''}`}
                    onClick={() => navigate(item.id)}
                  >
                    <Icon size={16} />
                    <span>{item.label}</span>
                    {item.badge && (
                      <span className="nav-badge danger">{item.badge}</span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="api-status-indicator">
            <div className="status-dot" style={{ background: apiOnline ? 'var(--status-passed)' : 'var(--accent-cyan)' }} />
            <span>FastAPI: {apiOnline ? 'Live Connected' : 'Local Engine Ready'}</span>
          </div>
        </div>
      </aside>

      {/* Main View Area */}
      <div className="main-wrapper">
        <header className="top-bar">
          <div className="page-title-group">
            <h1>{headerInfo.title}</h1>
            <p>{headerInfo.desc}</p>
          </div>

          <div className="top-actions">
            <button
              className="btn btn-outline btn-sm"
              onClick={() => navigate('evaluation')}
            >
              <FlaskConical size={14} /> Run Benchmarks
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => navigate('incidents')}
            >
              <AlertTriangle size={14} /> 2 Incidents
            </button>
          </div>
        </header>

        <main className="content-viewport">
          {currentView === 'overview' && (
            <OverviewView
              datasets={datasets}
              incidents={incidents}
              anomalies={anomalies}
              onNavigate={navigate}
            />
          )}

          {currentView === 'datasets' && (
            <DatasetsView
              datasets={datasets}
              onNavigate={navigate}
            />
          )}

          {currentView === 'profile' && (
            <ProfileView
              datasets={datasets}
              selectedDatasetName={viewParams.datasetName || "transactions"}
              onNavigate={navigate}
            />
          )}

          {currentView === 'rules' && (
            <QualityRulesView
              rules={rules}
              onNavigate={navigate}
            />
          )}

          {currentView === 'quality_runs' && (
            <QualityRunsView
              onNavigate={navigate}
            />
          )}

          {currentView === 'anomalies' && (
            <AnomalyView
              anomalies={anomalies}
              onNavigate={navigate}
            />
          )}

          {currentView === 'lineage' && (
            <LineageView
              onNavigate={navigate}
            />
          )}

          {currentView === 'blast_radius' && (
            <BlastRadiusView
              selectedNodeId={viewParams.nodeId || "transactions"}
            />
          )}

          {currentView === 'incidents' && (
            <IncidentsView
              incidents={incidents}
              onNavigate={navigate}
            />
          )}

          {currentView === 'rootcause' && (
            <RootCauseView
              incidents={incidents}
              selectedIncidentId={viewParams.incidentId || "INC-2026-081"}
              onNavigate={navigate}
            />
          )}

          {currentView === 'evaluation' && (
            <EvaluationView />
          )}
        </main>
      </div>
    </div>
  );
}
