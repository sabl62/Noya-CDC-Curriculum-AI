import React, { useEffect, useState } from "react";
import {
  LogOut,
  Moon,
  Sun,
  Trash2,
  User,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

const PRO_SETTINGS_MODULES = import.meta.glob("../pro/SettingsPro.jsx", { eager: true });
const ProSettings = PRO_SETTINGS_MODULES["../pro/SettingsPro.jsx"]?.default;
const proSettingsTabs = PRO_SETTINGS_MODULES["../pro/SettingsPro.jsx"]?.tabs || [];

const SETTINGS_KEYS = {
  THEME: "theme",
  CONTEXT_MEMORY: "noya_context_memory",
  USAGE_DATE: "noya_usage_date",
  USAGE_COUNT: "noya_usage_count",
  FREE_RESETS_LEFT: "noya_free_resets_left",
};

const getToday = () => new Date().toISOString().slice(0, 10);

const getUsageData = () => {
  const date = localStorage.getItem(SETTINGS_KEYS.USAGE_DATE);
  const count = parseInt(localStorage.getItem(SETTINGS_KEYS.USAGE_COUNT) || "0", 10);
  const freeResets = parseInt(localStorage.getItem(SETTINGS_KEYS.FREE_RESETS_LEFT) || "3", 10);
  const today = getToday();
  if (date !== today) {
    localStorage.setItem(SETTINGS_KEYS.USAGE_DATE, today);
    localStorage.setItem(SETTINGS_KEYS.USAGE_COUNT, "0");
    localStorage.setItem(SETTINGS_KEYS.FREE_RESETS_LEFT, "3");
    return { count: 0, freeResetsLeft: 3, resetInHours: 24 - new Date().getHours() };
  }
  return { count, freeResetsLeft: freeResets, resetInHours: 24 - new Date().getHours() };
};

const SettingsModal = ({ onClose, theme, onToggleTheme, billingAvailable = false }) => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("general");
  const [contextMemory, setContextMemory] = useState(() => {
    return localStorage.getItem(SETTINGS_KEYS.CONTEXT_MEMORY) !== "false";
  });
  const [usage, setUsage] = useState(getUsageData);

  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  const handleContextMemoryToggle = () => {
    const next = !contextMemory;
    setContextMemory(next);
    localStorage.setItem(SETTINGS_KEYS.CONTEXT_MEMORY, String(next));
  };

  const handleResetUsage = () => {
    const data = getUsageData();
    if (data.freeResetsLeft > 0) {
      const next = data.freeResetsLeft - 1;
      localStorage.setItem(SETTINGS_KEYS.FREE_RESETS_LEFT, String(next));
      localStorage.setItem(SETTINGS_KEYS.USAGE_COUNT, "0");
      setUsage({ ...getUsageData(), freeResetsLeft: next, count: 0 });
    }
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
                <h3>Daily Usage</h3>
                <div className="settings-usage-card">
                  <div className="settings-usage-header">
                    <span className="settings-usage-label">Messages today</span>
                    <span className="settings-usage-reset">Resets in {usage.resetInHours}h</span>
                  </div>
                  <div className="settings-usage-bar-wrap">
                    <div className="settings-usage-bar">
                      <div
                        className="settings-usage-bar-fill"
                        style={{ width: `${Math.min((usage.count / 50) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="settings-usage-count">{usage.count} / 50</span>
                  </div>
                  <p className="settings-usage-note">Demo limit — no actual cap enforced yet</p>
                </div>

                <h3>Reset Usage</h3>
                <div className="settings-reset-card">
                  <div className="settings-reset-info">
                    <span className="settings-reset-label">Free resets remaining</span>
                    <span className="settings-reset-count">{usage.freeResetsLeft} / 3</span>
                  </div>
                  <p className="settings-reset-desc">
                    After free resets are used, each reset costs Rs. 50.
                  </p>
                  <button
                    className="settings-reset-btn"
                    onClick={handleResetUsage}
                    disabled={usage.freeResetsLeft <= 0 || usage.count === 0}
                  >
                    Reset now
                  </button>
                </div>
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
