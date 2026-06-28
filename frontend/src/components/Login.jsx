import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import FormField from "./FormField";
import noyaLogo from "../assets/noya-logo.svg";

const Login = () => {
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(formData.username, formData.password);
      navigate("/");
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || "We couldn't sign you in. Check your username and password.";
      setError(msg);
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-6 py-12">
      <div className="w-full max-w-[400px] animate-rise-in">
        <div className="mb-9 text-center">
          <img src={noyaLogo} alt="" className="mx-auto mb-5 h-11 w-11 rounded-[var(--radius-sm)]" />
          <h1 className="font-[var(--font-display)] text-[32px] font-semibold tracking-tight text-[var(--ink)]">
            Welcome back
          </h1>
          <p className="mt-2 text-[15px] text-[var(--ink-soft)]">
            Sign in to pick up where you left off.
          </p>
        </div>

        <div className="rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-7 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          {error && (
            <div
              role="alert"
              aria-live="polite"
              className="mb-5 rounded-[var(--radius-sm)] border border-[var(--error)]/30 bg-[var(--error-tint)] px-4 py-3 text-[14px] font-medium text-[var(--error)]"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <FormField
              id="username"
              label="Username"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              required
              autoComplete="username"
              spellCheck={false}
              placeholder="Enter your username…"
            />

            <FormField
              id="password"
              label="Password"
              type={showPassword ? "text" : "password"}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              autoComplete="current-password"
              spellCheck={false}
              placeholder="Enter your password…"
              trailing={
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  className="absolute right-3 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-[var(--radius-sm)] text-[var(--ink-faint)] transition-colors hover:bg-[var(--bg)] hover:text-[var(--ink)] focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
                >
                  {showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
                </button>
              }
            />

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex h-12 w-full items-center justify-center gap-2 rounded-[var(--radius-sm)] bg-[var(--pine)] text-[15px] font-semibold text-white transition-colors duration-150 hover:bg-[var(--pine-strong)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface)] disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading && (
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                  aria-hidden="true"
                />
              )}
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-[14px] text-[var(--ink-soft)]">
          Don&rsquo;t have an account?{" "}
          <Link
            to="/signup"
            className="font-semibold text-[var(--pine)] underline-offset-2 hover:underline focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
