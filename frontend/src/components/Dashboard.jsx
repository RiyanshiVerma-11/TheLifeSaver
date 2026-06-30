import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { 
  AlertTriangle, 
  Sparkles, 
  Flame, 
  CheckCircle, 
  Play, 
  TrendingUp,
  X,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Cpu,
  Mail,
  Calendar,
  AlertCircle
} from 'lucide-react';

const Dashboard = () => {
  const { 
    tasks, 
    habits, 
    recommendations, 
    dismissRecommendation, 
    rescueTask,
    setFocusTask,
    setTimerMinutes,
    setTimerSeconds,
    setTimerIsRunning,
    setActiveTab,
    agentActivities,
    syncGoogleCalendar,
    connectGoogleAccount,
    userSettings,
    healthStats,
    toggleSubtask,
    notifications,
    readNotification,
    demoScenario,
    seedDemoData
  } = useApp();

  const [expandedReasoningTaskId, setExpandedReasoningTaskId] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState('All');
 
  // Filter tasks
  const pendingTasks = tasks.filter(t => t.status !== 'Completed');
  const completedTasks = tasks.filter(t => t.status === 'Completed');
  
  const demoTask = tasks.find(t => 
    t.title.includes("Operating Systems") || 
    t.title.includes("Bug Fix") || 
    t.title.includes("Investor Pitch") || 
    t.title.includes("Pitch Deck")
  );
  const isRescued = demoTask && (!!demoTask.rescue_strategy || demoTask.subtasks.length > 0);
  
  // Apply Category Filter to pending tasks
  const filteredPendingTasks = selectedCategory === 'All' 
    ? pendingTasks 
    : pendingTasks.filter(t => (t.category || '').toLowerCase() === selectedCategory.toLowerCase());

  // Sort pending by panic index
  const highPanicTasks = [...filteredPendingTasks]
    .sort((a, b) => b.panic_index - a.panic_index);

  // Focus on the highest panic task for the "Emergency Rescue Mode" widget
  const rescueTaskCandidate = [...pendingTasks]
    .sort((a, b) => b.panic_index - a.panic_index)
    .find(t => t.rescue_strategy);

  // Compute stats
  const totalStreak = habits.reduce((acc, h) => acc + h.streak, 0);
  const overdueCount = tasks.filter(t => t.status === 'Overdue').length;

  const startPomodoro = (task) => {
    setFocusTask(task);
    setTimerMinutes(25);
    setTimerSeconds(0);
    setTimerIsRunning(true);
    setActiveTab('tasks');
  };

  const getRelativeTime = (isoString) => {
    const diff = new Date(isoString) - new Date();
    const hours = Math.round(diff / (1000 * 60 * 60));
    if (hours < 0) return `${Math.abs(hours)}h overdue`;
    if (hours === 0) return "Due now";
    if (hours < 24) return `${hours}h remaining`;
    return `${Math.round(hours / 24)} days left`;
  };

  const toggleReasoning = (taskId) => {
    setExpandedReasoningTaskId(expandedReasoningTaskId === taskId ? null : taskId);
  };

  // Convert JSON timeline
  const parseRescueTimeline = (timelineStr) => {
    try {
      return JSON.parse(timelineStr || '[]');
    } catch {
      return [];
    }
  };

  return (
    <div className="dashboard-container">
      {/* Google API Integration Status Bar */}
      <div className="integration-status-bar glass-card">
        <div className="status-info">
          <span className={`status-pulse-dot ${demoScenario ? 'active-purple' : 'active'}`}></span>
          <span>
            {demoScenario ? (
              <strong className="presentation-scenario-badge">
                {demoScenario === 'student' && '🎓 PRESENTATION SCENARIO • Student Mode'}
                {demoScenario === 'professional' && '💼 PRESENTATION SCENARIO • Professional Mode'}
                {demoScenario === 'startup' && '🚀 PRESENTATION SCENARIO • Startup Founder Mode'}
              </strong>
            ) : (
              userSettings.google_account_connected 
                ? "⚡ Connected to Google APIs (Calendar & Gmail Active)" 
                : "🔒 Standalone Mode (Offline Sandboxed Calculations - Zero Cost)"
            )}
          </span>
          {demoScenario && (
            <span className="demo-timer-badge">⏱ Estimated Demo Time: 2 min</span>
          )}
        </div>
        {!userSettings.google_account_connected && !demoScenario && (
          <button 
            onClick={connectGoogleAccount} 
            className="btn btn-accent btn-xs glow-pulse-hover"
            style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem' }}
          >
            Connect Google Account
          </button>
        )}
      </div>

      {/* Header section */}
      <header className="dashboard-header">
        <div>
          <h1>Autonomous Rescue Center</h1>
          <p className="subtitle">Agentic Multi-LLM coordination active. Monitoring deadlines in real-time.</p>
        </div>
        
        {overdueCount > 0 && (
          <div className="alert-banner glass-card pulse-red">
            <AlertTriangle color="#ff3b30" size={20} />
            <div>
              <p className="alert-title">{overdueCount} Critical Overdue Warnings!</p>
              <p className="alert-desc">Deadlines exceeded. Auto-negotiation and timeline adjustments triggered.</p>
            </div>
          </div>
        )}
      </header>

      {demoScenario && (
        <div className="presentation-guide-panel glass-card border-purple animate-slide-in-top">
          <div className="presentation-guide-left">
            <div className="guide-header">
              <span className="live-demo-pill">🎤 PRESENTATION STEPS</span>
              <h3>Interactive Walkthrough Guide</h3>
            </div>
            
            <div className="guide-stepper">
              <div className="stepper-step completed">
                <div className="step-num">①</div>
                <div className="step-content">
                  <span className="step-title">AI Detects Failure</span>
                  <span className="step-desc">Workspace scanned; low-probability threat spotted.</span>
                </div>
              </div>
              <div className="step-connector completed"></div>

              <div className={`stepper-step ${isRescued ? 'completed' : 'active'}`}>
                <div className="step-num">{isRescued ? '✓' : '②'}</div>
                <div className="step-content">
                  <span className="step-title">Rescue Strategy Generated</span>
                  <span className="step-desc">
                    {isRescued 
                      ? "Scope pruned & critical next action mapped." 
                      : "Action Required: Click \"AI Rescue Plan\" on the urgent task card below."}
                  </span>
                </div>
              </div>
              <div className={`step-connector ${isRescued ? 'completed' : ''}`}></div>

              <div className={`stepper-step ${isRescued ? 'completed' : 'pending'}`}>
                <div className="step-num">{isRescued ? '✓' : '③'}</div>
                <div className="step-content">
                  <span className="step-title">Schedule Replanned</span>
                  <span className="step-desc">Focus Pomodoro slots blocked. Client calendar conflict resolved.</span>
                </div>
              </div>
              <div className={`step-connector ${isRescued ? 'completed' : ''}`}></div>

              <div className={`stepper-step ${isRescued ? 'completed' : 'pending'}`}>
                <div className="step-num">{isRescued ? '✓' : '④'}</div>
                <div className="step-content">
                  <span className="step-title">Negotiation Drafted</span>
                  <span className="step-desc">Professional extension email generated in the Negotiation Hub.</span>
                </div>
              </div>
              <div className={`step-connector ${isRescued ? 'completed' : ''}`}></div>

              <div className={`stepper-step ${isRescued ? 'completed' : 'pending'}`}>
                <div className="step-num">{isRescued ? '✓' : '⑤'}</div>
                <div className="step-content">
                  <span className="step-title">Reflection Stored</span>
                  <span className="step-desc">Habits logged; procrastination pattern registered in AI Memory.</span>
                </div>
              </div>
            </div>
          </div>

          <div className="presentation-guide-right">
            <div className={`mission-status-card ${isRescued ? 'status-rescued' : 'status-jeopardy'}`}>
              <div className="mission-card-header">
                <span className="mission-label">MISSION STATUS:</span>
                <strong className="mission-value">{isRescued ? '🛡️ RESCUED & OPTIMIZED' : '⚠️ IN JEOPARDY'}</strong>
              </div>
              <div className="mission-details">
                <div className="mission-metric">
                  <span className="metric-lbl">Active Task:</span>
                  <strong className="metric-val">{demoTask ? demoTask.title : 'None'}</strong>
                </div>
                <div className="mission-metric">
                  <span className="metric-lbl">Deadline Risk:</span>
                  <strong className="metric-val text-red">{isRescued ? 'MINIMIZED (COPEABLE)' : 'CRITICAL OVERLOAD'}</strong>
                </div>
                <div className="mission-metric">
                  <span className="metric-lbl">Success Probability:</span>
                  <strong className={`metric-val ${isRescued ? 'text-green' : 'text-orange'}`}>
                    {demoTask ? Math.round(demoTask.completion_probability * 100) : 0}%
                  </strong>
                </div>
                <div className="mission-metric">
                  <span className="metric-lbl">Rescue Status:</span>
                  <strong className="metric-val">{isRescued ? 'Active Execution' : 'Pending Intervention'}</strong>
                </div>
              </div>
              
              {isRescued && (
                <div className="mission-results-check">
                  <h5>🏆 Demo Impact Accomplished</h5>
                  <ul className="results-list">
                    <li>✓ Academic/Work Deadline Saved</li>
                    <li>✓ {demoScenario === 'student' ? '2.5' : demoScenario === 'professional' ? '3.0' : '4.5'} Focus Hours Optimized</li>
                    <li>✓ Burnout Risk Reduced (Sufficient Rest Recommended)</li>
                    <li>✓ Apology Email Ready in Negotiation Hub</li>
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Emergency Rescue Dashboard Widget (Featured Active Rescue) */}
      {rescueTaskCandidate && (
        <div className="emergency-rescue-widget glass-card pulsing-border-red">
          <div className="rescue-widget-header">
            <div className="widget-title">
              <ShieldAlert size={22} className="text-red animate-pulse" />
              <div>
                <h3>EMERGENCY DEADLINE RESCUE ACTIVE</h3>
                <p className="subtitle">AI Agent coordinating rescue execution plan for '{rescueTaskCandidate.title}'</p>
              </div>
            </div>
            <div className="time-badge urgent">{getRelativeTime(rescueTaskCandidate.due_date)}</div>
          </div>

          <div className="rescue-details-grid">
            {/* Completion probability circle */}
            <div className="prob-circle-container">
              <svg className="prob-circle" viewBox="0 0 100 100">
                <circle className="circle-bg" cx="50" cy="50" r="40" />
                <circle 
                  className={`circle-progress ${rescueTaskCandidate.completion_probability < 0.4 ? 'color-red' : 'color-orange'}`}
                  cx="50" 
                  cy="50" 
                  r="40" 
                  strokeDasharray="251.2"
                  strokeDashoffset={251.2 - (251.2 * rescueTaskCandidate.completion_probability)}
                />
              </svg>
              <div className="prob-circle-text">
                <span className="prob-number">{Math.round(rescueTaskCandidate.completion_probability * 100)}%</span>
                <span className="prob-label">Prob. of Success</span>
              </div>
            </div>

            {/* Strategic Details */}
            <div className="rescue-text-details">
              <div className="strategy-box">
                <span className="box-label">RESCUE STRATEGY</span>
                <p className="strategy-desc">{rescueTaskCandidate.rescue_strategy}</p>
              </div>
              <div className="action-box">
                <span className="box-label">CRITICAL NEXT ACTION</span>
                <p className="action-desc text-red font-weight-bold">
                  ⚡ {rescueTaskCandidate.critical_next_action}
                </p>
              </div>
            </div>

            {/* Rescue Timeline */}
            <div className="timeline-box">
              <span className="box-label">RESCUE TIMELINE</span>
              <div className="micro-timeline">
                {parseRescueTimeline(rescueTaskCandidate.rescue_timeline).map((milestone, idx) => (
                  <div key={idx} className="timeline-milestone-item">
                    <span className="milestone-time">{milestone.time}</span>
                    <span className="milestone-divider"></span>
                    <span className="milestone-title">{milestone.title}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid Content */}
      <div className="dashboard-grid SDE3-grid" style={{ alignItems: 'stretch' }}>
        
        {/* Left Side: Threats Radar & Priorities */}
        <div className="dashboard-left-column" style={{ display: 'flex', flexDirection: 'column', alignSelf: 'stretch' }}>
          {/* Radar Scanner Block */}
          <section className="glass-card radar-block">
            <div className="card-header">
              <h3>Emergency Threat Radar</h3>
              <span className="live-tag">LIVE SCAN</span>
            </div>
            
            <div className="radar-screen-wrapper">
              <div className="radar-screen">
                <div className="radar-sweep"></div>
                <div className="radar-circle circle-1"></div>
                <div className="radar-circle circle-2"></div>
                <div className="radar-circle circle-3"></div>
                <div className="radar-crosshair-x"></div>
                <div className="radar-crosshair-y"></div>
                
                {pendingTasks.slice(0, 5).map((task, idx) => {
                  const angles = [45, 120, 210, 290, 340];
                  const angle = angles[idx % angles.length] * (Math.PI / 180);
                  const maxPanic = 4.0;
                  const normalizedPanic = Math.min(task.panic_index || 0.1, maxPanic);
                  const distancePct = 85 - (normalizedPanic / maxPanic) * 60;
                  
                  const top = 50 + distancePct * Math.sin(angle) * 0.5;
                  const left = 50 + distancePct * Math.cos(angle) * 0.5;
                  
                  const isUrgent = task.priority === 'Urgent' || task.status === 'Overdue';
                  
                  return (
                    <div 
                      key={task.id} 
                      className={`radar-blip ${isUrgent ? 'blip-red' : 'blip-yellow'}`}
                      style={{ top: `${top}%`, left: `${left}%` }}
                      title={`${task.title} (Panic: ${task.panic_index})`}
                    >
                      <span className="blip-label">{task.title.substring(0, 12)}...</span>
                    </div>
                  );
                })}
                
                {pendingTasks.length === 0 && (
                  <div className="radar-clear-message">
                    <CheckCircle color="#10b981" size={28} />
                    <p>Radar Clear. No active threats.</p>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Core Priorities list with Explainable AI cards */}
          <section className="glass-card rescue-block" style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', flexGrow: 1 }}>
            <div className="card-header" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                <h3>Priority Actions &amp; Explainable AI</h3>
                <span className="priority-tag">sorted by panic Index</span>
              </div>
              <div className="category-filters-container" style={{ display: 'flex', gap: '8px', marginTop: '4px', width: '100%', overflowX: 'auto', paddingBottom: '4px' }}>
                {['All', 'Work', 'Academic', 'Life', 'Personal'].map(cat => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(cat)}
                    className={`category-filter-btn ${selectedCategory === cat ? 'active' : ''}`}
                    style={{
                      background: selectedCategory === cat ? 'rgba(0, 240, 255, 0.1)' : 'rgba(255, 255, 255, 0.02)',
                      border: selectedCategory === cat ? '1px solid var(--color-cyan)' : '1px solid var(--border-color)',
                      color: selectedCategory === cat ? 'var(--color-cyan)' : 'var(--text-secondary)',
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '0.75rem',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      outline: 'none'
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            <div className="rescue-list" style={{ display: 'flex', flexDirection: 'column', flexGrow: 1, height: 'auto', maxHeight: 'none' }}>
              {highPanicTasks.slice(0, 4).map(task => {
                const isExpanded = expandedReasoningTaskId === task.id;
                const hasRescue = !!task.rescue_strategy;
                return (
                  <div key={task.id} className="priority-card-wrapper">
                    <div className={`rescue-item ${task.status === 'Overdue' ? 'threat-overdue' : ''}`}>
                      <div className="rescue-item-meta">
                        <div className="rescue-title-row">
                          <span className={`badge badge-${task.priority.toLowerCase()}`}>
                            {task.priority}
                          </span>
                          <span className="time-badge">{getRelativeTime(task.due_date)}</span>
                          {task.completion_probability !== undefined && (
                            <span className={`prob-badge ${task.completion_probability < 0.4 ? 'risk-critical' : task.completion_probability < 0.7 ? 'risk-warning' : 'risk-safe'}`}>
                              P(Success): {Math.round(task.completion_probability * 100)}%
                            </span>
                          )}
                        </div>
                        <h4>{task.title}</h4>
                        <div className="panic-info-row">
                          <p className="panic-text">Panic Index: <strong>{task.panic_index}</strong></p>
                          <button 
                            className="explain-btn" 
                            onClick={() => toggleReasoning(task.id)}
                          >
                            {isExpanded ? <><ChevronUp size={12} /> Hide AI Reasoning</> : <><ChevronDown size={12} /> Explain AI decision</>}
                          </button>
                        </div>
                      </div>
                      
                      <div className="rescue-actions">
                        {task.subtasks && task.subtasks.length > 0 ? (
                          <button 
                            onClick={() => startPomodoro(task)}
                            className="btn btn-primary btn-sm"
                          >
                            <Play size={14} /> Start Focus
                          </button>
                        ) : (
                          <button 
                            onClick={() => rescueTask(task.id)}
                            className="btn btn-accent btn-sm glow-pulse-hover"
                          >
                            <Sparkles size={14} /> AI Rescue Plan
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Expandable Explainable AI & Opportunity Cost details card */}
                    {isExpanded && (
                      <div className="explainable-ai-card glass-card animate-slide-in">
                        <div className="reasoning-grid">
                          <div className="reason-item">
                            <span className="reason-label">Why this was prioritized:</span>
                            <p className="reason-text">{task.ai_reasoning || "Computational heuristics calculated this task as the highest relative impact deadline slot."}</p>
                          </div>
                          
                          <div className="reason-item">
                            <span className="reason-label">Opportunity Cost Trade-off:</span>
                            <p className="reason-text text-yellow">
                              {task.loss_if_skipped 
                                ? `⚠️ ${task.loss_if_skipped}` 
                                : `If you postpone this task, your probability of completing upcoming deliverables decreases by ${Math.round((1.0 - task.completion_probability) * 50)}%.`}
                            </p>
                          </div>

                          <div className="reason-item formulas">
                            <span className="reason-label">Panic Index Formula Derivation:</span>
                            <code className="reason-formula-block">
                              Panic Score = (Estimated Hours [{task.estimated_hours}h] / Hours Left) * Weight<br />
                              Calculated value: {task.panic_index}
                            </code>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
              
              {highPanicTasks.length === 0 && (
                <div className="empty-state">
                  <p>All clear! Relax or add new tasks using the command center.</p>
                </div>
              )}
            </div>
          </section>
        </div>

        {/* Right Side: Real-time Agent Activity Feed & Health analysis */}
        <div className="dashboard-right-column" style={{ display: 'flex', flexDirection: 'column', alignSelf: 'stretch' }}>
          {/* Agent Activity Feed Panel */}
          <section className="glass-card agent-feed-card">
            <div className="card-header">
              <div className="title-with-icon">
                <Cpu size={18} color="#bc34fa" className="animate-pulse" />
                <h3>Agent Activity Feed</h3>
              </div>
              <span className="live-tag active">AUTONOMOUS LOOP</span>
            </div>

            <div className="agent-activity-scroll">
              {agentActivities.length > 0 ? (
                agentActivities.map(activity => (
                  <div key={activity.id} className="activity-feed-item">
                    <div className="activity-meta">
                      <span className="activity-agent-name">[{activity.agent_name}]</span>
                      <span className="activity-time">{new Date(activity.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                    </div>
                    <p className="activity-desc">{activity.action_taken}</p>
                  </div>
                ))
              ) : (
                <div className="empty-feed">
                  <p>Awaiting event triggers on the bus...</p>
                </div>
              )}
            </div>
          </section>

          {/* Context-Aware Smart Alerts (Notifications) */}
          {notifications.filter(n => !n.is_read).length > 0 && (
            <section className="glass-card smart-alerts-card" style={{ marginTop: '1.5rem', width: '100%' }}>
              <div className="card-header">
                <div className="title-with-icon">
                  <AlertCircle size={18} color="#00f0ff" className="animate-pulse" />
                  <h3>Smart Interventions</h3>
                </div>
              </div>
              <div className="alerts-list">
                {notifications.filter(n => !n.is_read).slice(0, 3).map(notif => (
                  <div key={notif.id} className={`alert-item-row alert-${notif.type}`}>
                    <p>{notif.message}</p>
                    <button 
                      onClick={() => readNotification(notif.id)} 
                      className="alert-dismiss-btn"
                      title="Dismiss Alert"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Productivity Health Summary Widget */}
          <section className="glass-card health-summary-widget" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <h3>Health & Overload Metrics</h3>
            </div>
            
            <div className="health-gauge-grid">
              <div className="health-score-container">
                <div className="productivity-value">{healthStats.productivity_score}</div>
                <div className="productivity-label">Productivity score</div>
              </div>
              <div className="health-metric-box">
                <span className="health-risk-label">Burnout Risk:</span>
                <span className={`risk-badge-value ${healthStats.burnout_risk.toLowerCase()}`}>
                  {healthStats.burnout_risk}
                </span>
                <p className="health-tip-preview">{healthStats.suggested_rest}</p>
              </div>
            </div>
          </section>
        </div>

      </div>

      {/* AI Recommendations */}
      {recommendations.length > 0 && (
        <section className="glass-card recommendations-block" style={{ marginTop: '1.5rem' }}>
          <div className="card-header">
            <div className="title-with-spark">
              <Sparkles size={16} color="#00f0ff" className="sparkle-icon" />
              <h3>AI Productivity Insights</h3>
            </div>
          </div>
          <div className="recommendations-list">
            {recommendations.map(rec => (
              <div key={rec.id} className="recommendation-item">
                <p>{rec.content}</p>
                <button 
                  onClick={() => dismissRecommendation(rec.id)} 
                  className="dismiss-btn"
                  title="Dismiss recommendation"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

export default Dashboard;
