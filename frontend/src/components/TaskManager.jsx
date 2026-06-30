import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import FocusMode from './FocusMode';
import { 
  Sparkles, 
  Trash2, 
  Check, 
  Clock, 
  ChevronDown, 
  ChevronUp, 
  Plus, 
  Bookmark, 
  Calendar 
} from 'lucide-react';

const TaskManager = () => {
  const { 
    tasks, 
    addTask, 
    updateTask, 
    deleteTask, 
    rescueTask, 
    toggleSubtask 
  } = useApp();

  // State for task creation form
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [priority, setPriority] = useState('Medium');
  const [estHours, setEstHours] = useState(1);
  const [category, setCategory] = useState('Work');
  const [showAddForm, setShowAddForm] = useState(false);

  // Expanded task ID set for viewing subtasks
  const [expandedTasks, setExpandedTasks] = useState(new Set());

  const toggleExpanded = (id) => {
    const updated = new Set(expandedTasks);
    if (updated.has(id)) {
      updated.delete(id);
    } else {
      updated.add(id);
    }
    setExpandedTasks(updated);
  };

  const handleRescue = async (taskId) => {
    setExpandedTasks(prev => {
      const updated = new Set(prev);
      updated.add(taskId);
      return updated;
    });
    await rescueTask(taskId, true);
  };

  const handleCreateTask = (e) => {
    e.preventDefault();
    if (!title || !dueDate) return;

    addTask({
      title,
      description,
      due_date: new Date(dueDate).toISOString(),
      priority,
      estimated_hours: parseFloat(estHours),
      category
    });

    // Reset fields
    setTitle('');
    setDescription('');
    setDueDate('');
    setPriority('Medium');
    setEstHours(1);
    setCategory('Work');
    setShowAddForm(false);
  };

  const markCompleted = (task) => {
    const nextStatus = task.status === 'Completed' ? 'Pending' : 'Completed';
    updateTask(task.id, { status: nextStatus });
  };

  // Format date readable
  const formatDeadline = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="task-manager-layout">
      <div className="task-list-column">
        <header className="section-header">
          <div>
            <h2>Task Center</h2>
            <p className="subtitle">Prioritized using the LMLS dynamic algorithm.</p>
          </div>
          <button 
            onClick={() => setShowAddForm(!showAddForm)} 
            className="btn btn-primary"
          >
            <Plus size={16} /> New Task
          </button>
        </header>

        {showAddForm && (
          <form onSubmit={handleCreateTask} className="glass-card add-task-form">
            <h4>Add New Commitment</h4>
            <div className="form-grid">
              <div className="form-group span-2">
                <label>Task Title *</label>
                <input 
                  type="text" 
                  value={title} 
                  onChange={e => setTitle(e.target.value)} 
                  placeholder="e.g. Finish chemistry project slides" 
                  required 
                />
              </div>

              <div className="form-group span-2">
                <label>Description</label>
                <textarea 
                  value={description} 
                  onChange={e => setDescription(e.target.value)} 
                  placeholder="Notes, links, or instructions..." 
                />
              </div>

              <div className="form-group">
                <label>Due Date & Time *</label>
                <input 
                  type="datetime-local" 
                  value={dueDate} 
                  onChange={e => setDueDate(e.target.value)} 
                  required 
                />
              </div>

              <div className="form-group">
                <label>Priority</label>
                <select value={priority} onChange={e => setPriority(e.target.value)}>
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                  <option value="Urgent">Urgent</option>
                </select>
              </div>

              <div className="form-group">
                <label>Est. Effort (Hours)</label>
                <input 
                  type="number" 
                  step="0.5" 
                  min="0.5"
                  value={estHours} 
                  onChange={e => setEstHours(e.target.value)} 
                />
              </div>

              <div className="form-group">
                <label>Category</label>
                <select value={category} onChange={e => setCategory(e.target.value)}>
                  <option value="Work">Work</option>
                  <option value="Study">Study</option>
                  <option value="Life">Life</option>
                  <option value="Finance">Finance</option>
                </select>
              </div>
            </div>
            
            <div className="form-actions">
              <button 
                type="button" 
                onClick={() => setShowAddForm(false)} 
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button type="submit" className="btn btn-primary">
                Add Commitment
              </button>
            </div>
          </form>
        )}

        <div className="tasks-scroll-area">
          {tasks.map(task => {
            const isCompleted = task.status === 'Completed';
            const hasSubtasks = task.subtasks && task.subtasks.length > 0;
            const completedSubs = hasSubtasks ? task.subtasks.filter(s => s.is_completed).length : 0;
            const progressPct = hasSubtasks ? Math.round((completedSubs / task.subtasks.length) * 100) : 0;
            
            const isExpanded = expandedTasks.has(task.id);
            const isOverdue = task.status === 'Overdue';

            return (
              <div 
                key={task.id} 
                className={`task-card glass-card ${isCompleted ? 'task-completed' : ''} ${isOverdue ? 'border-threat-red' : ''}`}
              >
                <div className="task-card-main">
                  <button 
                    onClick={() => markCompleted(task)} 
                    className={`checkbox-circle ${isCompleted ? 'checked' : ''}`}
                    title={isCompleted ? "Mark pending" : "Mark completed"}
                  >
                    {isCompleted && <Check size={14} />}
                  </button>

                  <div className="task-content">
                    <div className="task-title-line">
                      <h4 className={isCompleted ? 'text-strike' : ''}>{task.title}</h4>
                      <div className="task-badges">
                        <span className="badge-category"><Bookmark size={10} /> {task.category}</span>
                        <span className={`badge badge-${task.priority.toLowerCase()}`}>{task.priority}</span>
                      </div>
                    </div>

                    <p className="task-desc">{task.description}</p>

                    <div className="task-meta">
                      <span className="meta-item"><Calendar size={12} /> {formatDeadline(task.due_date)}</span>
                      <span className="meta-item"><Clock size={12} /> {task.estimated_hours} hrs</span>
                      {!isCompleted && (
                        <span className={`meta-item panic-indicator ${task.panic_index > 1.5 ? 'critical' : ''}`}>
                          Panic Index: <strong>{task.panic_index}</strong>
                        </span>
                      )}
                    </div>

                    {hasSubtasks && (
                      <div className="task-progress-bar-wrapper">
                        <div className="progress-labels">
                          <span>Rescue Progress</span>
                          <span>{completedSubs}/{task.subtasks.length} ({progressPct}%)</span>
                        </div>
                        <div className="progress-track">
                          <div className="progress-fill" style={{ width: `${progressPct}%` }}></div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="task-actions-menu">
                    {!isCompleted && (
                      <button 
                        onClick={() => handleRescue(task.id)}
                        className="rescue-icon-btn glow-pulse-hover"
                        title="Decompose task with AI Rescue"
                      >
                        <Sparkles size={16} />
                      </button>
                    )}
                    <button 
                      onClick={() => toggleExpanded(task.id)} 
                      className="expand-btn"
                    >
                      {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </button>
                    <button 
                      onClick={() => deleteTask(task.id)} 
                      className="delete-icon-btn"
                      title="Delete task"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                {/* Subtask list panel expanded */}
                {isExpanded && (
                  <div className="subtask-expanded-panel">
                    {task.rescue_strategy && (
                      <div className="task-rescue-plan-details" style={{
                        background: 'rgba(255, 59, 48, 0.04)',
                        border: '1px solid rgba(255, 59, 48, 0.15)',
                        borderRadius: '8px',
                        padding: '12px 16px',
                        marginBottom: '16px',
                        fontSize: '0.85rem'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#ff453a', fontWeight: 'bold' }}>
                          <Sparkles size={14} />
                          <span>AI EMERGENCY RECOVERY PLAN</span>
                        </div>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '8px', lineHeight: '1.4' }}>
                          <strong>Strategy:</strong> {task.rescue_strategy}
                        </p>
                        {task.critical_next_action && (
                          <p style={{ color: '#eab308', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span>⚡</span>
                            <span><strong>Critical Next Action:</strong> {task.critical_next_action}</span>
                          </p>
                        )}
                      </div>
                    )}

                    <h5>AI Decomposed Checklist</h5>
                    {hasSubtasks ? (
                      <div className="subtask-list">
                        {task.subtasks.map(sub => (
                          <div key={sub.id} className="subtask-item">
                            <label className="checkbox-container">
                              <input 
                                type="checkbox" 
                                checked={sub.is_completed} 
                                onChange={e => toggleSubtask(task.id, sub.id, e.target.checked)}
                              />
                              <span className="checkmark"></span>
                              <span className={`subtask-title ${sub.is_completed ? 'text-strike' : ''}`}>{sub.title}</span>
                            </label>
                            <span className="subtask-est">{sub.estimated_minutes} min</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="no-subtasks-prompt">
                        <p>No checklist exists. Activate AI Rescue to decompose this task into a step-by-step roadmap.</p>
                        <button 
                          onClick={() => handleRescue(task.id)} 
                          className="btn btn-accent btn-sm"
                        >
                          <Sparkles size={12} /> AI Rescue
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {tasks.length === 0 && (
            <div className="empty-state glass-card">
              <p>No commitments found. Click "New Task" or use the AI chat command.</p>
            </div>
          )}
        </div>
      </div>

      <div className="focus-column">
        <FocusMode />
      </div>
    </div>
  );
};

export default TaskManager;
