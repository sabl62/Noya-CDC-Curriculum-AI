import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { getFriendlyApiError } from "../services/errors.js";
import { signInWithGoogle } from "../firebase/config";
import FormField from "./FormField";
import AuthLayout from "./AuthLayout";
import GoogleAuthButton from "./GoogleAuthButton";

const googleErrorMessage = (error) => {
  if (error?.response) {
    return getFriendlyApiError(error, { fallback: "We couldn't create your account with Google. Please try again." });
  }
  if (error?.code === "auth/configuration-missing") return error.message;
  if (error?.code === "auth/unauthorized-domain") return "This website isn't on Firebase's authorized domains yet. Add the current domain in Firebase Console.";
  if (error?.code === "auth/popup-blocked") return "Your browser blocked the Google sign-in window. Allow pop-ups and try again.";
  if (error?.code === "auth/popup-closed-by-user") return "Google sign-in was closed before it finished. Try again when you're ready.";
  if (error?.code === "auth/network-request-failed") return "Google sign-in couldn't connect. Check your internet connection and try again.";
  return "We couldn't create your account with Google. Please try again.";
};

const SignUp = () => {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    referralCode: new URLSearchParams(window.location.search).get("ref") || "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const { signup, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const passwordTooShort = formData.password.length > 0 && formData.password.length < 6;
  const passwordsMismatch = formData.confirmPassword.length > 0 && formData.password !== formData.confirmPassword;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords don't match.");
      return;
    }

    setLoading("password");
    try {
      await signup(formData.username, formData.email, formData.password, formData.referralCode);
      navigate("/");
    } catch (err) {
      setError(getFriendlyApiError(err, { fallback: "We couldn't create your account. Please try again." }));
      setLoading(null);
    }
  };

  const handleGoogleSignIn = async () => {
    setError("");
    setLoading("google");
    try {
      const idToken = await signInWithGoogle();
      await loginWithGoogle(idToken);
      navigate("/");
    } catch (err) {
      setError(googleErrorMessage(err));
      setLoading(null);
    }
  };

  return (
    <AuthLayout
      title="Join Noya"
      description="Create an account to start studying smarter, track your progress, and never lose your place."
    >
      <div className="auth-form-heading">
        <h2>Create your account</h2>
        <p>Get started with Google or your email.</p>
      </div>

      {error && <div role="alert" aria-live="polite" className="auth-error">{error}</div>}

      <GoogleAuthButton
        label="Sign up with Google"
        loading={loading === "google"}
        disabled={Boolean(loading)}
        onClick={handleGoogleSignIn}
      />

      <div className="auth-divider" aria-hidden="true"><span>or create with email</span></div>

      <form onSubmit={handleSubmit} className="auth-form" noValidate>
        <FormField
          id="username"
          label="Username"
          value={formData.username}
          onChange={(event) => setFormData({ ...formData, username: event.target.value })}
          required
          autoComplete="username"
          spellCheck={false}
          placeholder="Choose a username"
        />
        <FormField
          id="email"
          label="Email"
          type="email"
          inputMode="email"
          value={formData.email}
          onChange={(event) => setFormData({ ...formData, email: event.target.value })}
          required
          autoComplete="email"
          spellCheck={false}
          placeholder="you@example.com"
        />
        <FormField
          id="password"
          label="Password"
          type={showPassword ? "text" : "password"}
          value={formData.password}
          onChange={(event) => setFormData({ ...formData, password: event.target.value })}
          required
          autoComplete="new-password"
          spellCheck={false}
          placeholder="At least 6 characters"
          error={passwordTooShort ? "Needs at least 6 characters." : undefined}
          trailing={(
            <button
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Hide passwords" : "Show passwords"}
              aria-pressed={showPassword}
              className="auth-password-toggle"
            >
              {showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
            </button>
          )}
        />
        <FormField
          id="confirmPassword"
          label="Confirm password"
          type={showPassword ? "text" : "password"}
          value={formData.confirmPassword}
          onChange={(event) => setFormData({ ...formData, confirmPassword: event.target.value })}
          required
          autoComplete="new-password"
          spellCheck={false}
          placeholder="Re-enter your password"
          error={passwordsMismatch ? "Passwords don't match." : undefined}
        />
        <button type="submit" disabled={Boolean(loading)} className="auth-submit-button">
          {loading === "password" && <span className="auth-spinner auth-spinner-light" aria-hidden="true" />}
          {loading === "password" ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="auth-switch-prompt">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
};

export default SignUp;
