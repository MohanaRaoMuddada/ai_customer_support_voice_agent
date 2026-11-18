/**
 * App.jsx — AI Customer Support Chat Interface
 * =============================================
 *
 * ARCHITECTURE:
 * -------------
 * This component implements a minimal, single-file chat interface with both
 * text and voice input capabilities. All voice handling is done inline (no
 * separate VoiceButton component) using the browser's MediaRecorder API.
 *
 * VOICE PIPELINE (frontend side):
 * ---------------------------------
 *   recordAudio()         → requests mic permission, starts MediaRecorder
 *   stopRecording()       → stops MediaRecorder, collects audio chunks
 *   sendAudio(blob)       → POST /voice (multipart/form-data)
 *                           ↓
 *                         Gets ChatResponse JSON (transcription → agent → response)
 *                           ↓
 *   speakResponse(text)   → window.speechSynthesis (Browser SpeechSynthesis API)
 *
 * TEXT PIPELINE:
 * ---------------
 *   handleSendMessage(text) → POST /chat (JSON)
 *                              ↓
 *                            Gets ChatResponse JSON
 *                              ↓
 *   speakResponse(text)    → window.speechSynthesis
 *
 * DESIGN DECISIONS:
 * -----------------
 * - No Redux: all state is local useState hooks
 * - No authentication UI
 * - No external TTS: only window.speechSynthesis
 * - MediaRecorder preferred over Web Speech API: audio goes to backend (Groq
 *   Whisper), not processed in the browser, matching the backend architecture
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import {
  Send, Bot, User, Trash2, RefreshCw, MessageSquare, ShieldAlert,
  Sparkles, BookOpen, Mic, Square, Settings, ChevronDown, LogOut,
  RotateCcw, FileText, RotateCw, MapPin, XCircle, Plus,
  Clock, FileSearch, SlidersHorizontal
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────

const API_BASE = 'http://localhost:8000';

// ─────────────────────────────────────────────────────────────────────────────
// MicButton — inline component (no separate file, no Browser SpeechRecognition)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * MicButton component handles the complete audio recording lifecycle:
 *   1. Request microphone permission via getUserMedia()
 *   2. Instantiate MediaRecorder and collect audio chunks
 *   3. On stop: assemble Blob and invoke onAudioReady callback
 *
 * This approach uses the browser's MediaRecorder API (not the Web Speech API).
 * The recorded audio blob is sent to POST /voice for server-side Groq Whisper
 * transcription — which is the correct architecture for a backend portfolio project.
 *
 * Props:
 *   onAudioReady  (function) : called with the final audio Blob when recording stops
 *   disabled      (boolean)  : disables the button (e.g., while a request is loading)
 */
