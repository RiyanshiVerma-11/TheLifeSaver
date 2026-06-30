import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Sparkles, Calendar, Clock, Play, Trash2, CalendarDays, RefreshCw, X, Save } from 'lucide-react';

const CalendarView = () => {
  const { 
    schedule, 
    autoPlanSchedule, 
    tasks, 
    setFocusTask, 
    setTimerMinutes, 
    setTimerSeconds, 
    setTimerIsRunning, 
    setActiveTab,
    calendarEvents,
    addCalendarEvent,
    updateCalendarEvent,
    deleteCalendarEvent,
    syncGoogleCalendar,
    connectGoogleAccount,
    userSettings
  } = useApp();

  const [evTitle, setEvTitle] = useState('');
  const [evStart, setEvStart] = useState('');
  const [evEnd, setEvEnd] = useState('');

  // showSyncModal controls the edit review modal
  const [showSyncModal, setShowSyncModal] = useState(false);
  // Local editable copy of events populated from calendarEvents context
  const [eventsToEdit, setEventsToEdit] = useState([]);

  const formatDateTimeForInput = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      const tzOffset = date.getTimezoneOffset() * 60000;
      return (new Date(date - tzOffset)).toISOString().slice(0, 16);
    } catch {
      return '';
    }
  };

  const handleSyncClick = async () => {
    // Perform standard sync trigger first — this updates calendarEvents in context
    await syncGoogleCalendar();
    
    // After sync, populate the editable copy from the calendarEvents state (external events only)
    // calendarEvents is up-to-date since syncGoogleCalendar awaits fetchCalendarEvents internally
    const externalEvents = calendarEvents.filter(e => e.is_external || e.source === "Google Calendar");
    setEventsToEdit(externalEvents.map(e => ({
      id: e.id,
      title: e.title,
      start_time: formatDateTimeForInput(e.start_time),
      end_time: formatDateTimeForInput(e.end_time),
      source: e.source || "Google Calendar",
      is_external: true
    })));
    
    // Open the modal
    setShowSyncModal(true);
  };

  const handleEventChange = (index, field, value) => {
    const updated = [...eventsToEdit];
    updated[index][field] = value;
    setEventsToEdit(updated);
  };

  const handleSaveSync = async () => {
    for (const ev of eventsToEdit) {
      await updateCalendarEvent(ev.id, {
        title: ev.title,
        start_time: new Date(ev.start_time).toISOString(),
        end_time: new Date(ev.end_time).toISOString(),
        source: ev.source,
        is_external: ev.is_external
      });
    }
    await autoPlanSchedule();
    setShowSyncModal(false);
  };

  const handleStartBlockFocus = (taskId) => {
    const task = tasks.find(t => t.id === taskId);
    if (task) {
      setFocusTask(task);
      setTimerMinutes(25);
      setTimerSeconds(0);
      setTimerIsRunning(true);
      setActiveTab('tasks');
    }
  };

  const handleAddEvent = async (e) => {
    e.preventDefault();
    if (!evTitle || !evStart || !evEnd) return;
    await addCalendarEvent({
      title: evTitle,
      start_time: new Date(evStart).toISOString(),
      end_time: new Date(evEnd).toISOString(),
      source: "Google Calendar",
      is_external: true
    });
    setEvTitle('');
    setEvStart('');
    setEvEnd('');
  };

  const formatBlockTime = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatBlockDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
  };

  // Group blocks by date
  const groupedBlocks = schedule.reduce((acc, block) => {
    const dateStr = new Date(block.start_time).toDateString();
    if (!acc[dateStr]) acc[dateStr] = [];
    acc[dateStr].push(block);
    return acc;
  }, {});

  // Group external events by date
  const groupedEvents = calendarEvents.reduce((acc, ev) => {
    const dateStr = new Date(ev.start_time).toDateString();
    if (!acc[dateStr]) acc[dateStr] = [];
    acc[dateStr].push(ev);
    return acc;
  }, {});

  // All dates merged
  const allDates = Array.from(new Set([
    ...Object.keys(groupedBlocks),
    ...Object.keys(groupedEvents)
  ])).sort((a, b) => new Date(a) - new Date(b));

  return (
    <div className="calendar-container">
      <header className="section-header">
        <div>
          <h2>Schedule Matrix & GCal Sync</h2>
          <p className="subtitle">AI-calculated Pomodoro slots fitted around Google Calendar sync events.</p>
        </div>
        <div className="calendar-header-actions">
          <button 
            onClick={() => window.open('https://calendar.google.com/', '_blank')} 
            className="btn btn-muted glow-pulse-hover"
            style={{ marginRight: '0.75rem' }}
          >
            <CalendarDays size={14} /> Open Google Calendar
          </button>
          <button 
            onClick={handleSyncClick} 
            className="btn btn-muted glow-pulse-hover"
            style={{ marginRight: '0.75rem' }}
          >
            <RefreshCw size={14} /> Sync Google Calendar
          </button>
          <button 
            onClick={autoPlanSchedule} 
            className="btn btn-accent glow-pulse-hover"
          >
            <Sparkles size={16} /> Rebuild Schedule
          </button>
        </div>
      </header>

      {/* Connection notification */}
      {!userSettings.google_account_connected && (
        <div className="connection-alert-box glass-card animate-slide-in" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CalendarDays size={16} className="text-yellow animate-pulse" />
            <span>Currently in **Sandbox mode**. Any events added below will simulate Google Calendar entries to test collision avoidance.</span>
          </div>
          <button 
            onClick={connectGoogleAccount} 
            className="btn btn-accent btn-xs glow-pulse-hover" 
            style={{ fontSize: '0.75rem', padding: '0.2rem 0.6rem', marginLeft: '1rem' }}
          >
            Connect Real Google Calendar
          </button>
        </div>
      )}

      <div className="calendar-content grid-split">
        {/* Left Side: Combined Timeline showing focus blocks and external calendar events */}
        <div className="timeline-column glass-card">
          <div className="card-header">
            <Calendar size={18} color="#00f0ff" />
            <h3>Your Integrated Time Grid</h3>
          </div>

          <div className="timeline-scroll">
            {allDates.length > 0 ? (
              allDates.map(dateKey => {
                const dayBlocks = groupedBlocks[dateKey] || [];
                const dayEvents = groupedEvents[dateKey] || [];
                
                // Combine and sort chronologically
                const items = [
                  ...dayBlocks.map(b => ({ ...b, type: 'focus' })),
                  ...dayEvents.map(e => ({ ...e, type: 'external' }))
                ].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

                return (
                  <div key={dateKey} className="timeline-date-group">
                    <h4 className="date-group-header">{formatBlockDate(dateKey)}</h4>
                    
                    <div className="timeline-items">
                      {items.map(item => {
                        if (item.type === 'focus') {
                          const associatedTask = tasks.find(t => t.id === item.task_id);
                          return (
                            <div key={`focus-${item.id}`} className="timeline-item-card focus-card glass-card">
                              <div className="timeline-time-meta">
                                <Clock size={12} color="#00f0ff" />
                                <span className="text-cyan">
                                  [Focus] {formatBlockTime(item.start_time)} - {formatBlockTime(item.end_time)}
                                </span>
                              </div>
                              
                              <div className="timeline-task-details">
                                <h5>{associatedTask ? associatedTask.title : "Unmapped Task"}</h5>
                                <p>{associatedTask ? associatedTask.category : "General"}</p>
                              </div>

                              {associatedTask && (
                                <button 
                                  onClick={() => handleStartBlockFocus(item.task_id)}
                                  className="btn-play-action"
                                  title="Start Focus Block"
                                >
                                  <Play size={14} />
                                </button>
                              )}
                            </div>
                          );
                        } else {
                          return (
                            <div key={`ev-${item.id}`} className="timeline-item-card external-event-card glass-card">
                              <div className="timeline-time-meta">
                                <Clock size={12} color="#bc34fa" />
                                <span className="text-purple">
                                  [Meeting] {formatBlockTime(item.start_time)} - {formatBlockTime(item.end_time)}
                                </span>
                              </div>
                              
                              <div className="timeline-task-details">
                                <h5>{item.title}</h5>
                                <p className="text-muted">{item.source}</p>
                              </div>

                              <button 
                                onClick={() => deleteCalendarEvent(item.id)}
                                className="btn-delete-action text-red"
                                title="Delete Event"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          );
                        }
                      })}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="empty-state">
                <p>No active schedule allocations. Add calendar meetings on the right or rebuild schedule to slot focus sessions.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Add Simulated Calendar events and instructions */}
        <div className="instructions-column flex-column">
          <div className="glass-card new-event-card" style={{ marginBottom: '1.5rem', width: '100%' }}>
            <div className="card-header">
              <CalendarDays size={18} color="#00f0ff" />
              <h3>Add Calendar Event</h3>
            </div>
            
            <form onSubmit={handleAddEvent} className="settings-form">
              <div className="form-group">
                <label>Meeting Title:</label>
                <input 
                  type="text" 
                  value={evTitle} 
                  onChange={e => setEvTitle(e.target.value)} 
                  className="form-control"
                  placeholder="e.g. Stakeholder Review Session"
                  required
                />
              </div>

              <div className="form-group">
                <label>Start Date & Time:</label>
                <input 
                  type="datetime-local" 
                  value={evStart} 
                  onChange={e => setEvStart(e.target.value)} 
                  className="form-control"
                  required
                />
              </div>

              <div className="form-group">
                <label>End Date & Time:</label>
                <input 
                  type="datetime-local" 
                  value={evEnd} 
                  onChange={e => setEvEnd(e.target.value)} 
                  className="form-control"
                  required
                />
              </div>

              <button type="submit" className="btn btn-accent btn-block glow-pulse-hover">
                Inject Conflict Event
              </button>
            </form>
          </div>

          <div className="glass-card" style={{ width: '100%' }}>
            <h3>SDE-3 Conflict Mitigation</h3>
            <ul className="info-list">
              <li>
                <strong>Collision Detection:</strong> The AI Agent scans for overlaps with synced Google Calendar events.
              </li>
              <li>
                <strong>Auto-Push Blocks:</strong> If a focus session collides with a meeting, the block is dynamically pushed to the next open business slot.
              </li>
              <li>
                <strong>Recalculate Probability:</strong> Adding calendar events reduces your available free hours, updating deadline risk predictions instantly.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Google Calendar Sync & Edit Modal */}
      {showSyncModal && (
        <div className="modal-overlay">
          <div className="modal-content glass-card">
            <header className="modal-header">
              <h3>✍️ Review Synced Calendar Events</h3>
              <button 
                onClick={() => setShowSyncModal(false)}
                className="modal-close-btn"
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </header>
            
            <div className="modal-body">
              <p className="subtitle" style={{ margin: 0 }}>
                Adjust meeting times and titles imported from your calendar. Saving will trigger the AI scheduler to recalculate your focus slots automatically.
              </p>
              
              {eventsToEdit.length > 0 ? (
                eventsToEdit.map((ev, index) => (
                  <div key={ev.id} className="synced-event-edit-card">
                    <div className="event-index-label">Meeting #{index + 1}</div>
                    
                    <div className="form-group" style={{ marginTop: '4px' }}>
                      <label style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Title:</label>
                      <input 
                        type="text"
                        value={ev.title}
                        onChange={e => handleEventChange(index, 'title', e.target.value)}
                        className="form-control"
                        style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px 12px', color: 'var(--text-primary)', width: '100%', fontSize: '0.9rem' }}
                      />
                    </div>
                    
                    <div className="form-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                      <div className="form-group">
                        <label style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Start Time:</label>
                        <input 
                          type="datetime-local"
                          value={ev.start_time}
                          onChange={e => handleEventChange(index, 'start_time', e.target.value)}
                          className="form-control"
                          style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px 12px', color: 'var(--text-primary)', width: '100%', fontSize: '0.9rem' }}
                        />
                      </div>
                      
                      <div className="form-group">
                        <label style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>End Time:</label>
                        <input 
                          type="datetime-local"
                          value={ev.end_time}
                          onChange={e => handleEventChange(index, 'end_time', e.target.value)}
                          className="form-control"
                          style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px 12px', color: 'var(--text-primary)', width: '100%', fontSize: '0.9rem' }}
                        />
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state" style={{ padding: '20px', textAlign: 'center' }}>
                  <p>No external Google Calendar events fetched. Connect your account or inject simulated events first.</p>
                </div>
              )}
            </div>
            
            <footer className="modal-footer">
              <button 
                onClick={() => setShowSyncModal(false)}
                className="btn btn-secondary btn-sm"
              >
                Cancel
              </button>
              <button 
                onClick={handleSaveSync}
                className="btn btn-accent btn-sm glow-pulse-hover"
                disabled={eventsToEdit.length === 0}
              >
                <Save size={14} /> Save & Rebuild Schedule
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
};

export default CalendarView;
