import React from 'react';
import { useApp } from '../context/AppContext';
import { 
  LayoutDashboard, 
  CheckSquare, 
  Calendar, 
  Flame, 
  MessageSquare, 
  Timer, 
  Activity,
  Mail,
  BarChart2,
  X,
  Loader
} from 'lucide-react';


const Sidebar = ({ onCloseMenu }) => {
  const { activeTab, setActiveTab, apiHealth, timerIsRunning, timerMinutes, timerSeconds, focusTask, demoScenario, seedDemoData, isLoading } = useApp();

  const handleSeedClick = (scenario) => {
    if (isLoading) return;
    if (window.confirm("WARNING: Loading a presentation scenario will erase your current active task database. Are you sure you want to proceed?")) {
      seedDemoData(scenario);
      onCloseMenu?.();
    }
  };

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'tasks', label: 'Task Center', icon: CheckSquare },
    { id: 'calendar', label: 'Schedule Matrix', icon: Calendar },
    { id: 'habits', label: 'Habits & Streaks', icon: Flame },
    { id: 'negotiation', label: 'Negotiation Hub', icon: Mail },
    { id: 'analytics', label: 'Analytics & Health', icon: BarChart2 },
    { id: 'chat', label: 'Command Center', icon: MessageSquare },
  ];

  return (
    <aside className="sidebar glass-card">
      <div className="sidebar-brand" style={{ position: 'relative' }}>
        <span className="brand-logo">🚨</span>
        <div className="brand-text">
          <h2>Life Saver</h2>
          <span className="brand-sub">AI Companion</span>
        </div>
        <button 
          className="mobile-close-btn" 
          onClick={onCloseMenu}
          aria-label="Close menu"
          style={{
            position: 'absolute',
            right: '0',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '4px',
            display: 'none' /* Will be toggled by media queries in App.css */
          }}
        >
          <X size={20} />
        </button>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => {
                setActiveTab(item.id);
                onCloseMenu?.();
              }}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={20} className="nav-icon" />
              <span>{item.label}</span>
              {item.id === 'chat' && (
                <span className="ai-badge">AI</span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {timerIsRunning && (
          <div className="sidebar-timer-preview">
            <Timer size={16} className="timer-icon animate-spin" />
            <div className="timer-preview-details">
              <p className="timer-preview-title">{focusTask?.title || "Focusing..."}</p>
              <p className="timer-preview-time">
                {String(timerMinutes).padStart(2, '0')}:{String(timerSeconds).padStart(2, '0')}
              </p>
            </div>
          </div>
        )}

        <div className="sidebar-scenarios" style={{ position: 'relative' }}>
          {isLoading && (
            <div className="scenario-loading-overlay" style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(15, 23, 42, 0.7)',
              backdropFilter: 'blur(3px)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '8px',
              zIndex: 10,
              gap: '8px'
            }}>
              <Loader className="animate-spin text-cyan" size={24} style={{ color: 'var(--color-cyan)', animation: 'spin 2s linear infinite' }} />
              <span style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-primary)' }}>Seeding Scenario...</span>
            </div>
          )}
          <h4 className="scenarios-title">🎯 Presentation Scenario</h4>
          <div className="scenario-cards-container">
            <button 
              onClick={() => handleSeedClick('student')}
              className={`scenario-card ${demoScenario === 'student' ? 'active' : ''}`}
            >
              <div className="scenario-card-header">
                <span className="scenario-emoji">🎓</span>
                <span className="scenario-label">Student</span>
              </div>
              <p className="scenario-desc">Academic Deadline</p>
              <div className="scenario-risk-transition">
                <span className="risk-initial">Risk: 18%</span>
                <span className="risk-arrow">→</span>
                <span className="risk-improved">61%</span>
              </div>
            </button>

            <button 
              onClick={() => handleSeedClick('professional')}
              className={`scenario-card ${demoScenario === 'professional' ? 'active' : ''}`}
            >
              <div className="scenario-card-header">
                <span className="scenario-emoji">💼</span>
                <span className="scenario-label">Professional</span>
              </div>
              <p className="scenario-desc">Production Incident</p>
              <div className="scenario-risk-transition">
                <span className="risk-initial">Risk: 22%</span>
                <span className="risk-arrow">→</span>
                <span className="risk-improved">65%</span>
              </div>
            </button>

            <button 
              onClick={() => handleSeedClick('startup')}
              className={`scenario-card ${demoScenario === 'startup' ? 'active' : ''}`}
            >
              <div className="scenario-card-header">
                <span className="scenario-emoji">🚀</span>
                <span className="scenario-label">Founder</span>
              </div>
              <p className="scenario-desc">Investor Pitch</p>
              <div className="scenario-risk-transition">
                <span className="risk-initial">Risk: 12%</span>
                <span className="risk-arrow">→</span>
                <span className="risk-improved">58%</span>
              </div>
            </button>
          </div>
        </div>

        <div className="connection-status">
          <Activity size={14} className={apiHealth ? "text-green" : "text-yellow"} />
          <span>{apiHealth ? "Core Online" : "Local Mode"}</span>
          <span className={`status-dot ${apiHealth ? "online" : "fallback"}`}></span>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
