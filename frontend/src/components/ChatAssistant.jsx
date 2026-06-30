import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { Mic, Send, Bot, User, Sparkles, AlertCircle } from 'lucide-react';

const ChatAssistant = () => {
  const { chatHistory, sendChatMessage, isLoading } = useApp();
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [micSupported, setMicSupported] = useState(true);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Initialize Speech Recognition API
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMicSupported(false);
      return;
    }
    
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'en-US';

    rec.onstart = () => {
      setIsListening(true);
    };

    rec.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setInput(transcript);
      // Auto-submit after voice transcription — no manual send needed
      setTimeout(() => {
        if (transcript.trim()) {
          sendChatMessage(transcript);
          setInput('');
        }
      }, 300);
    };

    rec.onerror = (e) => {
      console.error("Speech Recognition Error:", e);
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = rec;
  }, []);

  // Speak the last AI response if TTS is enabled
  useEffect(() => {
    if (!ttsEnabled || chatHistory.length === 0) return;
    const lastMsg = chatHistory[chatHistory.length - 1];
    if (lastMsg.sender === 'ai') {
      window.speechSynthesis?.cancel();
      const utterance = new SpeechSynthesisUtterance(lastMsg.text);
      window.speechSynthesis?.speak(utterance);
    }
  }, [chatHistory, ttsEnabled]);

  // Clean up any ongoing TTS speech on unmount
  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendChatMessage(input);
    setInput('');
  };

  const toggleVoiceListen = () => {
    if (!micSupported) return;
    
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }
  };

  const formatMessageTime = (timeInput) => {
    const date = new Date(timeInput);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="chat-container glass-card">
      <header className="chat-header">
        <div className="chat-header-info">
          <Bot size={22} className="text-cyan animate-pulse" />
          <div>
            <h3>Command Center</h3>
            <p className="subtitle">Speak or type prompts to manage tasks, schedules & trigger rescues.</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            type="button"
            onClick={() => {
              const nextVal = !ttsEnabled;
              setTtsEnabled(nextVal);
              if (!nextVal) {
                window.speechSynthesis?.cancel();
              }
            }}
            className={`btn btn-sm ${ttsEnabled ? 'btn-accent' : 'btn-muted'}`}
            style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
          >
            {ttsEnabled ? "🔊 Voice Feed Active" : "🔇 Voice Feed Muted"}
          </button>
          {!micSupported && (
            <div className="mic-warning" style={{ fontSize: '0.75rem' }}>
              <AlertCircle size={14} /> <span>Voice Input Unavailable</span>
            </div>
          )}
        </div>
      </header>

      {/* Messages Viewport */}
      <div className="chat-messages-viewport">
        {chatHistory.map((msg, idx) => {
          const isAI = msg.sender === 'ai';
          return (
            <div key={idx} className={`chat-message-wrapper ${isAI ? 'msg-ai' : 'msg-user'}`}>
              <div className="msg-avatar">
                {isAI ? <Bot size={16} /> : <User size={16} />}
              </div>
              <div className="msg-bubble-container">
                <div className="msg-bubble">
                  <p>{msg.text}</p>
                </div>
                <span className="msg-time">{formatMessageTime(msg.timestamp)}</span>
              </div>
            </div>
          );
        })}
        {isLoading && (
          <div className="chat-message-wrapper msg-ai">
            <div className="msg-avatar animate-pulse">
              <Bot size={16} />
            </div>
            <div className="msg-bubble-container">
              <div className="msg-bubble loading-dots">
                <span>.</span><span>.</span><span>.</span>
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Suggestion Prompts */}
      <div className="chat-suggestions">
        <div className="suggestion-pill" onClick={() => setInput("Add an urgent task to study deep learning by tomorrow")}>
          ✨ "Add urgent task to study..."
        </div>
        <div className="suggestion-pill" onClick={() => setInput("Auto plan my day")}>
          📅 "Auto plan my day"
        </div>
        <div className="suggestion-pill" onClick={() => setInput("Recommend some productivity habits")}>
          💡 "Recommend productivity habits"
        </div>
      </div>

      {/* Message Input Bar */}
      <form onSubmit={handleSend} className="chat-input-bar">
        <input 
          type="text" 
          value={input} 
          onChange={e => setInput(e.target.value)} 
          placeholder="Speak or type a command (e.g. 'Add urgent task: submit taxes tomorrow 5 PM')..." 
          disabled={isLoading}
        />
        
        {micSupported && (
          <button 
            type="button" 
            onClick={toggleVoiceListen}
            className={`mic-btn ${isListening ? 'mic-listening' : ''}`}
            title={isListening ? "Listening... click to stop" : "Start Voice Assistance"}
          >
            {isListening ? (
              <div className="voice-wave-container">
                <span className="wave-line"></span>
                <span className="wave-line"></span>
                <span className="wave-line"></span>
              </div>
            ) : (
              <Mic size={18} />
            )}
          </button>
        )}

        <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
          <Send size={18} />
        </button>
      </form>
    </div>
  );
};

export default ChatAssistant;
