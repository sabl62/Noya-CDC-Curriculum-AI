import React, { useEffect, useRef, useState } from "react";
import {
  LogOut,
  Moon,
  Sun,
  User,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { usageAPI } from "../services/api";

const PRO_SETTINGS_MODULES = import.meta.glob("../pro/SettingsPro.jsx", { eager: true });
const ProSettings = PRO_SETTINGS_MODULES["../pro/SettingsPro.jsx"]?.default;
const proSettingsTabs = PRO_SETTINGS_MODULES["../pro/SettingsPro.jsx"]?.tabs || [];

const SETTINGS_KEYS = {
  CONTEXT_MEMORY: "noya_context_memory",
};

const formatResetTime = (resetsAt) => {
  if (!resetsAt) return "Starts after your first counted chat";
  const minutes = Math.max(1, Math.ceil((new Date(resetsAt).getTime() - Date.now()) / 60000));
  if (minutes <= 1) return "Resets in less than a minute";
  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const remainingMinutes = minutes % 60;
  const duration = days > 0
    ? `${days}d ${hours}h`
    : hours > 0
      ? `${hours}h ${remainingMinutes}m`
      : `${remainingMinutes}m`;
  return `Resets in ${duration}`;
};

const SettingsModal = ({ onClose, theme, onToggleTheme, billingAvailable = false }) => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("general");
  const [contextMemory, setContextMemory] = useState(() => {
    return localStorage.getItem(SETTINGS_KEYS.CONTEXT_MEMORY) !== "false";
  });
  const [usage, setUsage] = useState(null);
  const [usageLoading, setUsageLoading] = useState(false);
  const [usageError, setUsageError] = useState("");
  const modalRef = useRef(null);
  const closeButtonRef = useRef(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    const handleKey = (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !modalRef.current) return;
      const focusable = [...modalRef.current.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])')]
        .filter((element) => element.getAttribute("aria-hidden") !== "true");
      if (!focusable.length) {
        e.preventDefault();
        modalRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && (document.activeElement === first || !modalRef.current.contains(document.activeElement))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (document.activeElement === last || !modalRef.current.contains(document.activeElement))) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKey);
    };
  }, [onClose]);

  useEffect(() => {
    if (activeTab !== "usage") return undefined;
    let cancelled = false;
    setUsageLoading(true);
    setUsageError("");

    usageAPI.getStats()
      .then((data) => {
        if (!cancelled) setUsage(data);
      })
      .catch(() => {
        if (!cancelled) setUsageError("Usage data could not be loaded. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setUsageLoading(false);
      });

    return () => { cancelled = true; };
  }, [activeTab]);

  const handleContextMemoryToggle = () => {
    const next = !contextMemory;
    setContextMemory(next);
    localStorage.setItem(SETTINGS_KEYS.CONTEXT_MEMORY, String(next));
  };

  const handleLogout = () => {
    onClose();
    logout();
  };

  const handleTabKeyDown = (event) => {
    const tabButtons = [...event.currentTarget.querySelectorAll('[role="tab"]')];
    const currentIndex = tabButtons.indexOf(document.activeElement);
    if (currentIndex < 0) return;
    let nextIndex = currentIndex;
    if (["ArrowRight", "ArrowDown"].includes(event.key)) nextIndex = (currentIndex + 1) % tabButtons.length;
    else if (["ArrowLeft", "ArrowUp"].includes(event.key)) nextIndex = (currentIndex - 1 + tabButtons.length) % tabButtons.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = tabButtons.length - 1;
    else return;
    event.preventDefault();
    const nextTab = tabs[nextIndex];
    setActiveTab(nextTab.id);
    tabButtons[nextIndex].focus();
  };

  const tabs = [
    { id: "general", label: "General" },
    ...(billingAvailable && ProSettings ? proSettingsTabs : []),
    { id: "usage", label: "Usage" },
    { id: "account", label: "Account" },
  ];

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div ref={modalRef} className="settings-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="settings-title" tabIndex={-1}>
        <div className="settings-header">
          <div className="settings-heading">
            <span className="settings-eyebrow">Your workspace</span>
            <h2 id="settings-title">Settings</h2>
          </div>
          <button ref={closeButtonRef} type="button" className="settings-close-btn" onClick={onClose} aria-label="Close settings">
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <div className="settings-body">
          <nav className="settings-tabs" aria-label="Settings sections" role="tablist" aria-orientation="vertical" onKeyDown={handleTabKeyDown}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                id={`settings-tab-${tab.id}`}
                type="button"
                className={`settings-tab ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls="settings-panel"
                tabIndex={activeTab === tab.id ? 0 : -1}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="settings-content" id="settings-panel" role="tabpanel" aria-labelledby={`settings-tab-${activeTab}`} tabIndex={0}>
            {activeTab === "general" && (
              <div className="settings-section">
                <h3>Appearance</h3>
                <div className="settings-row">
                  <div className="settings-row-info">
                    <span className="settings-row-label">Theme</span>
                    <span className="settings-row-desc">Switch between light and dark mode</span>
                  </div>
                  <button type="button" className="settings-toggle-btn" onClick={onToggleTheme} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} appearance`}>
                    {theme === "dark" ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
                    <span>{theme === "dark" ? "Light" : "Dark"}</span>
                  </button>
                </div>

                <h3>AI Behavior</h3>
                <div className="settings-row">
                  <div className="settings-row-info">
                    <span className="settings-row-label">Context memory</span>
                    <span className="settings-row-desc">Allow Noya to remember previous messages in this session for better answers</span>
                  </div>
                  <button
                    className={`settings-switch ${contextMemory ? "on" : ""}`}
                    onClick={handleContextMemoryToggle}
                    type="button"
                    role="switch"
                    aria-checked={contextMemory}
                    aria-label="Context memory"
                  >
                    <span className="settings-switch-thumb" />
                  </button>
                </div>

              </div>
            )}

            {activeTab === "usage" && (
              <div className="settings-section">
                <h3>Chat Usage</h3>
                {usageLoading && <p className="settings-usage-note">Loading usage…</p>}
                {usageError && <p className="settings-usage-note" role="alert">{usageError}</p>}
                {usage && !usageLoading && (
                  <>
                    <p className="settings-usage-note">
                      {usage.plan_tier === "paid" ? "Pro plan" : "Free plan"}
                    </p>
                    {[ ["Daily chats", usage.daily], ["Monthly chats", usage.monthly] ].map(([label, quota]) => (
                      <div className="settings-usage-card" key={label}>
                        <div className="settings-usage-header">
                          <span className="settings-usage-label">{label} remaining</span>
                          <span className="settings-usage-reset">{formatResetTime(quota.resets_at)}</span>
                        </div>
                        <div className="settings-usage-bar-wrap">
                          <div className="settings-usage-bar">
                            <div
                              className="settings-usage-bar-fill"
                              style={{ width: `${Math.min((quota.used / quota.limit) * 100, 100)}%` }}
                            />
                          </div>
                          <span className="settings-usage-count">{quota.remaining} / {quota.limit}</span>
                        </div>
                        <p className="settings-usage-note">{quota.used} counted chats used</p>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}

            {activeTab === "account" && (
              <div className="settings-section">
                <h3>Profile</h3>
                <div className="settings-account-card">
                  <div className="settings-avatar">
                    <User size={24} />
                  </div>
                  <div className="settings-account-info">
                    <strong>{user?.username || "Guest"}</strong>
                    <span>{user?.email || "No email"}</span>
                  </div>
                </div>

                <div className="settings-field">
                  <label className="settings-field-label" htmlFor="settings-username">Username</label>
                  <input
                    id="settings-username"
                    type="text"
                    className="settings-input full"
                    value={user?.username || ""}
                    disabled
                  />
                </div>
                <div className="settings-field">
                  <label className="settings-field-label" htmlFor="settings-email">Email</label>
                  <input
                    id="settings-email"
                    type="email"
                    className="settings-input full"
                    value={user?.email || ""}
                    disabled
                  />
                </div>

                <button className="settings-logout-btn" onClick={handleLogout}>
                  <LogOut size={16} />
                  Log out
                </button>
              </div>
            )}

            {billingAvailable && ProSettings && <ProSettings activeTab={activeTab} onClose={onClose} user={user} />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
