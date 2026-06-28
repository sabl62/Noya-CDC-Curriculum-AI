import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  CirclePlus,
  Clock3,
  LogOut,
  Menu,
  MoonStar,
  PanelLeftClose,
  PenLine,
  Send,
  Sparkles,
  SunMedium,
  UserRound,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { API_URL, chatAPI } from "../services/api";
import { useAuth } from "../context/AuthContext.jsx";
import { findSubject } from "../data/curriculum.js";
import MarkdownRenderer from "./MarkdownRenderer.jsx";
import noyaLogo from "../assets/noya-logo.svg";

const quickPrompts = [
  "Explain this simply",
  "Give me exam-ready points",
  "Make this easier to remember",
  "Ask me three practice questions",
];

const MAX_TEXTAREA_HEIGHT = 164;
const REQUEST_TIMEOUT_MS = 45000;
const SESSIONS_CACHE_KEY = "noya_recent_chat_sessions";

const ChatView = ({ sessionId: externalSessionId = null, onNewChat, onSessionPending, onSessionCreated, theme = "dark", onToggleTheme }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const subjectContext = location.state?.subject;
  const chapterContext = location.state?.chapter;
  const currentSubject = useMemo(() => findSubject(subjectContext || ""), [subjectContext]);
  const availableChapters = currentSubject?.chapters || [];

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(externalSessionId);
  const [sessions, setSessions] = useState(() => {
    try {
      const cached = JSON.parse(localStorage.getItem(SESSIONS_CACHE_KEY) || "[]");
      return Array.isArray(cached) ? cached : [];
    } catch {
      return [];
    }
  });
  const [sessionsLoading, setSessionsLoading] = useState(() => {
    try {
      return !JSON.parse(localStorage.getItem(SESSIONS_CACHE_KEY) || "[]")?.length;
    } catch {
      return true;
    }
  });
  const [sessionsError, setSessionsError] = useState("");
  const [activeLoadingSession, setActiveLoadingSession] = useState(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isNearBottom, setIsNearBottom] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const revealTimerRef = useRef(null);
  const sessionIdRef = useRef(null);
  const scrollContainerRef = useRef(null);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  const isTyping = useMemo(() => messages.some((message) => message.streaming), [messages]);
  const hasContext = Boolean(subjectContext || chapterContext);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    setIsNearBottom(true);
  }, []);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const handleScroll = () => {
      const threshold = 100;
      setIsNearBottom(container.scrollHeight - container.scrollTop - container.clientHeight < threshold);
    };
    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  const refreshSessions = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setSessionsLoading(true);
      setSessionsError("");
    }

    try {
      const loadedSessions = await chatAPI.getSessions();
      const normalizedSessions = Array.isArray(loadedSessions) ? loadedSessions : [];
      setSessions(normalizedSessions);
      localStorage.setItem(SESSIONS_CACHE_KEY, JSON.stringify(normalizedSessions.slice(0, 30)));
      setSessionsError("");
    } catch {
      try {
        const cached = JSON.parse(localStorage.getItem(SESSIONS_CACHE_KEY) || "[]");
        setSessionsError(Array.isArray(cached) && cached.length ? "" : "Could not load conversations.");
      } catch {
        setSessionsError("Could not load conversations.");
      }
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    if (externalSessionId) {
      loadSession(externalSessionId);
    } else {
      resetChat({ notify: false });
    }
  }, [externalSessionId]);

  useEffect(() => {
    resetChat({ notify: false });
  }, [subjectContext, chapterContext]);

  useEffect(() => {
    return () => clearTimeout(revealTimerRef.current);
  }, []);

  useEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  }, [input]);

  const resetChat = ({ notify = true, goToSubjectSelection = false } = {}) => {
    setMessages([]);
    setInput("");
    setSessionId(null);
    setMobileSidebarOpen(false);
    if (notify) onNewChat?.();
    if (goToSubjectSelection) navigate("/subjects");
    setTimeout(() => inputRef.current?.focus(), 80);
  };

  const handleChangeChapter = (chapter) => {
    if (!chapter || !subjectContext) return;
    setMobileSidebarOpen(false);
    navigate("/chat", { state: { subject: subjectContext, chapter } });
  };

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      navigate("/login");
    }
  };

  const loadSession = async (id) => {
    setActiveLoadingSession(id);
    try {
      const session = await chatAPI.getSession(id);
      const loadedMessages = [];
      session.messages?.forEach((message) => {
        loadedMessages.push({ role: "user", content: message.message });
        loadedMessages.push({
          role: "assistant",
          content: message.response,
          source: (message.context || {}).source,
        });
      });
      setMessages(loadedMessages);
      setSessionId(session.id);
      setMobileSidebarOpen(false);
      refreshSessions({ silent: true });
    } catch {
      resetChat();
    } finally {
      setActiveLoadingSession(null);
    }
  };

  const handleSubmit = async (event, overrideText = null) => {
    event?.preventDefault?.();
    const message = (overrideText || input).trim();
    if (!message || loading || isTyping) return;

    clearTimeout(revealTimerRef.current);
    const creatingNewSession = !sessionId;
    const streamingId = Date.now();
    setInput("");
    setMessages((previous) => [
      ...previous,
      { role: "user", content: message },
      {
        role: "assistant",
        content: "",
        status: "Reading the lesson context",
        streaming: true,
        id: streamingId,
      },
    ]);
    setLoading(true);
    if (creatingNewSession) onSessionPending?.(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const contextPayload = {
        language: "english",
        mode: "chat",
        grade: "10",
        ...(subjectContext ? { subject: subjectContext } : {}),
        ...(chapterContext ? { chapter: chapterContext } : {}),
      };

      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API_URL}/chat/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message,
          context: contextPayload,
          session_id: sessionId,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error("Chat request failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.slice(6));

          if (data.type === "status") {
            setMessages((previous) => updateStreamingMessage(previous, streamingId, { status: data.message }));
          }

          if (data.type === "complete") {
            const fullContent = data.response || "I could not generate a response right now.";
            const words = fullContent.split(" ");
            const batchSize = 4;
            let wordIndex = 0;

            const revealNext = () => {
              const nextIndex = Math.min(wordIndex + batchSize, words.length);

              setMessages((previous) =>
                replaceStreamingMessage(previous, streamingId, {
                  role: "assistant",
                  content: words.slice(0, nextIndex).join(" "),
                  source: data.source,
                  streaming: nextIndex < words.length,
                  status: null,
                  id: streamingId,
                })
              );

              wordIndex = nextIndex;

              if (wordIndex >= words.length) {
                if (data.session_id && !sessionIdRef.current) {
                  setSessionId(data.session_id);
                  const optimisticSession = {
                    id: data.session_id,
                    title: data.session_title || message,
                    language: "english",
                    updated_at: new Date().toISOString(),
                  };
                  setSessions((previous) => {
                    const nextSessions = [optimisticSession, ...previous.filter((item) => item.id !== data.session_id)];
                    localStorage.setItem(SESSIONS_CACHE_KEY, JSON.stringify(nextSessions.slice(0, 30)));
                    return nextSessions;
                  });
                  onSessionCreated?.(data.session_id, optimisticSession);
                }
                return;
              }

              revealTimerRef.current = setTimeout(revealNext, 25);
            };

            revealNext();
          }

          if (data.type === "error") {
            setMessages((previous) =>
              replaceStreamingMessage(previous, streamingId, {
                role: "assistant",
                content: data.message || "Something went wrong. Please try again.",
                streaming: false,
                status: null,
                id: streamingId,
              })
            );
          }
        }
      }

      refreshSessions({ silent: true });
      if (creatingNewSession) onSessionPending?.(false);
    } catch (error) {
      if (creatingNewSession) onSessionPending?.(false);
      const timedOut = error?.name === "AbortError" || error?.code === "ERR_CANCELED";

      setMessages((previous) =>
        replaceStreamingMessage(previous, streamingId, {
          role: "assistant",
          content: timedOut
            ? "This took longer than expected, so I stopped waiting. Try a shorter question or ask again."
            : "Sorry, I hit a problem generating that answer. Please try again.",
          streaming: false,
          status: null,
          id: streamingId,
        })
      );
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  return (
    <div className="chat-shell">
      <Sidebar
        sessions={sessions}
        sessionsLoading={sessionsLoading}
        sessionsError={sessionsError}
        activeLoadingSession={activeLoadingSession}
        sessionId={sessionId}
        onSelectSession={loadSession}
        onRetrySessions={() => refreshSessions()}
        onNewChat={() => resetChat({ goToSubjectSelection: true })}
        subjectContext={subjectContext}
        chapterContext={chapterContext}
        availableChapters={availableChapters}
        onChangeChapter={handleChangeChapter}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed((value) => !value)}
        mobileOpen={mobileSidebarOpen}
        onCloseMobile={() => setMobileSidebarOpen(false)}
        user={user}
        theme={theme}
        onToggleTheme={onToggleTheme}
        onLogout={handleLogout}
      />

      {mobileSidebarOpen && (
        <button
          aria-label="Close sidebar"
          onClick={() => setMobileSidebarOpen(false)}
          className="chat-overlay"
        />
      )}

      <main className="chat-main">
        <header className="chat-topbar">
          <button
            onClick={() => setMobileSidebarOpen(true)}
            aria-label="Open sidebar"
            className="chat-icon-button lg:hidden"
          >
            <Menu size={19} aria-hidden="true" />
          </button>
          <div>
            <p>{chapterContext || subjectContext || "Noya Study Chat"}</p>
            <span>{hasContext ? "Focused on your selected lesson" : "Ask a clear study question to begin"}</span>
          </div>
          <button
            onClick={() => resetChat({ goToSubjectSelection: true })}
            className="chat-new-button"
          >
            <CirclePlus size={16} aria-hidden="true" />
            <span>New</span>
          </button>
        </header>

        <section aria-live="polite" aria-relevant="additions" className="chat-scroll" ref={scrollContainerRef}>
          <div className="chat-thread">
            {!messages.length && !loading && (
              <EmptyState
                subjectContext={subjectContext}
                chapterContext={chapterContext}
                onPrompt={(prompt) => handleSubmit(null, prompt)}
              />
            )}

            {messages.map((message, index) => (
              <MessageItem key={`${message.role}-${index}-${message.id || ""}`} message={message} />
            ))}

            <div ref={messagesEndRef} />
          </div>
        </section>

        <div className="chat-status-bar">
          {isTyping && (
            <span className="status-dots" aria-hidden="true">
              <span /><span /><span />
            </span>
          )}
          {!isTyping && messages.length > 0 && !isNearBottom && (
            <button className="status-arrow" onClick={scrollToBottom} aria-label="Scroll to bottom">
              <ChevronDown size={16} />
            </button>
          )}
        </div>

        <footer className="chat-composer-wrap">
          <form onSubmit={handleSubmit} className="chat-composer">
            <label htmlFor="chat-input" className="sr-only">
              Message Noya
            </label>
            <textarea
              id="chat-input"
              ref={inputRef}
              rows={1}
              value={input}
              disabled={loading || isTyping}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  handleSubmit(event);
                }
              }}
              placeholder="Ask Noya anything from your lesson..."
              style={{ maxHeight: MAX_TEXTAREA_HEIGHT }}
            />
            <button type="submit" disabled={!input.trim() || loading || isTyping} aria-label="Send message">
              <Send size={18} aria-hidden="true" />
            </button>
          </form>
          <p className="chat-disclaimer">Answers can make mistakes. Check important facts with your textbook or teacher.</p>
        </footer>
      </main>
    </div>
  );
};

