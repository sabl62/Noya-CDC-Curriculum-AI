import React from "react";
import noyaLogo from "../assets/noya-logo.svg";

const AuthLayout = ({ title, description, children }) => (
  <main className="auth-page">
    <div className="auth-shell">
      <section className="auth-brand-panel" aria-labelledby="auth-title">
        <a className="auth-brand" href="/" aria-label="Noya home">
          <img src={noyaLogo} alt="" />
          <span>Noya</span>
          <span className="auth-brand-period" aria-hidden="true">.</span>
        </a>
        <div className="auth-brand-copy">
          <h1 id="auth-title">{title}</h1>
          <p>{description}</p>
        </div>
        <div className="auth-brand-mark" aria-hidden="true">
          <span className="marginalia">Q.</span>
          <span />
        </div>
      </section>

      <section className="auth-form-panel" aria-label="Account access">
        <div className="auth-form-content">{children}</div>
      </section>
    </div>
    <p className="auth-footnote">A study companion for CDC-curriculum students</p>
  </main>
);

export default AuthLayout;
