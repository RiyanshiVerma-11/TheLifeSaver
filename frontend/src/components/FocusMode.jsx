import React, { useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext';
import { Play, Pause, RotateCcw, Volume2, VolumeX, Flame } from 'lucide-react';

const FocusMode = () => {
  const {
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
    logTaskFocus
  } = useApp();

  const [activeSound, setActiveSound] = useState(null); // 'noise', 'rain', 'synth' or null
  const audioContextRef = useRef(null);
  const audioNodesRef = useRef([]);

  // Keep ref of latest state to prevent stale closures in setInterval
  const stateRef = useRef(null);
  stateRef.current = { timerMinutes, timerSeconds, timerIsRunning, timerMode, focusTask };

  // Timer Tick logic
  useEffect(() => {
    let interval = null;
    if (timerIsRunning) {
      interval = setInterval(() => {
        const { timerMinutes: min, timerSeconds: sec } = stateRef.current;
        if (sec > 0) {
          setTimerSeconds(sec - 1);
        } else if (sec === 0) {
          if (min === 0) {
            handleTimerExpiry();
          } else {
            setTimerMinutes(min - 1);
            setTimerSeconds(59);
          }
        }
      }, 1000);
    } else {
      clearInterval(interval);
    }
    return () => clearInterval(interval);
  }, [timerIsRunning]);

  const handleTimerExpiry = () => {
    setTimerIsRunning(false);
    const { timerMode: currentMode, focusTask: currentTask } = stateRef.current;
    if (currentMode === 'focus') {
      triggerBrowserNotification("Focus Session Complete!", "Take a well-deserved 5-minute break.");
      if (currentTask) {
        logTaskFocus(currentTask.id, 25);
      }
      setTimerMode('break');
      setTimerMinutes(5);
      setTimerSeconds(0);
    } else {
      triggerBrowserNotification("Break Over!", "Time to get back to focus. Select a task to rescue.");
      setTimerMode('focus');
      setTimerMinutes(25);
      setTimerSeconds(0);
    }
  };

  const toggleTimer = () => {
    setTimerIsRunning(!timerIsRunning);
  };

  const resetTimer = () => {
    setTimerIsRunning(false);
    setTimerMinutes(timerMode === 'focus' ? 25 : 5);
    setTimerSeconds(0);
  };

  // SVG circular progress maths
  const totalSeconds = timerMode === 'focus' ? 25 * 60 : 5 * 60;
  const currentRemaining = timerMinutes * 60 + timerSeconds;
  const progressPct = ((totalSeconds - currentRemaining) / totalSeconds) * 100;
  
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progressPct / 100) * circumference;

  // Web Audio API Synthesizers for Ambient Sounds (SDE 3 Level Offline Audio Synth)
  const startAmbientSound = (type) => {
    // Stop current sounds
    stopAmbientSound();

    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const ctx = new AudioContext();
      audioContextRef.current = ctx;
      
      const bufferSize = ctx.sampleRate * 2;
      const noiseBuffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = noiseBuffer.getChannelData(0);
      
      let lastOut = 0.0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        if (type === 'rain') {
          // Pink/Brown noise filtering for soft rain sound
          output[i] = (lastOut + (0.02 * white)) / 1.02;
          lastOut = output[i];
          output[i] *= 3.5; // Gain compensation
        } else {
          // Pure white noise
          output[i] = white * 0.5;
        }
      }

      const noiseNode = ctx.createBufferSource();
      noiseNode.buffer = noiseBuffer;
      noiseNode.loop = true;

      // Filter settings
      const filter = ctx.createBiquadFilter();
      if (type === 'rain') {
        filter.type = 'lowpass';
        filter.frequency.value = 1000;
      } else if (type === 'noise') {
        filter.type = 'bandpass';
        filter.frequency.value = 800;
        filter.Q.value = 1.0;
      }

      const gain = ctx.createGain();
      gain.gain.value = 0.15; // Soft volume

      if (type === 'synth') {
        // Create Cyber Synth pulsating drones
        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const lfo = ctx.createOscillator();
        const lfoGain = ctx.createGain();
        
        osc1.type = 'sawtooth';
        osc1.frequency.value = 88; // Low F drone
        
        osc2.type = 'triangle';
        osc2.frequency.value = 132.5; // Fifth harmonic

        lfo.frequency.value = 0.2; // Slow pulse LFO (5s period)
        lfoGain.gain.value = 400; // Modulation depth

        const synthFilter = ctx.createBiquadFilter();
        synthFilter.type = 'lowpass';
        synthFilter.frequency.value = 600;
        synthFilter.Q.value = 4.0;

        lfo.connect(lfoGain);
        lfoGain.connect(synthFilter.frequency); // Modulate cut-off
        
        osc1.connect(synthFilter);
        osc2.connect(synthFilter);
        
        const synthGain = ctx.createGain();
        synthGain.gain.value = 0.08;
        
        synthFilter.connect(synthGain);
        synthGain.connect(ctx.destination);
        
        osc1.start();
        osc2.start();
        lfo.start();
        
        audioNodesRef.current = [osc1, osc2, lfo, ctx];
      } else {
        noiseNode.connect(filter);
        filter.connect(gain);
        gain.connect(ctx.destination);
        noiseNode.start();
        
        audioNodesRef.current = [noiseNode, ctx];
      }

      setActiveSound(type);
    } catch (e) {
      console.error("Failed starting Web Audio API synthesizer", e);
    }
  };

  const stopAmbientSound = () => {
    if (audioNodesRef.current.length > 0) {
      audioNodesRef.current.forEach(node => {
        try {
          if (node.stop) node.stop();
        } catch (e) {}
      });
      // Close context
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
      audioNodesRef.current = [];
      audioContextRef.current = null;
    }
    setActiveSound(null);
  };

  const handleSoundToggle = (soundType) => {
    if (activeSound === soundType) {
      stopAmbientSound();
    } else {
      startAmbientSound(soundType);
    }
  };

  useEffect(() => {
    // Cleanup audio nodes on unmount
    return () => {
      stopAmbientSound();
    };
  }, []);

  return (
    <div className={`focus-station glass-card ${timerMode === 'focus' ? 'glow-cyan' : 'glow-purple'}`}>
      <div className="card-header">
        <div className="title-with-spark">
          <Flame size={16} className="text-purple animate-pulse" />
          <h3>Focus Station</h3>
        </div>
        <span className={`timer-badge-mode mode-${timerMode}`}>{timerMode.toUpperCase()}</span>
      </div>

      <div className="timer-display-center">
        {/* SVG Progress Circle */}
        <svg className="timer-svg" width="200" height="200" viewBox="0 0 200 200">
          <circle 
            className="timer-circle-bg" 
            cx="100" 
            cy="100" 
            r={radius} 
          />
          <circle 
            className={`timer-circle-progress ${timerMode === 'focus' ? 'stroke-cyan' : 'stroke-purple'}`}
            cx="100" 
            cy="100" 
            r={radius} 
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform="rotate(-90 100 100)"
          />
        </svg>

        {/* Time Text Overlay */}
        <div className="timer-text">
          <h2>
            {String(timerMinutes).padStart(2, '0')}:{String(timerSeconds).padStart(2, '0')}
          </h2>
          <p>{focusTask ? focusTask.title.substring(0, 16) + "..." : "No Task Loaded"}</p>
        </div>
      </div>

      <div className="timer-controls">
        <button onClick={toggleTimer} className="btn btn-secondary btn-circle" title={timerIsRunning ? "Pause" : "Start"}>
          {timerIsRunning ? <Pause size={18} /> : <Play size={18} />}
        </button>
        <button onClick={resetTimer} className="btn btn-secondary btn-circle" title="Reset">
          <RotateCcw size={18} />
        </button>
      </div>

      {/* Ambient Sound Machine Section */}
      <div className="sound-machine">
        <h4>Ambient Sound Machine</h4>
        <div className="sound-buttons">
          <button 
            onClick={() => handleSoundToggle('rain')}
            className={`sound-btn ${activeSound === 'rain' ? 'active-rain' : ''}`}
          >
            🌧️ Rain
          </button>
          <button 
            onClick={() => handleSoundToggle('noise')}
            className={`sound-btn ${activeSound === 'noise' ? 'active-noise' : ''}`}
          >
            💨 White Noise
          </button>
          <button 
            onClick={() => handleSoundToggle('synth')}
            className={`sound-btn ${activeSound === 'synth' ? 'active-synth' : ''}`}
          >
            👾 Cyber Synth
          </button>
        </div>
        {activeSound && (
          <div className="audio-status">
            <Volume2 size={12} className="animate-pulse text-cyan" />
            <span>Generating ambient {activeSound} audio...</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default FocusMode;