const updateStreamingMessage = (messages, id, patch) =>
  messages.map((message) => (message.streaming && message.id === id ? { ...message, ...patch } : message));

const replaceStreamingMessage = (messages, id, replacement) => {
  const hasStreamingMessage = messages.some((message) => message.streaming && message.id === id);
  if (!hasStreamingMessage) return [...messages, replacement];
  return messages.map((message) => (message.streaming && message.id === id ? replacement : message));
};

const EmptyState = ({ subjectContext, chapterContext, onPrompt }) => (
  <div className="chat-empty">
    <div className="chat-empty-mark">
      <img src={noyaLogo} alt="" />
    </div>
    <div className="chat-empty-copy">
      <span><Sparkles size={15} aria-hidden="true" /> Study workspace</span>
      <h1>What should we make clear today?</h1>
      <p>
        {subjectContext && chapterContext
          ? `Ask about ${chapterContext}, or paste a line that feels confusing.`
          : "Ask a question, request a simpler explanation, or turn a lesson into study points."}
      </p>
    </div>
    <div className="chat-prompt-grid">
      {quickPrompts.map((prompt) => (
        <button key={prompt} onClick={() => onPrompt(prompt)}>
          <PenLine size={15} aria-hidden="true" />
          <span>{prompt}</span>
        </button>
      ))}
    </div>
  </div>
);

