import React, { useEffect, useState } from "react";
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

  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
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

  const tabs = [
    { id: "general", label: "General" },
    ...(billingAvailable && ProSettings ? proSettingsTabs : []),
    { id: "usage", label: "Usage" },
    { id: "account", label: "Account" },
  ];

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="settings-close-btn" onClick={onClose} aria-label="Close settings">
            <X size={18} />
          </button>
        </div>

        <div className="settings-body">
          <nav className="settings-tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={`settings-tab ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="settings-content">
            {activeTab === "general" && (
              <div className="settings-section">
                <h3>Appearance</h3>
                <div className="settings-row">
                  <div className="settings-row-info">
                    <span className="settings-row-label">Theme</span>
                    <span className="settings-row-desc">Switch between light and dark mode</span>
                  </div>
                  <button className="settings-toggle-btn" onClick={onToggleTheme}>
                    {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
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
                    role="switch"
                    aria-checked={contextMemory}
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
                  <label className="settings-field-label">Username</label>
                  <input
                    type="text"
                    className="settings-input full"
                    value={user?.username || ""}
                    disabled
                  />
                </div>
                <div className="settings-field">
                  <label className="settings-field-label">Email</label>
                  <input
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
