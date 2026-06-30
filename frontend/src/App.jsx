import React, { useState } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Menu } from 'lucide-react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import TaskManager from './components/TaskManager';
import CalendarView from './components/CalendarView';
import HabitTracker from './components/HabitTracker';
import ChatAssistant from './components/ChatAssistant';
import NegotiationHub from './components/NegotiationHub';
import AnalyticsHub from './components/AnalyticsHub';
import './App.css';

const MainAppLayout = () => {
  const { activeTab, isLoading, toastMessage } = useApp();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
 
  const renderActiveTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'tasks':
        return <TaskManager />;
      case 'calendar':
        return <CalendarView />;
      case 'habits':
        return <HabitTracker />;
      case 'negotiation':
        return <NegotiationHub />;
      case 'analytics':
        return <AnalyticsHub />;
      case 'chat':
        return <ChatAssistant />;
      default:
        return <Dashboard />;
    }
  };
 
  return (
    <div className="app-wrapper">
      {/* Mobile Top Header */}
      <header className="mobile-topbar glass-card">
        <button 
          className="mobile-menu-trigger" 
          onClick={() => setIsMobileMenuOpen(true)}
          aria-label="Open Menu"
        >
          <Menu size={24} />
        </button>
        <div className="mobile-brand">
          <span className="brand-logo">🚨</span>
          <span className="brand-name">Life Saver</span>
        </div>
      </header>

      {/* Sidebar Drawer Wrap */}
      <div className={`sidebar-drawer-container ${isMobileMenuOpen ? 'mobile-open' : ''}`}>
        {isMobileMenuOpen && (
          <div className="sidebar-backdrop" onClick={() => setIsMobileMenuOpen(false)} />
        )}
        <Sidebar onCloseMenu={() => setIsMobileMenuOpen(false)} />
      </div>

      <main className="content-area">
        {renderActiveTab()}
      </main>
 
      {toastMessage && (
        <div className="custom-toast glass-card animate-slide-in-right">
          <div className="toast-body">
            <span className="toast-pulse-dot"></span>
            <span className="toast-text">{toastMessage}</span>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="global-loader-overlay">
          <div className="loader-scanner">
            <span className="loader-sweep"></span>
          </div>
          <p>Synchronizing AI Matrices...</p>
        </div>
      )}
    </div>
  );
};

function App() {
  return (
    <AppProvider>
      <MainAppLayout />
    </AppProvider>
  );
}

export default App;