const Sidebar = ({
  sessions,
  sessionsLoading,
  sessionsError,
  activeLoadingSession,
  sessionId,
  onSelectSession,
  onRetrySessions,
  onNewChat,
  subjectContext,
  chapterContext,
  availableChapters,
  onChangeChapter,
  collapsed,
  onToggleCollapsed,
  mobileOpen,
  onCloseMobile,
  user,
  theme,
  onToggleTheme,
  onLogout,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClick = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [menuOpen]);

  return (
    <aside className={`chat-sidebar ${mobileOpen ? "is-open" : ""} ${collapsed ? "is-collapsed" : ""}`}>
      <div className="chat-sidebar-inner">
        <div className="chat-sidebar-header">
          <div className="chat-brand" onClick={onToggleCollapsed} role="button" tabIndex={0} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onToggleCollapsed(); } }}>
            <img src={noyaLogo} alt="" />
            {!collapsed && (
              <div>
                <strong>Noya</strong>
                <span>Study chat</span>
              </div>
            )}
          </div>
          <button onClick={onCloseMobile} aria-label="Close sidebar" className="chat-icon-button show-mobile">
            <PanelLeftClose size={17} aria-hidden="true" />
          </button>
        </div>

        <div className="chat-sidebar-actions">
          <button onClick={onNewChat} title="New chat" className="chat-primary-action">
            <CirclePlus size={17} aria-hidden="true" />
            {!collapsed && <span>New chat</span>}
          </button>
          <button onClick={onToggleCollapsed} title="Change chapter" className="chat-secondary-action">
            <BookOpen size={17} aria-hidden="true" />
            {!collapsed && <span>Chapter</span>}
          </button>
        </div>

        {!collapsed && (
          <nav aria-label="Conversation history" className="chat-history">
            {subjectContext && availableChapters.length > 0 && (
              <div className="chat-chapter-picker">
                <label htmlFor="chat-chapter-select">Current chapter</label>
                <select
                  id="chat-chapter-select"
                  value={chapterContext || ""}
                  onChange={(event) => onChangeChapter(event.target.value)}
                >
                  {availableChapters.map((chapter) => (
                    <option key={chapter} value={chapter}>
                      {chapter}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="chat-history-title">
              <span>Recent chats</span>
              {sessionsLoading && <Clock3 size={13} aria-hidden="true" />}
            </div>

            {sessionsLoading && <SessionSkeleton />}

            {!sessionsLoading && sessionsError && (
              <div className="chat-history-empty">
                <p>{sessionsError}</p>
                <button onClick={onRetrySessions}>Retry</button>
              </div>
            )}

            {!sessionsLoading && !sessionsError && sessions.length === 0 && (
              <div className="chat-history-empty">
                <p>Your conversations will appear here after the first saved answer.</p>
              </div>
            )}

            {!sessionsLoading && !sessionsError && sessions.length > 0 && (
              <div className="chat-session-list">
                {sessions.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => onSelectSession(item.id)}
                    aria-current={sessionId === item.id ? "true" : undefined}
                    className={sessionId === item.id ? "active" : ""}
                  >
                    <span>{item.title || item.last_message?.message || "Untitled chat"}</span>
                    {activeLoadingSession === item.id ? <Clock3 size={14} aria-hidden="true" /> : <ChevronRight size={14} aria-hidden="true" />}
                  </button>
                ))}
              </div>
            )}
          </nav>
        )}

        <div className="chat-sidebar-footer">
          <div className="chat-user-menu" ref={menuRef}>
            <button
              className="chat-user-avatar-btn"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="User menu"
              aria-expanded={menuOpen}
            >
              <UserRound size={18} aria-hidden="true" />
            </button>
            {menuOpen && (
              <div className={`chat-user-popup${collapsed ? " is-right" : ""}`}>
                <div className="chat-user-popup-header">
                  <strong>{user?.username || "Guest"}</strong>
                  <span>{user?.email || ""}</span>
                </div>
                <div className="chat-user-popup-plan">
                  <span className={`plan-badge ${user?.plan_tier === "paid" ? "paid" : "free"}`}>
                    {user?.plan_tier === "paid" ? "Paid" : "Free"}
                  </span>
                </div>
                <div className="chat-user-popup-actions">
                  <button onClick={onToggleTheme} className="chat-popup-btn">
                    {theme === "dark" ? <SunMedium size={15} aria-hidden="true" /> : <MoonStar size={15} aria-hidden="true" />}
                    <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
                  </button>
                  <button onClick={onLogout} className="chat-popup-btn danger">
                    <LogOut size={15} aria-hidden="true" />
                    <span>Log out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
};

const SessionSkeleton = () => (
  <div className="chat-session-skeleton" aria-label="Loading recent chats">
    {Array.from({ length: 6 }).map((_, index) => (
      <div key={index}>
        <span />
      </div>
    ))}
  </div>
);

const MessageItem = ({ message }) => {
  if (message.role === "user") {
    return (
      <article className="chat-message user">
        <div>
          <p>{message.content}</p>
        </div>
      </article>
    );
  }

  if (message.streaming) {
    return (
      <article className="chat-message assistant is-streaming">
        <div className="assistant-mark">
          <Sparkles size={15} aria-hidden="true" />
        </div>
        <div className="assistant-response">
          {message.content ? (
            <MarkdownRenderer content={message.content} />
          ) : (
            <div className="streaming-line">
              <span />
              <span />
              <span />
              <p>{message.status || "Thinking"}</p>
            </div>
          )}
        </div>
      </article>
    );
  }

  return (
    <article className="chat-message assistant">
      <div className="assistant-mark">
        <Check size={15} aria-hidden="true" />
      </div>
      <div className="assistant-response">
        <MarkdownRenderer content={typeof message.content === "string" ? message.content : String(message.content || "")} />
        {message.source && (
          <div className="assistant-source">
            <span>From lesson</span>
            <p>{message.source}</p>
          </div>
        )}
      </div>
    </article>
  );
};

export default ChatView;
