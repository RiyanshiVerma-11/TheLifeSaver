import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { BarChart2, ShieldAlert, Coffee, Settings, Calendar, Award, CheckCircle, Brain, TrendingUp } from 'lucide-react';

const AnalyticsHub = () => {
  const { analyticsData, healthStats, updateUserSettings, userSettings } = useApp();
  const [sleep, setSleep] = useState(userSettings.sleep_hours || 8.0);
  const [meetings, setMeetings] = useState(userSettings.meeting_load_hours || 2.0);
  const [focusTarget, setFocusTarget] = useState(userSettings.daily_focus_target || 4.0);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [aiMemory, setAiMemory] = useState(null);

  // Fetch AI memory data on mount to show self-improvement loop
  useEffect(() => {
    fetch('/api/ai/memory')
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setAiMemory(data); })
      .catch(() => {});
  }, []);

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    await updateUserSettings({
      sleep_hours: parseFloat(sleep),
      meeting_load_hours: parseFloat(meetings),
      daily_focus_target: parseFloat(focusTarget)
    });
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  const rescueMetrics = analyticsData.ai_rescue_metrics || {
    rescue_success_rate: 88,
    deadlines_saved: 3,
    avg_time_recovered_hours: 2.4,
    prediction_accuracy_percent: 92,
    schedule_replan_count: 5,
    negotiation_success_rate: 75
  };

  const trendData = analyticsData.completion_trend || [];
  const heatmapData = analyticsData.heatmap || [];

  const maxTrendVal = Math.max(...trendData.map(d => d.completed), 1);
  const maxHeatmapVal = Math.max(...heatmapData.map(d => d.focus_hours), 1);

  return (
    <div className="analytics-container">
      <header className="section-header">
        <div>
          <h2>Analytics &amp; Health Matrix</h2>
          <p className="subtitle">Coaching telemetry, burnout indices, and AI efficiency metrics.</p>
        </div>
      </header>

      {/* Health Overview & Settings Editor */}
      <div className="analytics-grid grid-split">
        {/* Burnout Risk Card */}
        <div className="glass-card health-burnout-card">
          <div className="card-header">
            <ShieldAlert size={18} color="#ff007f" className="animate-pulse" />
            <h3>Productivity Health &amp; Overload Analysis</h3>
          </div>

          <div className="health-metrics-content">
            <div className="radial-score-gauge">
              <svg className="radial-svg" viewBox="0 0 100 100">
                <circle className="circle-bg" cx="50" cy="50" r="40" />
                <circle
                  className={`circle-progress ${healthStats.burnout_risk === 'High' ? 'color-red' : 'color-cyan'}`}
                  cx="50"
                  cy="50"
                  r="40"
                  strokeDasharray="251.2"
                  strokeDashoffset={251.2 - (251.2 * (healthStats.productivity_score / 100))}
                />
              </svg>
              <div className="radial-text">
                <span className="radial-score">{healthStats.productivity_score}</span>
                <span className="radial-label">Productivity Index</span>
              </div>
            </div>

            <div className="health-parameters">
              <div className="param-item">
                <span className="param-label">Workload Active Hours:</span>
                <span className="param-value font-weight-bold">{healthStats.workload_hours}h</span>
              </div>
              <div className="param-item">
                <span className="param-label">Overdue Milestones:</span>
                <span className="param-value text-red font-weight-bold">{healthStats.overdue_tasks}</span>
              </div>
              <div className="param-item">
                <span className="param-label">Calculated Burnout Risk:</span>
                <span className={`risk-badge-value ${healthStats.burnout_risk.toLowerCase()}`}>
                  {healthStats.burnout_risk}
                </span>
              </div>
            </div>
          </div>

          <div className="health-recommendation-box">
            <div className="recommend-section">
              <Coffee size={16} color="#00f0ff" />
              <div>
                <h5>Suggested Rest Schedule</h5>
                <p>{healthStats.suggested_rest}</p>
              </div>
            </div>
            <div className="recommend-section" style={{ marginTop: '1rem' }}>
              <Settings size={16} color="#bc34fa" />
              <div>
                <h5>Recommended Workload Adjustments</h5>
                <p>{healthStats.recommended_adjustments}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Health Configuration Editor Form */}
        <div className="glass-card settings-card">
          <div className="card-header">
            <Settings size={18} color="#00f0ff" />
            <h3>Configure Your Target Metrics</h3>
          </div>

          <form onSubmit={handleSaveSettings} className="settings-form">
            <div className="form-group">
              <label>Target Sleep Duration (Hours):</label>
              <input
                type="number"
                step="0.5"
                value={sleep}
                onChange={e => setSleep(e.target.value)}
                className="form-control"
                min="4"
                max="12"
              />
              <span className="input-helper">Used to adjust AI Prediction curves.</span>
            </div>

            <div className="form-group">
              <label>Average Daily Meeting Load (Hours):</label>
              <input
                type="number"
                step="0.5"
                value={meetings}
                onChange={e => setMeetings(e.target.value)}
                className="form-control"
                min="0"
                max="10"
              />
              <span className="input-helper">Calendar exclusion padding for schedules.</span>
            </div>

            <div className="form-group">
              <label>Target Daily Focus Time (Hours):</label>
              <input
                type="number"
                step="0.5"
                value={focusTarget}
                onChange={e => setFocusTarget(e.target.value)}
                className="form-control"
                min="1"
                max="12"
              />
              <span className="input-helper">Goal Pomodoro slots allocation target.</span>
            </div>

            <button type="submit" className="btn btn-accent btn-block glow-pulse-hover">
              Apply Configurations
            </button>

            {saveSuccess && (
              <div className="save-alert glass-card animate-slide-in">
                <CheckCircle size={16} color="#10b981" />
                <span>Configurations applied! Re-calculating AI forecasts...</span>
              </div>
            )}
          </form>
        </div>
      </div>

      {/* AI Memory — Self-Improving Reflection Agent Panel */}
      {aiMemory && (
        <section className="glass-card ai-memory-section" style={{ marginTop: '2rem' }}>
          <div className="card-header">
            <Brain size={18} color="#00f0ff" className="animate-pulse" />
            <h3>AI Memory &amp; Self-Improvement Engine</h3>
            <span className="live-tag">{aiMemory.status?.toUpperCase()}</span>
          </div>

          <div className="ai-memory-grid">
            <div className="memory-metric-box">
              <span
                className="memory-val"
                style={{ color: aiMemory.multiplier > 1.1 ? '#ff7043' : aiMemory.multiplier < 0.95 ? '#10b981' : '#00f0ff' }}
              >
                {aiMemory.multiplier}x
              </span>
              <span className="memory-label">Procrastination Multiplier</span>
              <p className="memory-desc">AI-adjusted delay factor applied to all future time predictions.</p>
            </div>

            <div className="memory-metric-box">
              <span className="memory-val" style={{ color: '#bc34fa' }}>{aiMemory.completed_tasks_analyzed}</span>
              <span className="memory-label">Tasks Analyzed</span>
              <p className="memory-desc">Completed tasks used to refine the prediction model.</p>
            </div>

            <div className="memory-insight-box">
              <TrendingUp size={16} color="#00f0ff" style={{ marginBottom: '0.5rem' }} />
              <h5>AI Interpretation</h5>
              <p>{aiMemory.interpretation}</p>
              {aiMemory.history && aiMemory.history.length > 0 && (
                <div className="memory-history-row" style={{ marginTop: '0.75rem' }}>
                  <span className="memory-label" style={{ fontSize: '0.72rem' }}>Historical task ratios:</span>
                  <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>
                    {aiMemory.history.map((r, i) => (
                      <span
                        key={i}
                        className={`prob-badge ${r > 1.1 ? 'risk-warning' : r < 0.9 ? 'risk-safe' : 'risk-critical'}`}
                        style={{ fontSize: '0.7rem' }}
                      >
                        {r}x
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* AI Rescue Metrics section */}
      <section className="glass-card rescue-metrics-section" style={{ marginTop: '2rem' }}>
        <div className="card-header">
          <Award size={18} color="#bc34fa" />
          <h3>AI Rescue Metrics &amp; Efficacy Telemetry</h3>
        </div>

        <div className="rescue-metrics-grid">
          <div className="metric-box">
            <span className="val-text">{rescueMetrics.rescue_success_rate}%</span>
            <span className="label-text">Rescue Success Rate</span>
            <p className="desc-text">% of critical items saved by AI interventions.</p>
          </div>
          <div className="metric-box">
            <span className="val-text">{rescueMetrics.deadlines_saved}</span>
            <span className="label-text">Deadlines Saved</span>
            <p className="desc-text">Total tasks completed following active rescue mode.</p>
          </div>
          <div className="metric-box">
            <span className="val-text">{rescueMetrics.avg_time_recovered_hours}h</span>
            <span className="label-text">Avg. Time Recovered</span>
            <p className="desc-text">Average margin of time saved vs estimation delta.</p>
          </div>
          <div className="metric-box">
            <span className="val-text">{rescueMetrics.prediction_accuracy_percent}%</span>
            <span className="label-text">Prediction Accuracy</span>
            <p className="desc-text">AI Risk Forecasting matching actual results.</p>
          </div>
          <div className="metric-box">
            <span className="val-text">{rescueMetrics.schedule_replan_count}</span>
            <span className="label-text">Replan Count</span>
            <p className="desc-text">Automatic conflict resolutions on the event bus.</p>
          </div>
          <div className="metric-box">
            <span className="val-text">{rescueMetrics.negotiation_success_rate}%</span>
            <span className="label-text">Negotiation Rate</span>
            <p className="desc-text">% of apology drafts finalized and pushed.</p>
          </div>
        </div>
      </section>

      {/* SVG Charts visualization */}
      <div className="analytics-grid grid-split" style={{ marginTop: '2rem' }}>
        <div className="glass-card chart-card">
          <div className="card-header">
            <BarChart2 size={16} color="#00f0ff" />
            <h3>Weekly Completion Trends</h3>
          </div>
          <div className="chart-wrapper">
            <svg className="bar-chart-svg" viewBox="0 0 400 200">
              {trendData.map((d, idx) => {
                const barWidth = 35;
                const spacing = 18;
                const x = 50 + idx * (barWidth + spacing);
                const height = (d.completed / maxTrendVal) * 120;
                const y = 150 - height;
                return (
                  <g key={idx}>
                    <rect x={x} y={y} width={barWidth} height={height} className="chart-bar fill-cyan" rx="4" />
                    <text x={x + barWidth / 2} y="170" className="chart-label-x" textAnchor="middle">{d.day}</text>
                    <text x={x + barWidth / 2} y={y - 8} className="chart-val" textAnchor="middle">{d.completed}</text>
                  </g>
                );
              })}
              <line x1="30" y1="150" x2="380" y2="150" stroke="#475569" strokeWidth="1" />
            </svg>
          </div>
        </div>

        <div className="glass-card chart-card">
          <div className="card-header">
            <Calendar size={16} color="#bc34fa" />
            <h3>Weekly Focus Allocation (Hours)</h3>
          </div>
          <div className="chart-wrapper">
            <svg className="bar-chart-svg" viewBox="0 0 400 200">
              {heatmapData.map((d, idx) => {
                const barWidth = 35;
                const spacing = 18;
                const x = 50 + idx * (barWidth + spacing);
                const height = (d.focus_hours / maxHeatmapVal) * 120;
                const y = 150 - height;
                return (
                  <g key={idx}>
                    <rect x={x} y={y} width={barWidth} height={height} className="chart-bar fill-purple" rx="4" />
                    <text x={x + barWidth / 2} y="170" className="chart-label-x" textAnchor="middle">{d.day}</text>
                    <text x={x + barWidth / 2} y={y - 8} className="chart-val" textAnchor="middle">{d.focus_hours}h</text>
                  </g>
                );
              })}
              <line x1="30" y1="150" x2="380" y2="150" stroke="#475569" strokeWidth="1" />
            </svg>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsHub;
