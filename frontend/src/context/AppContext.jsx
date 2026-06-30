import React, { createContext, useState, useEffect, useContext, useRef } from 'react';

const AppContext = createContext();

export const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export const AppProvider = ({ children }) => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [tasks, setTasks] = useState([]);
  const [habits, setHabits] = useState([]);
  const [schedule, setSchedule] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [chatHistory, setChatHistory] = useState([
    { sender: 'ai', text: "Hello! I am your AI Rescue Companion. Tell me what needs to be done, or click 'Rescue' on any task in your tracker to break it down.", timestamp: new Date() }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [apiHealth, setApiHealth] = useState(true);

  // New SDE-3 Features State
  const [userSettings, setUserSettings] = useState({
    sleep_hours: 8.0,
    meeting_load_hours: 2.0,
    daily_focus_target: 4.0,
    google_account_connected: false
  });
  const [emailDrafts, setEmailDrafts] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [agentActivities, setAgentActivities] = useState([]);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [analyticsData, setAnalyticsData] = useState({
    completion_trend: [],
    heatmap: [],
    avg_panic_score: 0.0,
    ai_rescue_metrics: {
      rescue_success_rate: 88,
      deadlines_saved: 3,
      avg_time_recovered_hours: 2.4,
      prediction_accuracy_percent: 92,
      schedule_replan_count: 5,
      negotiation_success_rate: 75
    }
  });
  const [healthStats, setHealthStats] = useState({
    productivity_score: 82,
    burnout_risk: "Low",
    workload_hours: 0,
    overdue_tasks: 0,
    suggested_rest: "Maintain standard schedules.",
    recommended_adjustments: "Workload balanced."
  });

  // Flow control: Google Auth login simulation state
  const [demoLoginMode, setDemoLoginMode] = useState(true); // Default to standalone login

  // Focus Station / Pomodoro State
  const [focusTask, setFocusTask] = useState(null);
  const [timerMinutes, setTimerMinutes] = useState(25);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [timerIsRunning, setTimerIsRunning] = useState(false);
  const [timerMode, setTimerMode] = useState('focus'); // 'focus' or 'break'
  const [demoScenario, setDemoScenario] = useState("");
  const [toastMessage, setToastMessage] = useState(null);
  const toastTimeoutRef = useRef(null);

  // Fetch initial data
  useEffect(() => {
    fetchInitialData();
  }, []);

  // Set up background timers: poll logs, health stats, notifications every 15 seconds to simulate Event Bus updates
  useEffect(() => {
    if (!apiHealth) return;
    const interval = setInterval(() => {
      fetchAgentActivities().catch(console.error);
      fetchNotifications().catch(console.error);
      fetchHealthStats().catch(console.error);
      fetchAnalyticsData().catch(console.error);
      fetchTasks().catch(console.error);
      fetchSchedule().catch(console.error);
    }, 15000);
    return () => clearInterval(interval);
  }, [apiHealth]);

  const showToast = (message) => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current);
    }
    setToastMessage(message);
    toastTimeoutRef.current = setTimeout(() => {
      setToastMessage(null);
      toastTimeoutRef.current = null;
    }, 4500);
  };

  const seedDemoData = async (scenario) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/demo/seed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario })
      });
      if (res.ok) {
        const data = await res.json();
        setDemoScenario(scenario);
        await fetchInitialData();
        
        const counts = data.seeded_records;
        const scenLabel = scenario === 'student' ? 'Student' : scenario === 'professional' ? 'Professional' : 'Startup';
        showToast(`✓ ${scenLabel} Scenario Loaded (${counts.tasks} Tasks, ${counts.calendar_events} Calendar Conflict, ${counts.notifications} Alert, ${counts.agent_logs} Agent Activities)`);
      } else {
        console.error("Failed to seed demo data");
        showToast("❌ Seeding failed. Ensure backend service is online.");
      }
    } catch (err) {
      console.error("Error seeding demo data:", err);
      showToast("❌ Network error while loading presentation scenario.");
    } finally {
      setIsLoading(false);
    }
  };

  const fetchInitialData = async () => {
    setIsLoading(true);
    try {
      await Promise.all([
        fetchTasks(),
        fetchHabits(),
        fetchSchedule(),
        fetchRecommendations(),
        fetchUserSettings(),
        fetchEmailDrafts(),
        fetchNotifications(),
        fetchAgentActivities(),
        fetchCalendarEvents(),
        fetchAnalyticsData(),
        fetchHealthStats()
      ]);
      setApiHealth(true);
    } catch (err) {
      console.warn("Failed fetching backend data, running in offline fallback mode.", err);
      setApiHealth(false);
      loadOfflineMockData();
    } finally {
      setIsLoading(false);
    }
  };

  const loadOfflineMockData = () => {
    setTasks([
      { 
        id: 101, 
        title: "Prepare Project Pitch", 
        description: "Need to present slides to investors", 
        due_date: new Date(Date.now() + 3 * 3600 * 1000).toISOString(), 
        priority: "Urgent", 
        status: "In Progress", 
        estimated_hours: 2, 
        category: "Work", 
        panic_index: 2.5, 
        impact: "High",
        reward: "Avoid losing potential investor financing.",
        loss_if_skipped: "Pitch cancellation and failure to secure next round.",
        completion_probability: 0.38,
        rescue_strategy: "Cut details out of slide deck. Focus purely on core traction slides, unit economics, and team introduction.",
        critical_next_action: "Finalize unit economics slide immediately.",
        rescue_timeline: JSON.stringify([
          {"time": "12:30 PM", "title": "Prune deck template", "completed": true},
          {"time": "1:00 PM", "title": "Insert financials overview", "completed": false},
          {"time": "1:30 PM", "title": "Submit deck draft to lead", "completed": false}
        ]),
        subtasks: [
          { id: 201, title: "Define problem statement", is_completed: true, estimated_minutes: 15 }, 
          { id: 202, title: "Draft slide outlines", is_completed: false, estimated_minutes: 30 }
        ] 
      },
      { 
        id: 102, 
        title: "Pay Electricity Bill", 
        description: "Avoid late penalties", 
        due_date: new Date(Date.now() + 18 * 3600 * 1000).toISOString(), 
        priority: "High", 
        status: "Pending", 
        estimated_hours: 0.5, 
        category: "Life", 
        panic_index: 0.8,
        impact: "Medium",
        reward: "Prevent penalty charges.",
        loss_if_skipped: "Utility service interruption.",
        completion_probability: 0.85,
        subtasks: [] 
      }
    ]);
    setHabits([
      { id: 1, title: "Study Algorithms", frequency: "Daily", streak: 3, last_completed_date: new Date().toISOString().split('T')[0] },
      { id: 2, title: "Exercise", frequency: "Daily", streak: 0, last_completed_date: null }
    ]);
    setCalendarEvents([
      { id: 501, title: "Sync with Team", start_time: new Date(Date.now() + 2 * 3600 * 1000).toISOString(), end_time: new Date(Date.now() + 3 * 3600 * 1000).toISOString(), source: "Google Calendar", is_external: true }
    ]);
    setEmailDrafts([
      { id: 601, task_id: 101, recipient: "lead@investors.com", subject: "Brief Delay: Project Pitch Deck", body: "Dear Investors,\n\nI request to push the Pitch Deck submission window to tomorrow morning...", status: "Draft", created_at: new Date().toISOString() }
    ]);
    setNotifications([
      { id: 701, message: "🚨 Emergency Rescue Mode activated for 'Prepare Project Pitch' (Probability at 38%).", type: "urgent", created_at: new Date().toISOString() }
    ]);
    setAgentActivities([
      { id: 801, agent_name: "Prioritization Agent", action_taken: "Re-calculated tasks urgency metrics and sorted workspace queue.", timestamp: new Date().toISOString() },
      { id: 802, agent_name: "AI Prediction Engine", action_taken: "Forecasted Pitch Deck completion probability at 38% based on meeting load.", timestamp: new Date().toISOString() }
    ]);
  };

  const fetchTasks = async () => {
    const res = await fetch(`${API_BASE}/tasks/`);
    if (!res.ok) throw new Error("Tasks fetch failed");
    const data = await res.json();
    setTasks(data);
  };

  const addTask = async (taskData) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tasks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskData)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchTasks();
      await fetchRecommendations();
      await fetchHealthStats();
      await fetchAgentActivities();
      await fetchNotifications();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        const mockTask = {
          id: Date.now(),
          ...taskData,
          panic_index: 0.5,
          completion_probability: 0.90,
          created_at: new Date().toISOString(),
          subtasks: []
        };
        setTasks(prev => [mockTask, ...prev]);
        showToast("✓ Created task offline (saved locally)");
      } else {
        showToast("❌ Failed to create task. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const updateTask = async (taskId, updatedFields) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedFields)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchTasks();
      await fetchHealthStats();
      await fetchAgentActivities();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        setTasks(prev => prev.map(t => t.id === taskId ? { ...t, ...updatedFields } : t));
      } else {
        showToast("❌ Failed to update task.");
      }
    }
  };

  const logTaskFocus = async (taskId, minutes) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}/log-focus?minutes=${minutes}`, {
        method: 'POST'
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchTasks();
      await fetchAnalyticsData();
      await fetchHealthStats();
      await fetchAgentActivities();
      showToast(`✓ Logged ${minutes}m focus time to task.`);
    } catch (err) {
      console.error("Failed to log task focus time:", err);
      showToast("❌ Failed to log focus time.");
    }
  };

  const deleteTask = async (taskId) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchTasks();
      await fetchSchedule();
      await fetchHealthStats();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        setTasks(prev => prev.filter(t => t.id !== taskId));
      } else {
        showToast("❌ Failed to delete task.");
      }
    }
  };

  const rescueTask = async (taskId, preventRedirect = false) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}/rescue`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error("Rescue failed");
      await fetchTasks();
      await fetchSchedule();
      await fetchNotifications();
      await fetchAgentActivities();
      await fetchEmailDrafts();
      await fetchHealthStats();
      if (!preventRedirect) {
        setActiveTab('dashboard');
      }
      triggerBrowserNotification("AI Rescue Mode Activated", "We've built an emergency timeline and extension draft.");
    } catch (err) {
      console.error(err);
      setTasks(prev => prev.map(t => {
        if (t.id === taskId) {
          return {
            ...t,
            status: 'In Progress',
            completion_probability: 0.38,
            rescue_strategy: "Consolidate outline and proceed to raw drafts first.",
            critical_next_action: "Outline main requirements.",
            rescue_timeline: JSON.stringify([
              {"time": "Now + 15m", "title": "Structure Outline", "completed": false},
              {"time": "Now + 45m", "title": "First Draft", "completed": false}
            ])
          };
        }
        return t;
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSubtask = async (taskId, subtaskId, isCompleted) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/subtasks/${subtaskId}?is_completed=${isCompleted}`, {
        method: 'PUT'
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchTasks();
      await fetchAgentActivities();
      await fetchHealthStats();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        setTasks(prev => prev.map(t => {
          if (t.id === taskId) {
            return {
              ...t,
              subtasks: t.subtasks.map(s => s.id === subtaskId ? { ...s, is_completed: isCompleted } : s)
            };
          }
          return t;
        }));
      } else {
        showToast("❌ Failed to toggle subtask status.");
      }
    }
  };

  // User Settings API
  const fetchUserSettings = async () => {
    const res = await fetch(`${API_BASE}/ai/health-analysis`);
    if (!res.ok) {
      throw new Error(`UserSettings fetch failed: status ${res.status}`);
    }
    const data = await res.json();
    if (data.settings) {
      setUserSettings(data.settings);
    }
  };

  const updateUserSettings = async (updatedFields) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedFields)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchUserSettings();
      await fetchHealthStats();
      await fetchSchedule();
      await fetchTasks();
      await fetchAgentActivities();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        setUserSettings(prev => ({ ...prev, ...updatedFields }));
      } else {
        showToast("❌ Failed to update settings.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Smart Notifications API
  const fetchNotifications = async () => {
    const res = await fetch(`${API_BASE}/ai/notifications`);
    if (!res.ok) {
      throw new Error(`Notifications fetch failed: status ${res.status}`);
    }
    const data = await res.json();
    setNotifications(data);
  };

  const readNotification = async (notifId) => {
    try {
      const res = await fetch(`${API_BASE}/ai/notifications/${notifId}/read`, { method: 'POST' });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchNotifications();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        setNotifications(prev => prev.map(n => n.id === notifId ? { ...n, is_read: true } : n));
      } else {
        showToast("❌ Failed to mark notification as read.");
      }
    }
  };

  // Agent Activities API
  const fetchAgentActivities = async () => {
    const res = await fetch(`${API_BASE}/ai/agents/activity`);
    if (!res.ok) {
      throw new Error(`Agent activities fetch failed: status ${res.status}`);
    }
    const data = await res.json();
    setAgentActivities(data);
  };

  // Calendar Sync API
  const fetchCalendarEvents = async () => {
    const res = await fetch(`${API_BASE}/schedule/events`);
    if (!res.ok) {
      throw new Error(`Calendar events fetch failed: status ${res.status}`);
    }
    const data = await res.json();
    setCalendarEvents(data);
  };

  const addCalendarEvent = async (eventData) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/schedule/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventData)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchCalendarEvents();
      await fetchSchedule();
      await fetchTasks();
      await fetchHealthStats();
      await fetchAgentActivities();
    } catch (err) {
      console.error(err);
      showToast("❌ Failed to add calendar event.");
    } finally {
      setIsLoading(false);
    }
  };

  const deleteCalendarEvent = async (eventId) => {
    try {
      const res = await fetch(`${API_BASE}/schedule/events/${eventId}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchCalendarEvents();
      await fetchSchedule();
      await fetchTasks();
      await fetchHealthStats();
      await fetchAgentActivities();
    } catch (err) {
      console.error(err);
      showToast("❌ Failed to delete calendar event.");
    }
  };

  const updateCalendarEvent = async (eventId, eventData) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/schedule/events/${eventId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventData)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchCalendarEvents();
      await fetchSchedule();
      await fetchTasks();
      await fetchHealthStats();
      await fetchAgentActivities();
    } catch (err) {
      console.error(err);
      showToast("❌ Failed to update calendar event.");
    } finally {
      setIsLoading(false);
    }
  };

  const syncGoogleCalendar = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/schedule/sync-google-calendar`, {
        method: 'POST'
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchCalendarEvents();
      await fetchSchedule();
      await fetchTasks();
      await fetchUserSettings();
      await fetchAgentActivities();
      triggerBrowserNotification("Google Calendar Synced", "Conflicts resolved, and focus blocks mapped successfully.");
    } catch (err) {
      console.error(err);
      showToast("❌ Failed to sync Google Calendar.");
    } finally {
      setIsLoading(false);
    }
  };

  // Negotiation API
  const fetchEmailDrafts = async () => {
    const res = await fetch(`${API_BASE}/negotiation/drafts`);
    if (!res.ok) {
      throw new Error(`Email drafts fetch failed: status ${res.status}`);
    }
    const data = await res.json();
    setEmailDrafts(data);
  };

  const updateEmailDraft = async (draftId, draftData) => {
    try {
      const res = await fetch(`${API_BASE}/negotiation/drafts/${draftId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draftData)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchEmailDrafts();
    } catch (err) {
      console.error(err);
      showToast("❌ Failed to update email draft.");
    }
  };

  const sendEmailDraft = async (draftId) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/negotiation/send/${draftId}`, {
        method: 'POST'
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchEmailDrafts();
      await fetchNotifications();
      await fetchAgentActivities();
      triggerBrowserNotification("Email Sent", "Your deadline negotiation request has been pushed.");
    } catch (err) {
      console.error(err);
      showToast("❌ Failed to send email draft.");
    } finally {
      setIsLoading(false);
    }
  };

  const deleteEmailDraft = async (draftId) => {
    try {
      const res = await fetch(`${API_BASE}/negotiation/drafts/${draftId}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchEmailDrafts();
    } catch (err) {
      console.error(err);
      showToast("❌ Failed to delete email draft.");
    }
  };

  // Analytics & Health API
  const fetchAnalyticsData = async () => {
    const res = await fetch(`${API_BASE}/ai/analytics/dashboard`);
    if (!res.ok) {
      throw new Error(`Analytics data fetch failed: status ${res.status}`);
    }
    const data = await res.json();
    setAnalyticsData(data);
  };

  const fetchHealthStats = async () => {
    const res = await fetch(`${API_BASE}/ai/health-analysis`);
    if (!res.ok) {
      throw new Error(`Health stats fetch failed: status ${res.status}`);
    }
    const data = await res.json();
    setHealthStats(data);
  };

  // Habits Logic
  const fetchHabits = async () => {
    const res = await fetch(`${API_BASE}/habits/`);
    if (!res.ok) throw new Error("Habits fetch failed");
    const data = await res.json();
    setHabits(data);
  };

  const addHabit = async (habitData) => {
    try {
      const res = await fetch(`${API_BASE}/habits/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(habitData)
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchHabits();
      await fetchHealthStats();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        const mockHabit = { id: Date.now(), title: habitData.title, frequency: habitData.frequency, streak: 0, logs: [] };
        setHabits(prev => [...prev, mockHabit]);
        showToast("✓ Created habit offline (saved locally)");
      } else {
        showToast("❌ Failed to create habit.");
      }
    }
  };

  const logHabit = async (habitId) => {
    const todayStr = new Date().toISOString().split('T')[0];
    try {
      const res = await fetch(`${API_BASE}/habits/${habitId}/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed_date: todayStr })
      });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchHabits();
      await fetchAnalyticsData();
      await fetchHealthStats();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        setHabits(prev => prev.map(h => {
          if (h.id === habitId) {
            return {
              ...h,
              streak: h.streak + 1,
              last_completed_date: todayStr
            };
          }
          return h;
        }));
      } else {
        showToast("❌ Failed to log habit.");
      }
    }
  };

  const deleteHabit = async (habitId) => {
    try {
      const res = await fetch(`${API_BASE}/habits/${habitId}`, { method: 'DELETE' });
      if (!res.ok) {
        throw new Error(`Server returned status ${res.status}`);
      }
      await fetchHabits();
      await fetchHealthStats();
    } catch (err) {
      console.error(err);
      if (!apiHealth) {
        setHabits(prev => prev.filter(h => h.id !== habitId));
      } else {
        showToast("❌ Failed to delete habit.");
      }
    }
  };

  // Schedule logic
  const fetchSchedule = async () => {
    const res = await fetch(`${API_BASE}/schedule/`);
    if (!res.ok) throw new Error("Schedule fetch failed");
    const data = await res.json();
    setSchedule(data);
  };

  const autoPlanSchedule = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/schedule/auto-plan`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setSchedule(data);
        await fetchHealthStats();
        await fetchAgentActivities();
        triggerBrowserNotification("Auto-Scheduler Complete", "We have structured Pomodoro blocks on your calendar to maximize task success!");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  // Recommendations Logic
  const fetchRecommendations = async () => {
    const res = await fetch(`${API_BASE}/ai/recommendations`);
    if (!res.ok) throw new Error("Recommendations fetch failed");
    const data = await res.json();
    setRecommendations(data);
  };

  const dismissRecommendation = async (recId) => {
    try {
      await fetch(`${API_BASE}/ai/recommendations/${recId}/dismiss`, { method: 'POST' });
      setRecommendations(prev => prev.filter(r => r.id !== recId));
    } catch (err) {
      console.error(err);
      setRecommendations(prev => prev.filter(r => r.id !== recId));
    }
  };

  // Chat message submission
  const sendChatMessage = async (text) => {
    const userMsg = { sender: 'user', text, timestamp: new Date() };
    setChatHistory(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          chat_history: chatHistory
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        const aiMsg = { sender: 'ai', text: data.response, timestamp: new Date() };
        setChatHistory(prev => [...prev, aiMsg]);
        
        // Execute actions suggested by AI BEFORE refreshing state
        if (data.action_suggested === 'create_task' && data.parsed_data) {
          try {
            const taskRes = await fetch(`${API_BASE}/tasks/`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(data.parsed_data)
            });
            if (taskRes.ok) {
              showToast(`✓ Task "${data.parsed_data.title}" created successfully!`);
            } else {
              console.error("Task creation failed:", await taskRes.text());
              showToast(`❌ Failed to create task. Please try using the New Task form.`);
            }
          } catch (taskErr) {
            console.error("Task creation error:", taskErr);
            showToast(`❌ Network error creating task. Please try again.`);
          }
        } else if (data.action_suggested === 'rescue_task' && data.parsed_data) {
          const titleToRescue = data.parsed_data.task_title || '';
          const match = tasks.find(t => t.title.toLowerCase().includes(titleToRescue.toLowerCase()));
          if (match) {
            await rescueTask(match.id);
          }
        }

        // Refresh all data AFTER actions complete
        await fetchTasks();
        await fetchSchedule();
        await fetchHealthStats();
        await fetchAgentActivities();
        await fetchNotifications();
        await fetchEmailDrafts();
      }
    } catch (err) {
      console.error(err);
      setTimeout(() => {
        setChatHistory(prev => [...prev, {
          sender: 'ai',
          text: "I'm running in local mode right now. I can log your tasks or start Pomodoros to keep you working!",
          timestamp: new Date()
        }]);
      }, 1000);
    } finally {
      setIsLoading(false);
    }
  };

  // Notification helper
  const triggerBrowserNotification = (title, message) => {
    if (Notification.permission === 'granted') {
      new Notification(title, { body: message });
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          new Notification(title, { body: message });
        }
      });
    }
  };

  return (
    <AppContext.Provider value={{
      activeTab,
      setActiveTab,
      tasks,
      habits,
      schedule,
      recommendations,
      chatHistory,
      isLoading,
      apiHealth,
      addTask,
      updateTask,
      deleteTask,
      rescueTask,
      logTaskFocus,
      toggleSubtask,
      addHabit,
      logHabit,
      deleteHabit,
      autoPlanSchedule,
      dismissRecommendation,
      sendChatMessage,
      focusTask,
      setFocusTask,
      timerMinutes,
      setTimerMinutes,
      timerSeconds,
      setTimerSeconds,
      timerIsRunning,
      setTimerIsRunning,
      timerMode,
      setTimerMode,
      triggerBrowserNotification,
      
      // Extended states & methods
      userSettings,
      updateUserSettings,
      emailDrafts,
      sendEmailDraft,
      updateEmailDraft,
      deleteEmailDraft,
      notifications,
      readNotification,
      agentActivities,
      calendarEvents,
      addCalendarEvent,
      updateCalendarEvent,
      deleteCalendarEvent,
      syncGoogleCalendar,
      analyticsData,
      healthStats,
      demoLoginMode,
      setDemoLoginMode,
      demoScenario,
      seedDemoData,
      toastMessage,
      setToastMessage
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => useContext(AppContext);
