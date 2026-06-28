import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import FormField from "./FormField";
import noyaLogo from "../assets/noya-logo.svg";

const SignUp = () => {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    referralCode: new URLSearchParams(window.location.search).get("ref") || "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();

  const passwordTooShort = formData.password.length > 0 && formData.password.length < 6;
  const passwordsMismatch = formData.confirmPassword.length > 0 && formData.password !== formData.confirmPassword;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setLoading(true);
    try {
      await signup(formData.username, formData.email, formData.password, formData.referralCode);
      navigate("/");
    } catch (err) {
      setError(err.message || "We couldn't create your account. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg)] px-6 py-12">
      <div className="w-full max-w-[400px] animate-rise-in">
        <div className="mb-9 text-center">
          <img src={noyaLogo} alt="" className="mx-auto mb-5 h-11 w-11 rounded-[var(--radius-sm)]" />
          <h1 className="font-[var(--font-display)] text-[32px] font-semibold tracking-tight text-[var(--ink)]">
            Join Noya
          </h1>
          <p className="mt-2 text-[15px] text-[var(--ink-soft)]">
            Create an account to start studying.
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
              placeholder="Choose a username…"
            />

            <FormField
              id="email"
              label="Email"
              type="email"
              inputMode="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              autoComplete="email"
              spellCheck={false}
              placeholder="your@email.com"
            />

            <FormField
              id="password"
              label="Password"
              type={showPassword ? "text" : "password"}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              autoComplete="new-password"
              spellCheck={false}
              placeholder="At least 6 characters…"
              error={passwordTooShort ? "Needs at least 6 characters." : undefined}
              trailing={
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Hide passwords" : "Show passwords"}
                  aria-pressed={showPassword}
                  className="absolute right-3 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-[var(--radius-sm)] text-[var(--ink-faint)] transition-colors hover:bg-[var(--bg)] hover:text-[var(--ink)] focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
                >
                  {showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
                </button>
              }
            />

            <FormField
              id="confirmPassword"
              label="Confirm Password"
              type={showPassword ? "text" : "password"}
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              required
              autoComplete="new-password"
              spellCheck={false}
              placeholder="Confirm your password…"
              error={passwordsMismatch ? "Passwords don't match." : undefined}
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
              {loading ? "Creating account…" : "Sign Up"}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-[14px] text-[var(--ink-soft)]">
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-semibold text-[var(--pine)] underline-offset-2 hover:underline focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pine)]/40"
          >
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
};

export default SignUp;
