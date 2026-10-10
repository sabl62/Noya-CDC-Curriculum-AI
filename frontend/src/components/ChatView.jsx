import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import {
  ArrowUp,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  CirclePlus,
  Clock3,
  Copy,
  LogOut,
  PanelLeftClose,
  PenLine,
  Settings,
  UserRound,
  X,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { API_URL, chatAPI } from "../services/api";
import { useAuth } from "../context/AuthContext.jsx";
import { findSubject } from "../data/curriculum.js";
import MarkdownRenderer from "./MarkdownRenderer.jsx";
import SettingsModal from "./SettingsModal.jsx";
import noyaLogo from "../assets/noya-logo.svg";

const PRO_CHAT_MODULES = import.meta.glob("../pro/ChatProFeatures.jsx", { eager: true });
const ProChatFeatures = PRO_CHAT_MODULES["../pro/ChatProFeatures.jsx"];

const quickPrompts = [
  "Explain this simply",
  "Give me exam-ready points",
  "Make this easier to remember",
  "Ask me three practice questions",
];

const MODELS = [
  { id: "deepseek-v3", name: "DeepSeek V3", tier: "free" },
  { id: "deepseek-r1", name: "DeepSeek R1", tier: "free" },
];

const MAX_TEXTAREA_HEIGHT = 164;
const REQUEST_TIMEOUT_MS = 45000;
const SESSIONS_CACHE_KEY = "noya_recent_chat_sessions";
const RECENT_CHATS_HIDDEN_KEY = "noya_recent_chats_hidden";

const chatErrorMessage = (code, statusCode) => {
  if (code === "auth_expired" || statusCode === 401) {
    return "Your session expired. Please sign in again.";
  }
  if (code === "model_traffic") {
    return "The AI models are under heavy traffic right now. Please try again in a little while.";
  }
  if (code === "user_api_quota") {
    return "Your custom API key has run out of available usage. Add credits or use a key with available quota.";
  }
  if (code === "ai_timeout") {
    return "The AI service took too long to respond. Please try again.";
  }
  if (statusCode >= 500 || code === "server_failure") {
    return "Noya's AI service couldn't generate a response right now. Please try again later.";
  }
  return "Something went wrong while sending your question. Please try again.";
};

const ChatView = ({ sessionId: externalSessionId = null, onNewChat, onSessionPending, onSessionCreated, onSessionSelected, theme = "dark", onToggleTheme, billingAvailable = false }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const subjectContext = location.state?.subject;
  const chapterContext = location.state?.chapter;
  const currentSubject = useMemo(() => findSubject(subjectContext || ""), [subjectContext]);
  const availableChapters = currentSubject?.chapters || [];
  const proEnabled = Boolean(billingAvailable && ProChatFeatures);
  const availableModels = proEnabled ? [...MODELS, ...ProChatFeatures.models] : MODELS;
  const hasProAccess = proEnabled && ProChatFeatures.hasProAccess(user);

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [selectedModel, setSelectedModel] = useState(MODELS[0]);
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [dropdownDir, setDropdownDir] = useState("down");
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
  const [settingsOpen, setSettingsOpen] = useState(false);
  const closeSettings = useCallback(() => setSettingsOpen(false), []);
  const [limitPopup, setLimitPopup] = useState(null);
  const [limitBanner, setLimitBanner] = useState(null);
  const [rateNotice, setRateNotice] = useState(false);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const modelDropdownRef = useRef(null);
  const revealTimerRef = useRef(null);
  const sessionIdRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const dismissedLimitRef = useRef(null);
  // Session identity is tracked in refs as well as state because the load and
  // reset effects below must see the in-flight load synchronously, before React
  // has committed the corresponding state updates.
  const loadingSessionRef = useRef(null);
  const loadedSessionRef = useRef(null);
  const loadRequestRef = useRef(0);
  // Marks the subject/chapter pair that loadSession() pushed into router state.
  // That navigation is what fires the reset effect below, so the effect has to
  // be able to tell it apart from a subject/chapter change the student made.
  const appliedContextRef = useRef(null);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    if (!proEnabled && selectedModel.tier === "paid") {
      setSelectedModel(MODELS[0]);
      setModelDropdownOpen(false);
    }
  }, [proEnabled, selectedModel]);

  useEffect(() => {
    if (!rateNotice) return undefined;
    const timer = setTimeout(() => setRateNotice(false), 8000);
    return () => clearTimeout(timer);
  }, [rateNotice]);

  const dismissLimitPopup = () => {
    if (!limitPopup) return;
    dismissedLimitRef.current = limitPopup.limitType;
    setLimitBanner(limitPopup);
    setLimitPopup(null);
  };

  const isTyping = useMemo(() => messages.some((message) => message.streaming), [messages]);
  // True while the selected chat is being fetched, so the thread can show a
  // placeholder instead of the previous chat's messages.
  const loadingSession = Boolean(activeLoadingSession) && activeLoadingSession === sessionId;
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

  useEffect(() => {
    if (!modelDropdownOpen) return;
    const trigger = modelDropdownRef.current;
    if (trigger) {
      const rect = trigger.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      setDropdownDir(spaceBelow >= spaceAbove ? "down" : "up");
    }
    const handleClickOutside = (e) => {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target)) {
        setModelDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [modelDropdownOpen]);

  useEffect(() => {
    const textarea = inputRef.current;
    if (!textarea) return;
    const handleKeyDown = (e) => {
      if (loading || isTyping) return;
      if (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT") return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key.length === 1 || e.key === "Backspace") {
        textarea.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [loading, isTyping]);

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
    // Follow the session App considers current, but never re-fetch what is
    // already on screen — otherwise selecting a chat in the sidebar would echo
    // back as a prop change and reload it a second time.
    if (!externalSessionId) {
      // App cleared the current session. Mirror that, but only when a session
      // was genuinely open — otherwise this would wipe a brand-new chat, which
      // has no session id yet.
      if (loadedSessionRef.current) {
        loadedSessionRef.current = null;
        setSessionId(null);
      }
      return;
    }
    if (externalSessionId === loadedSessionRef.current || externalSessionId === loadingSessionRef.current) {
      return;
    }
    loadSession(externalSessionId);
  }, [externalSessionId]);

  useEffect(() => {
    // A subject/chapter change starts a new conversation — except the change
    // loadSession() just made while restoring a chat's own textbook context.
    // Resetting on that one used to discard the messages that were only just
    // fetched and leave the sidebar with nothing selected.
    const contextKey = `${subjectContext || ""}\u0000${chapterContext || ""}`;
    if (appliedContextRef.current === contextKey) {
      appliedContextRef.current = null;
      return;
    }
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
    // Invalidate any in-flight history request so its response is discarded
    // rather than repopulating a chat the user has already left.
    loadRequestRef.current += 1;
    loadingSessionRef.current = null;
    loadedSessionRef.current = null;
    appliedContextRef.current = null;
    sessionIdRef.current = null;
    setMessages([]);
    setInput("");
    setSessionId(null);
    setActiveLoadingSession(null);
    setMobileSidebarOpen(false);
    if (notify) onNewChat?.();
    if (goToSubjectSelection) navigate("/subjects");
    setTimeout(() => inputRef.current?.focus(), 80);
  };

  const handleChangeChapter = (chapter) => {
    if (!chapter || !subjectContext) return;
    setMobileSidebarOpen(false);
    // An explicit chapter choice is always a new conversation.
    appliedContextRef.current = null;
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
    if (!id) return;

    // Claim the session synchronously: the effects above read the refs to
    // decide whether a subject/chapter change is a reset or a session switch.
    // Dropping any marker from an earlier load keeps a stale one from
    // suppressing a genuine reset later on.
    loadingSessionRef.current = id;
    appliedContextRef.current = null;
    loadRequestRef.current += 1;
    const requestId = loadRequestRef.current;

    // Select immediately so the row shows its active state while it loads,
    // instead of appearing to do nothing until the response arrives.
    setSessionId(id);
    setActiveLoadingSession(id);

    try {
      const session = await chatAPI.getSession(id);

      // A newer click (or a new chat) landed while this request was in flight.
      if (requestId !== loadRequestRef.current) return;

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
      loadedSessionRef.current = session.id;
      setMobileSidebarOpen(false);
      // Keep App's idea of the current session in step with the sidebar, so the
      // two never disagree about what is open.
      onSessionSelected?.(session.id);

      // Restore the session's own subject/chapter into router state.
      // The session record (kept in sync by the backend) is authoritative.
      // Message contexts are only a fallback, and only when their subject
      // matches — so a message saved during the stale-state bug can never
      // restore a chapter from another subject's book.
      const restoredSubject = session.subject || null;
      let restoredChapter = session.chapter || null;
      if (!restoredChapter && restoredSubject && session.messages?.length) {
        for (let i = session.messages.length - 1; i >= 0; i--) {
          const messageContext = session.messages[i].context || {};
          if (
            messageContext.subject === restoredSubject &&
            messageContext.chapter
          ) {
            restoredChapter = messageContext.chapter;
            break;
          }
        }
      }
      // A chapter that isn't part of this subject's curriculum is junk — drop it.
      const subjectChapters = findSubject(restoredSubject || "")?.chapters || [];
      if (restoredChapter && !subjectChapters.includes(restoredChapter)) {
        restoredChapter = null;
      }
      if (restoredSubject !== subjectContext || restoredChapter !== chapterContext) {
        // Flag this navigation as ours so the reset effect above recognises it.
        appliedContextRef.current = `${restoredSubject || ""}\u0000${restoredChapter || ""}`;
        navigate("/chat", {
          state: restoredSubject ? { subject: restoredSubject, chapter: restoredChapter } : {},
          replace: true,
        });
      }

      refreshSessions({ silent: true });
    } catch {
      if (requestId !== loadRequestRef.current) return;
      // Put the selection back on the chat that is actually on screen. Wiping
      // everything because one history request failed is what used to leave
      // the sidebar with nothing selected.
      const stillLoadedId = loadedSessionRef.current || null;
      setSessionId(stillLoadedId);
    } finally {
      if (requestId === loadRequestRef.current) {
        loadingSessionRef.current = null;
        setActiveLoadingSession(null);
      }
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
      { role: "user", content: message, id: `user-${streamingId}` },
      {
        role: "assistant",
        content: "",
        status: "Thinking",
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
          model: selectedModel.id,
        }),
        signal: controller.signal,
      });

      if (response.status === 429) {
        let payload = {};
        try {
          payload = await response.json();
        } catch {
          payload = {};
        }
        const knownLimit = ["daily", "monthly", "rate"].includes(payload.limit_type);
        if (!knownLimit) {
          setMessages((previous) =>
            replaceStreamingMessage(previous, streamingId, {
              role: "assistant",
              content: "Noya is receiving too many requests right now. Please wait a moment and try again.",
              streaming: false,
              status: null,
              id: streamingId,
            })
          );
          if (creatingNewSession) onSessionPending?.(false);
          return;
        }
        const limitType = payload.limit_type;
        const info = { limitType, plan: payload.plan || user?.plan_tier || "free" };

        // Undo the optimistic turn — the message was not answered.
        setMessages((previous) => previous.filter((item) => item.id !== streamingId));
        setInput(message);

        if (limitType === "rate") {
          setRateNotice(true);
        } else if (dismissedLimitRef.current === limitType) {
          setLimitBanner(info);
        } else {
          setLimitPopup(info);
        }

        if (creatingNewSession) onSessionPending?.(false);
        return;
      }

      if (!response.ok || !response.body) {
        let errorCode = "server_failure";
        try {
          const payload = await response.json();
          errorCode = payload.error_code || errorCode;
        } catch {
          // Non-JSON proxy/server errors still receive a safe message below.
        }
        if (response.status === 401) {
          errorCode = "auth_expired";
          logout();
          navigate("/login", { replace: true });
        }
        const failure = new Error(chatErrorMessage(errorCode, response.status));
        failure.chatMessage = chatErrorMessage(errorCode, response.status);
        throw failure;
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
                  loadedSessionRef.current = data.session_id;
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
                content: chatErrorMessage(data.error_code),
                streaming: false,
                status: null,
                id: streamingId,
              })
            );
          }
        }
      }

      // A delivered answer means any earlier quota/rate notice no longer applies.
      setRateNotice(false);
      setLimitBanner(null);
      dismissedLimitRef.current = null;

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
            : error?.chatMessage || (error instanceof TypeError
              ? "Noya couldn't reach its servers. Check your connection and try again."
              : chatErrorMessage("server_failure")),
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
        proEnabled={proEnabled}
        hasProAccess={hasProAccess}
        onLogout={handleLogout}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {mobileSidebarOpen && (
        <button
          aria-label="Close sidebar"
          onClick={() => setMobileSidebarOpen(false)}
          className="chat-overlay"
        />
      )}

      <main className="chat-main">
        <section aria-live="polite" aria-relevant="additions" className="chat-scroll" ref={scrollContainerRef}>
          <div className="chat-thread">
            {loadingSession && <ThreadSkeleton />}

            {!loadingSession && !messages.length && !loading && (
              <EmptyState
                subjectContext={subjectContext}
                chapterContext={chapterContext}
                onPrompt={(prompt) => handleSubmit(null, prompt)}
              />
            )}

            {!loadingSession && messages.map((message, index) => (
              <MessageItem
                key={`${message.role}-${index}-${message.id || ""}`}
                message={message}
              />
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
          {rateNotice && (
            <div className="chat-limit-banner rate" role="status">
              <span>You are sending messages too quickly. Please wait a moment and try again.</span>
              <button type="button" onClick={() => setRateNotice(false)} aria-label="Dismiss">
                <X size={13} />
              </button>
            </div>
          )}
          {limitBanner && (
            <div className="chat-limit-banner" role="status">
              {proEnabled && limitBanner.plan !== "paid" ? (
                <ProChatFeatures.LimitBanner limitType={limitBanner.limitType} onUpgrade={() => navigate("/billing")} />
              ) : (
                <>
                  <span>You have reached your {limitBanner.limitType} limit on chats. Please try again when your limit resets.</span>
                  <button type="button" onClick={() => setLimitBanner(null)} aria-label="Dismiss"><X size={13} /></button>
                </>
              )}
            </div>
          )}
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
            <div className="chat-model-picker" ref={modelDropdownRef}>
              <button
                type="button"
                className="chat-model-trigger"
                onClick={() => setModelDropdownOpen((v) => !v)}
                disabled={loading || isTyping}
              >
                {/* <Sparkles size={14} aria-hidden="true" /> */}
                <span>{selectedModel.name}</span>
                <ChevronDown size={14} aria-hidden="true" className={modelDropdownOpen ? "rotated" : ""} />
              </button>
              {modelDropdownOpen && (
                <div className={`chat-model-dropdown ${dropdownDir === "up" ? "drop-up" : ""}`}>
                  {availableModels.map((model) => {
                    const isDisabled = model.tier === "paid" && !hasProAccess;
                    return (
                      <button
                        key={model.id}
                        type="button"
                        className={`chat-model-option ${selectedModel.id === model.id ? "active" : ""} ${isDisabled ? "locked" : ""}`}
                        onClick={() => {
                          if (!isDisabled) {
                            setSelectedModel(model);
                            setModelDropdownOpen(false);
                          }
                        }}
                        disabled={isDisabled}
                      >
                        {model.tier === "paid" && proEnabled
                          ? <ProChatFeatures.ModelOptionLabel model={model} />
                          : <span className="model-option-name">{model.name}</span>}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
            <button
              type="submit"
              className="chat-send-btn"
              disabled={!input.trim() || loading || isTyping}
              aria-label="Send message"
            >
              <ArrowUp size={18} strokeWidth={2.5} aria-hidden="true" />
            </button>
          </form>
          <p className="chat-disclaimer">Answers can make mistakes. Check important facts with your textbook or teacher.</p>
        </footer>

        {proEnabled && !hasProAccess && <ProChatFeatures.FloatingUpgrade />}
      </main>
      {settingsOpen && (
        <SettingsModal
          onClose={closeSettings}
          theme={theme}
          onToggleTheme={onToggleTheme}
          billingAvailable={proEnabled}
        />
      )}
      {limitPopup && (
        <div className="limit-popup-overlay" onClick={dismissLimitPopup}>
          <div
            className="limit-popup"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="limit-popup-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button type="button" className="limit-popup-close" onClick={dismissLimitPopup} aria-label="Close">
              <X size={17} />
            </button>
            <div className="limit-popup-icon">
              <Clock3 size={20} />
            </div>
            <h3 id="limit-popup-title">
              {limitPopup.limitType === "monthly" ? "Monthly Limit reached!" : "Daily Limit reached!"}
            </h3>
            <p>
              {proEnabled && limitPopup.plan !== "paid"
                ? <ProChatFeatures.LimitPopupMessage limitType={limitPopup.limitType} />
                : `You have reached your ${limitPopup.limitType} limit on chats. Please try again when your limit resets.`}
            </p>
            {proEnabled && limitPopup.plan !== "paid" ? (
              <ProChatFeatures.UpgradeAction onClick={() => { dismissLimitPopup(); navigate("/billing"); }} />
            ) : (
              <button type="button" className="limit-popup-upgrade" onClick={dismissLimitPopup}>
                Got it
              </button>
            )}
          </div>
        </div>
      )}
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
const titles=["Let's Study Together!", "I'm Ready!", "Any Doubts?", "Let's Ace that Exam."];
const title = titles[Math.floor(Math.random()*titles.length)];
const EmptyState = ({ subjectContext, chapterContext, onPrompt }) => (
  <div className="chat-empty">
    
    
    <div className="chat-empty-copy">

      {/* <span><Sparkles size={15} aria-hidden="true" /> Study workspace</span> */}
      <h1>{title}</h1>
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
  proEnabled,
  hasProAccess,
  onLogout,
  onOpenSettings,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [popupStyle, setPopupStyle] = useState({});
  const [highlightPicker, setHighlightPicker] = useState(false);
  const [recentChatsHidden, setRecentChatsHidden] = useState(() => {
    try {
      return localStorage.getItem(RECENT_CHATS_HIDDEN_KEY) === "true";
    } catch {
      return false;
    }
  });
  const menuRef = useRef(null);
  const avatarRef = useRef(null);
  const popupRef = useRef(null);
  const chapterSelectRef = useRef(null);

  const focusChapterPicker = useCallback(() => {
    setHighlightPicker(true);
    setTimeout(() => setHighlightPicker(false), 1500);
  }, []);

  const toggleRecentChats = () => {
    setRecentChatsHidden((hidden) => !hidden);
  };

  useEffect(() => {
    try {
      localStorage.setItem(RECENT_CHATS_HIDDEN_KEY, String(recentChatsHidden));
    } catch {
      // Keep the toggle usable if browser storage is unavailable.
    }
  }, [recentChatsHidden]);

  useEffect(() => {
    const handleClick = (event) => {
      if (
        !menuRef.current?.contains(event.target) &&
        !popupRef.current?.contains(event.target)
      ) {
        setMenuOpen(false);
      }
    };
    if (menuOpen) {
      document.addEventListener("mousedown", handleClick);
      return () => document.removeEventListener("mousedown", handleClick);
    }
  }, [menuOpen]);

  useLayoutEffect(() => {
    if (!menuOpen) return undefined;
    const gap = 10;
    const focusFrame = window.requestAnimationFrame(() => {
      popupRef.current?.querySelector('[role="menuitem"]')?.focus();
    });
    const updatePosition = () => {
      if (!avatarRef.current || !popupRef.current) return;
      const anchor = avatarRef.current.getBoundingClientRect();
      const popup = popupRef.current.getBoundingClientRect();
      const width = Math.min(popup.width || 240, window.innerWidth - gap * 2);
      const height = Math.min(popup.height || 220, window.innerHeight - gap * 2);
      const placeRight = collapsed && window.innerWidth - anchor.right >= width + gap;
      const placeLeft = collapsed && !placeRight && anchor.left >= width + gap;
      const left = placeRight
        ? anchor.right + gap
        : placeLeft
          ? anchor.left - width - gap
          : Math.max(gap, Math.min(anchor.left + (anchor.width - width) / 2, window.innerWidth - width - gap));
      const top = anchor.top >= height + gap
        ? anchor.top - height - gap
        : Math.max(gap, Math.min(anchor.bottom + gap, window.innerHeight - height - gap));
      setPopupStyle({ position: "fixed", top, left, maxHeight: `calc(100dvh - ${gap * 2}px)`, zIndex: 1000 });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.cancelAnimationFrame(focusFrame);
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [menuOpen, collapsed]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        avatarRef.current?.focus();
        return;
      }
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        const items = [...(popupRef.current?.querySelectorAll('[role="menuitem"]') || [])];
        if (!items.length) return;
        event.preventDefault();
        const currentIndex = items.indexOf(document.activeElement);
        const nextIndex = event.key === "Home"
          ? 0
          : event.key === "End"
            ? items.length - 1
            : (currentIndex + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
        items[nextIndex].focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [menuOpen]);

  return (
    <aside className={`chat-sidebar ${mobileOpen ? "is-open" : ""} ${collapsed ? "is-collapsed" : ""}`}>
      <div className="chat-sidebar-inner">
        <div className="chat-sidebar-header">
          <button type="button" className="chat-brand" onClick={onToggleCollapsed} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            <img src={noyaLogo} alt="" />
            {!collapsed && (
              <div>
                <strong>Noya</strong>
                {/* <span>Study chat</span> */}
              </div>
            )}
          </button>
          <button onClick={onCloseMobile} aria-label="Close sidebar" className="chat-icon-button show-mobile">
            <PanelLeftClose size={17} aria-hidden="true" />
          </button>
        </div>

        <div className="chat-sidebar-actions">
          <button type="button" onClick={onNewChat} title="New chat" aria-label={collapsed ? "New chat" : undefined} className="chat-primary-action">
            <CirclePlus size={17} aria-hidden="true" />
            {!collapsed && <span>New chat</span>}
          </button>
          <button
            onClick={() => { if (collapsed) onToggleCollapsed(); else focusChapterPicker(); }}
            title="Change chapter"
            aria-label={collapsed ? "Change chapter" : undefined}
            className={`chat-secondary-action${collapsed ? " highlight" : ""}`}
          >
            <BookOpen size={17} aria-hidden="true" />
            {!collapsed && <span>Chapter</span>}
          </button>
        </div>

        {!collapsed && (
          <nav aria-label="Conversation history" className="chat-history">
            {subjectContext && availableChapters.length > 0 && (
              <div className="chat-chapter-picker">
                <label htmlFor="chat-chapter-select">Chapter</label>
                <select
                  ref={chapterSelectRef}
                  id="chat-chapter-select"
                  value={chapterContext || ""}
                  onChange={(event) => onChangeChapter(event.target.value)}
                  className={highlightPicker ? "highlight" : ""}
                >
                  {!chapterContext && <option value="">Select a chapter</option>}
                  {availableChapters.map((chapter) => (
                    <option key={chapter} value={chapter}>
                      {chapter}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {!subjectContext && (
              <div className="chat-chapter-picker">
                <span className="chat-chapter-empty">Select a subject to choose a chapter</span>
                <button className="chat-secondary-action small" onClick={() => navigate("/subjects")}>
                  <BookOpen size={15} />
                  <span>Choose subject</span>
                </button>
              </div>
            )}

            <div className="chat-history-title">
              <button
                type="button"
                className="chat-history-toggle"
                onClick={toggleRecentChats}
                aria-expanded={!recentChatsHidden}
                aria-controls="chat-session-history"
              >
                <span>Recent chats</span>
                <ChevronDown size={14} aria-hidden="true" className={recentChatsHidden ? "collapsed" : ""} />
              </button>
              {sessionsLoading && <Clock3 size={13} aria-hidden="true" />}
            </div>

            <div id="chat-session-history" hidden={recentChatsHidden}>
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
                  {sessions.map((item) => {
                    const isSelected = sessionId === item.id;
                    const isLoading = activeLoadingSession === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => onSelectSession(item.id)}
                        aria-current={isSelected ? "true" : undefined}
                        aria-busy={isLoading ? "true" : undefined}
                        disabled={isLoading}
                        className={`${isSelected ? "active" : ""}${isLoading ? " loading" : ""}`}
                      >
                        <span className="chat-session-label">
                          {item.title || item.last_message?.message || "Untitled chat"}
                        </span>
                        {isLoading
                          ? <span className="chat-session-spinner" aria-hidden="true" />
                          : <ChevronRight size={14} aria-hidden="true" />}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </nav>
        )}

        <div className="chat-sidebar-footer">
          <div className="chat-user-menu" ref={menuRef}>
            <button
              ref={avatarRef}
              className="chat-user-avatar-btn"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label={`Account menu for ${user?.username || "Guest"}`}
              title="Account menu"
              aria-expanded={menuOpen}
              aria-haspopup="menu"
              aria-controls={menuOpen ? "chat-user-popup" : undefined}
              onKeyDown={(event) => {
                if ((event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") && !menuOpen) {
                  event.preventDefault();
                  setMenuOpen(true);
                }
              }}
            >
              <UserRound size={18} aria-hidden="true" />
            </button>
            {!collapsed && (
              <span className="chat-user-name">{user?.username || "Guest"}</span>
            )}
            {menuOpen && createPortal(
              <div id="chat-user-popup" ref={popupRef} className="chat-user-popup" style={popupStyle} role="menu" aria-label="Account menu">
                <div className="chat-user-popup-header">
                  <strong>{user?.username || "Guest"}</strong>
                  <span>{user?.email || ""}</span>
                </div>
                {proEnabled && (
                  <div className="chat-user-popup-plan">
                    <ProChatFeatures.PlanBadge hasAccess={hasProAccess} />
                  </div>
                )}
                <div className="chat-user-popup-actions">
                  {proEnabled && !hasProAccess && <ProChatFeatures.UserMenuUpgrade />}
                  <button role="menuitem" onClick={() => { setMenuOpen(false); onOpenSettings?.(); }} className="chat-popup-btn">
                    <Settings size={15} aria-hidden="true" />
                    <span>Settings</span>
                  </button>
                  <button role="menuitem" onClick={onLogout} className="chat-popup-btn danger">
                    <LogOut size={15} aria-hidden="true" />
                    <span>Log out</span>
                  </button>
                </div>
              </div>,
              document.body,
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

// Placeholder shown in the message thread while a recent chat is fetched, so
// opening one reads as a transition rather than a frozen screen.
const ThreadSkeleton = () => (
  <div className="chat-thread-skeleton" role="status" aria-label="Loading conversation" aria-busy="true">
    <span className="sr-only">Loading conversation</span>
    <div className="chat-skeleton-user" aria-hidden="true">
      <span className="chat-skeleton-line" />
    </div>
    <div className="chat-skeleton-answer" aria-hidden="true">
      <span className="chat-skeleton-line long" />
      <span className="chat-skeleton-line medium" />
      <span className="chat-skeleton-line short" />
    </div>
  </div>
);

const MessageItem = ({ message }) => {
  const [copied, setCopied] = useState(false);

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
          <img src={noyaLogo} alt="" className="animate-spin" />
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

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content || "");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = message.content || "";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <article className="chat-message assistant">
      <div className="assistant-mark">
         <img src={noyaLogo} alt="" />
      </div>
      <div className="assistant-response">
        <MarkdownRenderer content={typeof message.content === "string" ? message.content : String(message.content || "")} />
        <div className="assistant-actions">
          <button
            className="assistant-action-btn"
            onClick={handleCopy}
            title="Copy response"
            aria-label="Copy response"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {/* <span>{copied ? "Copied" : "Copy"}</span> */}
          </button>
        </div>
      </div>
    </article>
  );
};

export default ChatView;
