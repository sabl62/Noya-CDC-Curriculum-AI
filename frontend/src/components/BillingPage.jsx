import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Check, CreditCard, Shield, Zap, Clock, Headphones } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

const PRO_FEATURES = [
  "10x more usage than Free",
  "Smart AI models",
  "PYQ analysis",
  "Practice questions from SEE papers",
  "Custom API key",
  "Extension support — add your own books & question sets",
];

const BillingPage = ({ theme, onToggleTheme }) => {
  const { user } = useAuth();
  const isPro = user?.plan_tier === "paid";

  return (
    <div className="billing-page">
      <nav className="billing-nav">
        <Link to="/chat" className="billing-back">
          <ArrowLeft size={18} />
          Back to chat
        </Link>
      </nav>

      <main className="billing-main">
        <div className="billing-hero">
          <span className="billing-badge">Pricing</span>
          <h1>Upgrade to <span className="billing-highlight">Pro</span></h1>
          <p>Get unlimited access to Noya AI and supercharge your learning</p>
        </div>

        <div className="billing-cards">
          <div className="billing-plan-card free">
            <div className="billing-plan-header">
              <h3>Free</h3>
              <div className="billing-price">
                <span className="billing-amount">Rs. 0</span>
                <span className="billing-period">forever</span>
              </div>
            </div>
            <ul className="billing-features">
              <li><Check size={16} /> Limited daily questions</li>
              <li><Check size={16} /> Standard AI models</li>
              <li><Check size={16} /> Basic chat history</li>
              <li className="disabled"><Check size={16} /> Custom API key</li>
              <li className="disabled"><Check size={16} /> PYQ analysis</li>
              <li className="disabled"><Check size={16} /> Extension support</li>
            </ul>
            {isPro ? (
              <div className="billing-current">Current plan</div>
            ) : (
              <div className="billing-current active">Your current plan</div>
            )}
          </div>

          <div className="billing-plan-card pro">
            <div className="billing-plan-popular">Most popular</div>
            <div className="billing-plan-header">
              <h3>Pro</h3>
              <div className="billing-price">
                <span className="billing-amount">Rs. 799</span>
                <span className="billing-period">/year</span>
              </div>
            </div>
            <ul className="billing-features">
              {PRO_FEATURES.map((feature) => (
                <li key={feature}><Check size={16} /> {feature}</li>
              ))}
            </ul>
            {isPro ? (
              <div className="billing-current">Current plan</div>
            ) : (
              <button className="billing-upgrade-btn">
                <CreditCard size={16} />
                Upgrade now
              </button>
            )}
          </div>
        </div>

        <div className="billing-faqs">
          <h2>Frequently asked questions</h2>
          <div className="billing-faq-grid">
            <div className="billing-faq">
              <div className="billing-faq-icon"><Zap size={18} /></div>
              <h4>What happens when I upgrade?</h4>
              <p>Your Pro features activate instantly. No waiting, no downtime.</p>
            </div>
            <div className="billing-faq">
              <div className="billing-faq-icon"><Shield size={18} /></div>
              <h4>Is my payment secure?</h4>
              <p>Yes. Payments are processed through secure, encrypted gateways. We never store card details.</p>
            </div>
            <div className="billing-faq">
              <div className="billing-faq-icon"><Clock size={18} /></div>
              <h4>Can I cancel anytime?</h4>
              <p>Absolutely. Cancel anytime from your settings. You keep Pro access until the billing period ends.</p>
            </div>
            <div className="billing-faq">
              <div className="billing-faq-icon"><Headphones size={18} /></div>
              <h4>Need help?</h4>
              <p>Contact our support team at support@noya.ai for any billing questions.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default BillingPage;