function MicButton({ onAudioReady, disabled }) {
  // isRecording: true while MediaRecorder is actively capturing audio
  const [isRecording, setIsRecording] = useState(false);
  // micStatus: user-facing status message shown next to the button
  const [micStatus, setMicStatus] = useState('Click to speak');

  // Refs persist across renders without triggering re-renders
  const mediaRecorderRef = useRef(null);  // MediaRecorder instance
  const audioChunksRef   = useRef([]);    // Collected audio data chunks
  const streamRef        = useRef(null);  // MediaStream (for cleanup)

  // Cleanup: stop microphone stream when component unmounts
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  // ── recordAudio: start microphone capture ─────────────────────────────────
  const recordAudio = async () => {
    // Guard: already recording
    if (isRecording) return;

    try {
      // Request microphone access — browser prompts user for permission
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Clear any previous audio chunks
      audioChunksRef.current = [];

      // Instantiate MediaRecorder with the live audio stream
      // Prefer audio/webm (Chrome default) which Groq Whisper supports natively
      const options = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? { mimeType: 'audio/webm;codecs=opus' }
        : {};
      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;

      // Collect audio data as it arrives from the microphone
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // When recording stops: assemble chunks into a Blob and fire callback
      recorder.onstop = () => {
        const mimeType = recorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

        // Stop all microphone tracks to release the hardware
        stream.getTracks().forEach(track => track.stop());
        streamRef.current = null;

        setIsRecording(false);
        setMicStatus('Click to speak');

        // Hand off the blob to the parent (App) for upload
        if (onAudioReady) {
          onAudioReady(audioBlob);
        }
      };

      recorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        setIsRecording(false);
        setMicStatus('Recording error — try again');
        stream.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      };

      // Start recording; request data every 250ms for smoother collection
      recorder.start(250);
      setIsRecording(true);
      setMicStatus('Recording… click again to stop');

    } catch (err) {
      // Handle microphone permission denial and other getUserMedia errors
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setMicStatus('Microphone permission denied');
      } else if (err.name === 'NotFoundError') {
        setMicStatus('No microphone found');
      } else {
        setMicStatus('Could not access microphone');
      }
      console.error('getUserMedia error:', err);
    }
  };

  // ── stopRecording: halt capture and trigger onstop ────────────────────────
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      // onstop handler fires asynchronously after stop()
    }
  };

  // ── toggleMic: single button toggles record/stop ──────────────────────────
  const toggleMic = () => {
    if (disabled) return;
    if (isRecording) {
      stopRecording();
    } else {
      recordAudio();
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      {/* Microphone button */}
      <button
        id="voice-mic-button"
        type="button"
        onClick={toggleMic}
        disabled={disabled}
        title={micStatus}
        style={{
          background: isRecording ? 'rgba(244, 63, 94, 0.15)' : 'rgba(255, 255, 255, 0.05)',
          border: '1px solid',
          borderColor: isRecording ? 'var(--status-error)' : 'var(--panel-border)',
          borderRadius: 'var(--radius-md)',
          color: isRecording ? 'var(--status-error)' : 'var(--text-muted)',
          width: '38px',
          height: '38px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: disabled ? 'not-allowed' : 'pointer',
          transition: 'all var(--transition-fast)',
          position: 'relative',
          flexShrink: 0,
        }}
      >
        {/* Pulsing ring indicator when recording is active */}
        {isRecording && (
          <span
            style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              borderRadius: 'var(--radius-md)',
              border: '2px solid var(--status-error)',
              animation: 'pulse-ring 1.5s infinite ease-in-out',
              opacity: 0.6,
            }}
          />
        )}
        {/* Icon: Stop square when recording, Mic when idle */}
        {isRecording ? <Square size={16} fill="currentColor" /> : <Mic size={18} />}
      </button>

      {/* Status label */}
      <span
        id="voice-mic-status"
        style={{
          fontSize: '0.78rem',
          color: isRecording ? 'var(--status-error)' : 'var(--text-muted)',
          fontWeight: isRecording ? '600' : '400',
          transition: 'color var(--transition-fast)',
          whiteSpace: 'nowrap',
        }}
      >
        {micStatus}
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SIDEBAR SUB-COMPONENTS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * SidebarHeader — Brand identity + compact new-chat trigger
 */
function SidebarHeader({ onNewChat }) {
  return (
    <div className="sb-header">
      <div className="sb-brand">
        <div className="sb-brand-icon">
          <Sparkles size={13} />
        </div>
        <div className="sb-brand-text">
          <span className="sb-brand-name">AI Support</span>
          <span className="sb-brand-sub">Customer Assistant</span>
        </div>
      </div>
      <button className="sb-new-chat-btn" onClick={onNewChat} title="New conversation">
        <Plus size={13} />
        New Chat
      </button>
    </div>
  );
}

// Quick action data — purely presentational
const QUICK_ACTIONS = [
  { id: 'refund',   label: 'Refund Policy',       icon: RotateCcw,   msg: 'What is the refund policy?' },
  { id: 'shipping', label: 'Shipping Information', icon: MapPin,      msg: 'What are the shipping options and delivery times?' },
  { id: 'order',    label: 'Order Status',         icon: FileSearch,  msg: 'How can I check my order status?' },
  { id: 'track',    label: 'Track Order',          icon: RotateCw,    msg: 'How do I track my order?' },
  { id: 'cancel',   label: 'Cancel Order',         icon: XCircle,     msg: 'How do I cancel my order?' },
];

/**
 * QuickActions — Vertical list of shortcut prompts with icon + label
 * Props:
 *   onSelect (fn) : fires the quick message into the chat
 */
