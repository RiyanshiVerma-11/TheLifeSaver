import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Plus, Flame, Check, Trash2, Award } from 'lucide-react';

const HabitTracker = () => {
  const { habits, addHabit, logHabit, deleteHabit } = useApp();
  const [title, setTitle] = useState('');
  const [frequency, setFrequency] = useState('Daily');
  const [showAddForm, setShowAddForm] = useState(false);

  const handleAdd = (e) => {
    e.preventDefault();
    if (!title) return;
    addHabit({ title, frequency });
    setTitle('');
    setShowAddForm(false);
  };

  const isCompletedToday = (habit) => {
    if (!habit.last_completed_date) return false;
    const today = new Date().toISOString().split('T')[0];
    return habit.last_completed_date === today;
  };

  return (
    <div className="habits-container">
      <header className="section-header">
        <div>
          <h2>Habit Station & Streaks</h2>
          <p className="subtitle">Build resilience. Logging habits keeps the AI panic metrics low.</p>
        </div>
        <button 
          onClick={() => setShowAddForm(!showAddForm)} 
          className="btn btn-primary"
        >
          <Plus size={16} /> New Habit
        </button>
      </header>

      {showAddForm && (
        <form onSubmit={handleAdd} className="glass-card add-habit-form">
          <h4>Create Core Habit</h4>
          <div className="form-row">
            <div className="form-group flex-1">
              <label>Habit Name</label>
              <input 
                type="text" 
                value={title} 
                onChange={e => setTitle(e.target.value)} 
                placeholder="e.g. Solve 2 Leetcode problems" 
                required 
              />
            </div>
            
            <div className="form-group">
              <label>Frequency</label>
              <select value={frequency} onChange={e => setFrequency(e.target.value)}>
                <option value="Daily">Daily</option>
                <option value="Weekly">Weekly</option>
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
              Create Habit
            </button>
          </div>
        </form>
      )}

      <div className="habits-grid">
        {habits.map(habit => {
          const doneToday = isCompletedToday(habit);
          return (
            <div key={habit.id} className="habit-card glass-card">
              <div className="habit-header">
                <span className="badge-freq">{habit.frequency}</span>
                <button 
                  onClick={() => deleteHabit(habit.id)}
                  className="delete-habit-btn"
                  title="Remove Habit"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              <h3>{habit.title}</h3>

              <div className="habit-streak-display">
                <Flame size={20} className={habit.streak > 0 ? "streak-active animate-pulse" : "streak-empty"} />
                <div>
                  <p className="streak-count">{habit.streak} Day Streak</p>
                  <p className="streak-status">
                    {habit.streak > 0 ? "Pacing high!" : "Unstarted"}
                  </p>
                </div>
              </div>

              <div className="habit-action-footer">
                {doneToday ? (
                  <div className="habit-completed-tag">
                    <Check size={16} /> Completed Today
                  </div>
                ) : (
                  <button 
                    onClick={() => logHabit(habit.id)}
                    className="btn btn-primary w-full"
                  >
                    Done Today
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {habits.length === 0 && (
          <div className="empty-state glass-card span-all">
            <Award size={36} color="#64748b" />
            <p>No habits added yet. Streaks trigger positive AI coaching metrics. Try creating one!</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default HabitTracker;
// Note: styling classes matching habit layouts will be placed in App.css.
