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
    return getFriendlyApiError(error, { fallback: "We couldn't sign you in with Google. Please try again." });
  }
  if (error?.code === "auth/configuration-missing") return error.message;
  if (error?.code === "auth/unauthorized-domain") return "This website isn't on Firebase's authorized domains yet. Add the current domain in Firebase Console.";
  if (error?.code === "auth/popup-blocked") return "Your browser blocked the Google sign-in window. Allow pop-ups and try again.";
  if (error?.code === "auth/popup-closed-by-user") return "Google sign-in was closed before it finished. Try again when you're ready.";
  if (error?.code === "auth/network-request-failed") return "Google sign-in couldn't connect. Check your internet connection and try again.";
  return "We couldn't sign you in with Google. Please try again.";
};

const Login = () => {
  const [formData, setFormData] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const { login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading("password");
    try {
      await login(formData.username, formData.password);
      navigate("/");
    } catch (err) {
      setError(getFriendlyApiError(err, {
        fallback: "We couldn't sign you in. Check your username and password.",
        unauthorized: "Username or password is incorrect.",
      }));
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
      title="Welcome back"
      description="Sign in to pick up where you left off and keep your study streak going."
    >
      <div className="auth-form-heading">
        <h2>Sign in</h2>
        <p>Choose how you’d like to continue.</p>
      </div>

      {error && <div role="alert" aria-live="polite" className="auth-error">{error}</div>}

      <GoogleAuthButton
        label="Sign in with Google"
        loading={loading === "google"}
        disabled={Boolean(loading)}
        onClick={handleGoogleSignIn}
      />

      <div className="auth-divider" aria-hidden="true"><span>or use your username</span></div>

      <form onSubmit={handleSubmit} className="auth-form" noValidate>
        <FormField
          id="username"
          label="Username"
          value={formData.username}
          onChange={(event) => setFormData({ ...formData, username: event.target.value })}
          required
          autoComplete="username"
          spellCheck={false}
          placeholder="Enter your username"
        />
        <FormField
          id="password"
          label="Password"
          type={showPassword ? "text" : "password"}
          value={formData.password}
          onChange={(event) => setFormData({ ...formData, password: event.target.value })}
          required
          autoComplete="current-password"
          spellCheck={false}
          placeholder="Enter your password"
          trailing={(
            <button
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              className="auth-password-toggle"
            >
              {showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}
            </button>
          )}
        />
        <button type="submit" disabled={Boolean(loading)} className="auth-submit-button">
          {loading === "password" && <span className="auth-spinner auth-spinner-light" aria-hidden="true" />}
          {loading === "password" ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="auth-switch-prompt">
        New to Noya? <Link to="/signup">Create an account</Link>
      </p>
    </AuthLayout>
  );
};

export default Login;
