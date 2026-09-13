import React, { useEffect, useState } from "react";
import {
  CreditCard,
  Eye,
  EyeOff,
  Key,
  LogOut,
  Moon,
  Sun,
  Trash2,
  User,
  Zap,
  AlertTriangle,
  Check,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

const SETTINGS_KEYS = {
  THEME: "theme",
  CONTEXT_MEMORY: "noya_context_memory",
  CUSTOM_API_KEY: "noya_custom_api_key",
  USAGE_DATE: "noya_usage_date",
  USAGE_COUNT: "noya_usage_count",
  FREE_RESETS_LEFT: "noya_free_resets_left",
  BILLING_EMAIL: "noya_billing_email",
  BILLING_PHONE: "noya_billing_phone",
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

const SettingsModal = ({ onClose, theme, onToggleTheme }) => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("general");
  const [contextMemory, setContextMemory] = useState(() => {
    return localStorage.getItem(SETTINGS_KEYS.CONTEXT_MEMORY) !== "false";
  });
  const [apiKey, setApiKey] = useState(() => localStorage.getItem(SETTINGS_KEYS.CUSTOM_API_KEY) || "");
  const [showApiKey, setShowApiKey] = useState(false);
  const [apiKeySaved, setApiKeySaved] = useState(false);
  const [usage, setUsage] = useState(getUsageData);
  const [billingEmail, setBillingEmail] = useState(() => localStorage.getItem(SETTINGS_KEYS.BILLING_EMAIL) || user?.email || "");
  const [billingPhone, setBillingPhone] = useState(() => localStorage.getItem(SETTINGS_KEYS.BILLING_PHONE) || "");
  const [billingEmailSaved, setBillingEmailSaved] = useState(false);
  const [billingPhoneSaved, setBillingPhoneSaved] = useState(false);

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

  const handleSaveApiKey = () => {
    if (apiKey.trim()) {
      localStorage.setItem(SETTINGS_KEYS.CUSTOM_API_KEY, apiKey.trim());
    } else {
      localStorage.removeItem(SETTINGS_KEYS.CUSTOM_API_KEY);
    }
    setApiKeySaved(true);
    setTimeout(() => setApiKeySaved(false), 2000);
  };

  const handleDeleteApiKey = () => {
    setApiKey("");
    localStorage.removeItem(SETTINGS_KEYS.CUSTOM_API_KEY);
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

  const handleSaveBillingEmail = () => {
    localStorage.setItem(SETTINGS_KEYS.BILLING_EMAIL, billingEmail);
    setBillingEmailSaved(true);
    setTimeout(() => setBillingEmailSaved(false), 2000);
  };

  const handleSaveBillingPhone = () => {
    localStorage.setItem(SETTINGS_KEYS.BILLING_PHONE, billingPhone);
    setBillingPhoneSaved(true);
    setTimeout(() => setBillingPhoneSaved(false), 2000);
  };

  const handleLogout = () => {
    onClose();
    logout();
  };

  const tabs = [
    { id: "general", label: "General" },
    { id: "billing", label: "Billing" },
    { id: "usage", label: "Usage" },
    { id: "account", label: "Account" },
    { id: "config", label: "Configuration" },
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

                {user?.plan_tier !== "paid" && (
                  <div className="settings-upgrade-card">
                    <div className="settings-upgrade-icon"><Zap size={20} /></div>
                    <div className="settings-upgrade-info">
                      <strong>Upgrade to Pro</strong>
                      <span>Unlock unlimited usage, priority responses, and more</span>
                    </div>
                    <a href="/billing" className="settings-upgrade-btn" onClick={onClose}>Upgrade</a>
                  </div>
                )}
              </div>
            )}

            {activeTab === "billing" && (
              <div className="settings-section">
                <h3>Subscription</h3>
                <div className="settings-plan-card">
                  <div className="settings-plan-header">
                    <span className={`plan-badge ${user?.plan_tier === "paid" ? "paid" : "free"}`}>
                      {user?.plan_tier === "paid" ? "Pro" : "Free"}
                    </span>
                    {user?.plan_tier === "paid" && <span className="settings-plan-active">Active</span>}
                  </div>
                  {user?.plan_tier !== "paid" && (
                    <div className="settings-plan-details">
                      <div className="settings-price">
                        <span className="settings-price-amount">Rs. 799</span>
                        <span className="settings-price-period">/year</span>
                      </div>
                      <ul className="settings-plan-features">
                        <li>10x more usage than Free</li>
                        <li>Smart AI models</li>
                        <li>PYQ analysis</li>
                        <li>Practice questions from SEE papers</li>
                        <li>Custom API key</li>
                        <li>Extension support — add your own books &amp; question sets</li>
                      </ul>
                      <a href="/billing" className="settings-full-upgrade-btn" onClick={onClose}>
                        <CreditCard size={16} />
                        Upgrade to Pro — Rs. 799/year
                      </a>
                    </div>
                  )}
                </div>

                <h3>Billing Information</h3>
                <div className="settings-field">
                  <label className="settings-field-label">Billing email</label>
                  <div className="settings-field-row">
                    <input
                      type="email"
                      className="settings-input"
                      value={billingEmail}
                      onChange={(e) => setBillingEmail(e.target.value)}
                      placeholder="your@email.com"
                    />
                    <button className="settings-save-btn" onClick={handleSaveBillingEmail}>
                      {billingEmailSaved ? <Check size={14} /> : "Save"}
                    </button>
                  </div>
                </div>
                <div className="settings-field">
                  <label className="settings-field-label">Billing phone</label>
                  <div className="settings-field-row">
                    <input
                      type="tel"
                      className="settings-input"
                      value={billingPhone}
                      onChange={(e) => setBillingPhone(e.target.value)}
                      placeholder="+977 98XXXXXXXX"
                    />
                    <button className="settings-save-btn" onClick={handleSaveBillingPhone}>
                      {billingPhoneSaved ? <Check size={14} /> : "Save"}
                    </button>
                  </div>
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

            {activeTab === "config" && (
              <div className="settings-section">
                <h3>Custom API Key</h3>
                {user?.plan_tier !== "paid" ? (
                  <div className="settings-pro-locked">
                    <Key size={20} />
                    <div className="settings-pro-locked-info">
                      <strong>Pro feature</strong>
                      <span>Upgrade to Pro to use your own custom API key for a personalised experience.</span>
                    </div>
                    <a href="/billing" className="settings-upgrade-btn" onClick={onClose}>Upgrade</a>
                  </div>
                ) : (
                  <>
                    <p className="settings-config-desc">
                      Add your own API key to use your personal AI provider account. This key is stored locally on your device and is never sent to our servers.
                    </p>
                    <div className="settings-api-warning">
                      <AlertTriangle size={16} />
                      <span>An API key of a lower intelligence model can reduce the response quality significantly.</span>
                    </div>
                    <div className="settings-field">
                      <label className="settings-field-label">API Key</label>
                      <div className="settings-field-row">
                        <div className="settings-api-input-wrap">
                          <input
                            type={showApiKey ? "text" : "password"}
                            className="settings-input"
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder="sk-..."
                          />
                          <button
                            className="settings-api-toggle"
                            onClick={() => setShowApiKey((v) => !v)}
                            aria-label={showApiKey ? "Hide key" : "Show key"}
                          >
                            {showApiKey ? <EyeOff size={14} /> : <Eye size={14} />}
                          </button>
                        </div>
                        <button className="settings-save-btn" onClick={handleSaveApiKey}>
                          {apiKeySaved ? <Check size={14} /> : "Save"}
                        </button>
                      </div>
                    </div>
                    {apiKey && (
                      <button className="settings-delete-btn" onClick={handleDeleteApiKey}>
                        <Trash2 size={14} />
                        Remove API key
                      </button>
                    )}
                    <div className="settings-api-note">
                      <Key size={14} />
                      <span>Your key is stored in localStorage and never leaves your browser.</span>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;
