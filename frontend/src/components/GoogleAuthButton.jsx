import React from "react";

const GoogleMark = () => (
  <svg aria-hidden="true" viewBox="0 0 48 48" className="h-[18px] w-[18px]">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z" />
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.72 7.18l7.64 5.93c4.46-4.13 7.12-10.2 7.12-17.58Z" />
    <path fill="#FBBC05" d="M10.53 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.85 23.85 0 0 0 0 24c0 3.88.93 7.55 2.56 10.78l7.97-6.19Z" />
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.9-5.87l-7.64-5.93c-2.13 1.43-4.85 2.28-8.26 2.28-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z" />
  </svg>
);

const GoogleAuthButton = ({ label, loading = false, disabled = false, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled || loading}
    className="google-auth-button"
  >
    {loading ? (
      <span className="auth-spinner" aria-hidden="true" />
    ) : (
      <GoogleMark />
    )}
    <span>{loading ? "Connecting to Google…" : label}</span>
  </button>
);

export default GoogleAuthButton;