function QuickActions({ onSelect }) {
  const [activeId, setActiveId] = useState(null);

  const handleClick = (action) => {
    setActiveId(action.id);
    onSelect(action.msg);
  };

  return (
    <div className="sb-section">
      <p className="sb-section-title">Quick Actions</p>
      <ul className="sb-list" role="list">
        {QUICK_ACTIONS.map((action) => {
          const Icon = action.icon;
          return (
            <li key={action.id}>
              <button
                className={`sb-list-item${activeId === action.id ? ' sb-active' : ''}`}
                onClick={() => handleClick(action)}
                title={action.label}
              >
                <span className="sb-item-icon"><Icon size={13} /></span>
                <span className="sb-item-label">{action.label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// Knowledge base document list — presentational data
const KNOWLEDGE_DOCS = [
  { id: 'policy',  name: 'Company Policy.pdf',  meta: '24 KB · Updated today' },
  { id: 'faq',     name: 'FAQ.pdf',              meta: '12 KB · Updated 3 days ago' },
  { id: 'manual',  name: 'Product Manual.pdf',   meta: '140 KB · Updated last week' },
];

/**
 * KnowledgeSection — Compact document reference list
 */
function KnowledgeSection() {
  return (
    <div className="sb-section">
      <p className="sb-section-title">Knowledge</p>
      <ul className="sb-list" role="list">
        {KNOWLEDGE_DOCS.map((doc) => (
          <li key={doc.id}>
            <button className="sb-list-item sb-doc-item" title={doc.name}>
              <span className="sb-item-icon sb-doc-icon"><FileText size={13} /></span>
              <span className="sb-doc-text">
                <span className="sb-item-label">{doc.name}</span>
                <span className="sb-doc-meta">{doc.meta}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Recent chat data — presentational
const RECENT_CHATS = [
  { id: 'c1', label: 'Refund for Order #102',     time: '2m ago',   active: true  },
  { id: 'c2', label: 'Shipping Query',             time: '1h ago',   active: false },
  { id: 'c3', label: 'Delivery Address Update',    time: 'Yesterday', active: false },
  { id: 'c4', label: 'Track Order #89',            time: '3d ago',   active: false },
];

/**
 * RecentChats — Scrollable conversation history list
 */
function RecentChats() {
  const [activeId, setActiveId] = useState('c1');

  return (
    <div className="sb-section sb-recent-chats">
      <p className="sb-section-title">Recent Chats</p>
      <ul className="sb-list sb-chats-list" role="list">
        {RECENT_CHATS.map((chat) => (
          <li key={chat.id}>
            <button
              className={`sb-list-item sb-chat-item${activeId === chat.id ? ' sb-active' : ''}`}
              onClick={() => setActiveId(chat.id)}
              title={chat.label}
            >
              <span className="sb-item-icon"><MessageSquare size={12} /></span>
              <span className="sb-item-label">{chat.label}</span>
              <span className="sb-chat-time">{chat.time}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * SidebarFooter — User identity + settings icon
 * Props:
 *   onSettingsClick (fn) : optional handler (UI only)
 */
function SidebarFooter({ onSettingsClick }) {
  return (
    <div className="sb-footer">
      <div className="sb-footer-inner">
        <div className="sb-avatar">M</div>
        <div className="sb-user-text">
          <span className="sb-user-name">Mohan</span>
          <span className="sb-user-role">Customer</span>
        </div>
        <button
          className="sb-settings-btn"
          onClick={onSettingsClick}
          title="Settings"
          aria-label="Settings"
        >
          <Settings size={14} />
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// App — Main Component
// ─────────────────────────────────────────────────────────────────────────────

function App() {
  // messages: array of { id, text, sender ('user'|'bot'), time, sources }
  const [messages, setMessages] = useState([]);
  // inputValue: current text typed in the input box
  const [inputValue, setInputValue] = useState('');
  // isLoading: true while a /chat or /voice request is in flight
  const [isLoading, setIsLoading] = useState(false);
  // error: string shown in the error banner, null to hide
  const [error, setError] = useState(null);
  // sessionId: random identifier for this conversation session
  const [sessionId, setSessionId] = useState('');

  // Ref to scroll to the bottom of the messages list
  const messagesEndRef = useRef(null);

  // Generate a session ID on mount and set up SpeechSynthesis cleanup
  useEffect(() => {
    const id = 'session_' + Math.random().toString(36).substring(2, 9);
    setSessionId(id);
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Auto-scroll to the newest message whenever the list updates
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading]);

  // ── speakResponse: Browser SpeechSynthesis API ────────────────────────────
  /**
   * Convert the AI text response to audible speech using the browser's built-in
   * SpeechSynthesis API. This is the ONLY voice output mechanism — no external
   * TTS APIs are used.
   *
   * SpeechSynthesisUtterance configuration:
   *   lang  : 'en-US'  — English (United States) language model
   *   rate  : 1.0      — normal speaking speed
   *   pitch : 1.0      — natural pitch
   */
  const speakResponse = useCallback((text) => {
    if (!('speechSynthesis' in window)) {
      console.warn('SpeechSynthesis is not supported in this browser.');
      return;
    }
    // Cancel any ongoing speech before starting a new utterance
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  }, []);

  // ── appendMessage: add a message object to the conversation ───────────────
  const appendMessage = useCallback((text, sender, sources = []) => {
    const msg = {
      id: Date.now() + Math.random(),
      text,
      sender,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      sources,
    };
    setMessages(prev => [...prev, msg]);
    return msg;
  }, []);

  // ── handleSendMessage: POST /chat with text input ─────────────────────────
  /**
   * displayMessages() is handled by the JSX render loop below.
   * This function covers the text input → /chat → response → speak pipeline.
   */
  const handleSendMessage = async (textToSend) => {
    const trimmed = textToSend.trim();
    if (!trimmed) return;

    appendMessage(trimmed, 'user');
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE}/chat`, {
        message: trimmed,
        session_id: sessionId,
        language: 'en',
      });

      const botText = response.data.response || '';
      const botSources = response.data.sources || [];

      appendMessage(botText, 'bot', botSources);
      speakResponse(botText);

    } catch (err) {
      console.error('Chat request failed:', err);
      setError(
        err.response?.data?.detail ||
        'Failed to reach the support agent. Is the backend running on port 8000?'
      );
    } finally {
      setIsLoading(false);
    }
  };

  // ── sendAudio: POST /voice with recorded audio blob ───────────────────────
  /**
   * Called by MicButton's onAudioReady callback with the recorded Blob.
   *
   * Flow:
   *   1. Show "Voice message" placeholder in the chat (user side)
   *   2. POST audio as multipart/form-data to /voice
   *   3. The backend transcribes via Groq Whisper, runs the agent, returns ChatResponse
   *   4. Display and speak the AI response
   *   5. Update the placeholder with the actual transcription (if known)
   */
  const sendAudio = async (audioBlob) => {
    if (!audioBlob || audioBlob.size === 0) {
      setError('The recording was empty. Please try speaking again.');
      return;
    }

    // Show a user-side placeholder while processing
    appendMessage('🎙️ Voice message sent…', 'user');
    setIsLoading(true);
    setError(null);

    try {
      // Build a FormData payload — FastAPI reads this as UploadFile
      const formData = new FormData();
      // Name the field "audio" to match the FastAPI parameter name
      const extension = audioBlob.type.includes('ogg') ? 'ogg' : 'webm';
      formData.append('audio', audioBlob, `recording.${extension}`);

      const response = await axios.post(`${API_BASE}/voice`, formData, {
        headers: {
          // Axios sets Content-Type automatically with the correct boundary
          // when formData is passed — do NOT set it manually here.
        },
        timeout: 30000, // 30 second timeout for Whisper + agent round-trip
      });

      const botText = response.data.response || '';
      const botSources = response.data.sources || [];

      appendMessage(botText, 'bot', botSources);
      speakResponse(botText);

    } catch (err) {
      console.error('Voice request failed:', err);

      // Surface Whisper-specific error messages from the backend
      const detail = err.response?.data?.detail;
      if (detail) {
        setError(detail);
      } else if (err.code === 'ECONNABORTED') {
        setError('Voice request timed out. Please try again or type your question.');
      } else {
        setError('Voice processing failed. Please try typing your question instead.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // ── handleSubmit: form submit handler for text input ──────────────────────
  const handleSubmit = (e) => {
    e.preventDefault();
    handleSendMessage(inputValue);
  };

  // ── handleResetChat: clear conversation and generate new session ──────────
  const handleResetChat = () => {
    setMessages([]);
    setError(null);
    setInputValue('');
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setSessionId('session_' + Math.random().toString(36).substring(2, 9));
  };

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER — displayMessages() is the JSX message map below
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="app-container">

      {/* ── Sidebar ──────────────────────────────────────────────── */}
      <aside className="sidebar">
        <SidebarHeader onNewChat={handleResetChat} />

        {/* Scrollable middle zone containing all content sections */}
        <div className="sb-scroll-area">
          <QuickActions onSelect={handleSendMessage} />
          <div className="sb-divider" />
          <KnowledgeSection />
          <div className="sb-divider" />
          <RecentChats />
        </div>

        <SidebarFooter />
      </aside>

      {/* ── Main Chat Panel ──────────────────────────────────────────────── */}
      <main className="chat-panel">

        {/* Chat Header */}
        <header className="chat-header">
          <div className="bot-info">
            <div className="bot-avatar-wrapper">
              <div className="bot-avatar"><Bot size={22} /></div>
              <span className="status-indicator"></span>
            </div>
            <div className="bot-details">
              <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>AI Support Agent</span>
              <span className="bot-status">Active Online</span>
            </div>
          </div>
          <div className="header-actions">
            <button onClick={handleResetChat} className="action-button" title="Clear Conversation">
              <Trash2 size={18} />
            </button>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="error-banner">
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={18} />
              {error}
            </span>
            <button onClick={() => setError(null)}>&times;</button>
          </div>
        )}

        {/* ── Messages Container — displayMessages() ──────────────────── */}
        <div className="messages-container">

          {/* Welcome screen shown when no messages exist */}
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-logo"><Bot size={32} /></div>
              <h3>How can I help you today?</h3>
              <p>
                Ask me about orders, refund policies, shipping, or any support question.
                Use the <strong>microphone button</strong> to speak, or type below.
              </p>
              <div className="welcome-suggestions">
                <div onClick={() => handleSendMessage('What is the refund policy?')} className="suggestion-card">
                  <span>What is the refund policy?</span>
                  <span className="arrow">&rarr;</span>
                </div>
                <div onClick={() => handleSendMessage('Check order status for order ID 1002')} className="suggestion-card">
                  <span>Check order status for order ID 1002</span>
                  <span className="arrow">&rarr;</span>
                </div>
              </div>
            </div>
          ) : (
            /* Map over messages to render conversation bubbles */
            messages.map((msg) => (
              <div
                key={msg.id}
                className={`message-row ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}
              >
                <div className="message-bubble">
                  <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{msg.text}</p>

                  {/* Sources section — shown on bot messages that used RAG */}
                  {msg.sender === 'bot' && msg.sources && msg.sources.length > 0 && (
                    <div className="sources-list">
                      <span className="sources-title">
                        <BookOpen size={12} /> References:
                      </span>
                      <div className="sources-tags">
                        {msg.sources.map((src, idx) => (
                          <span key={idx} className="source-tag">{src}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <span className="message-time">{msg.time}</span>
                </div>
              </div>
            ))
          )}

          {/* Typing indicator shown while a request is in flight */}
          {isLoading && (
            <div className="message-row bot-message">
              <div className="message-bubble">
                <div className="typing-bubble">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Input Panel ─────────────────────────────────────────────── */}
        <div className="input-panel">
          <form onSubmit={handleSubmit} className="input-container">

            {/* MicButton — MediaRecorder-based voice input */}
            <MicButton onAudioReady={sendAudio} disabled={isLoading} />

            {/* Text input */}
            <input
              id="chat-text-input"
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your question or click the mic to speak…"
              className="chat-input"
              disabled={isLoading}
              autoFocus
            />

            {/* Send button */}
            <button
              id="chat-send-button"
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="send-button"
            >
              <Send size={16} />
              Send
            </button>
          </form>
        </div>

      </main>
    </div>
  );
}

export default App;
