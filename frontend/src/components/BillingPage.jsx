import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  CreditCard,
  Headphones,
  Info,
  Loader2,
  Shield,
  Smartphone,
  Wallet,
  X,
  Zap,
  AlertCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { authAPI, billingAPI } from "../services/api";

const PRO_FEATURES = [
  "10x more usage than Free",
  "Smart AI models",
  "PYQ analysis",
  "Practice questions from SEE papers",
  "Custom API key",
  "Extension support — add your own books & question sets",
];

const FALLBACK_PLAN = {
  id: "pro",
  name: "Noya Pro",
  amount: 799,
  currency: "NPR",
  price: "Rs. 799",
};

const PROVIDER_META = {
  esewa: {
    label: "eSewa",
    hint: "Pay with your eSewa wallet",
    icon: Wallet,
  },
  khalti: {
    label: "Khalti",
    hint: "Pay with your Khalti wallet",
    icon: Smartphone,
  },
  stripe: {
    label: "Credit / Debit card",
    hint: "Visa, Mastercard via Stripe",
    icon: CreditCard,
  },
};

const NOTICE_ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
};

const BillingPage = ({ theme, onToggleTheme }) => {
  const { user, setUser, isLoggedIn } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [plansData, setPlansData] = useState(null);
  const [plansLoaded, setPlansLoaded] = useState(false);
  const [showMethods, setShowMethods] = useState(false);
  const [processing, setProcessing] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [notice, setNotice] = useState(null);

  const isPro = user?.plan_tier === "paid";
  const plan = useMemo(
    () => plansData?.plans?.find((p) => p.id === "pro") || FALLBACK_PLAN,
    [plansData]
  );
  const providers = useMemo(() => {
    const list = plansData?.providers?.filter((p) => p.enabled) || [];
    return list;
  }, [plansData]);
  const priceLabel = plan.amount ? `Rs. ${plan.amount}` : plan.price;

  useEffect(() => {
    billingAPI
      .getPlans()
      .then(setPlansData)
      .catch(() => setPlansData(null))
      .finally(() => setPlansLoaded(true));
  }, []);

  const refreshUser = async () => {
    try {
      const res = await authAPI.getCurrentUser();
      if (res?.data) {
        setUser(res.data);
        localStorage.setItem("user", JSON.stringify(res.data));
      }
    } catch {
      /* keep the cached user; status endpoint is still authoritative */
    }
  };

  const handleVerifyResult = async (result) => {
    if (result?.status === "completed") {
      await refreshUser();
      setNotice({
        type: "success",
        message: "Payment confirmed — Noya Pro is now active for 1 year.",
      });
    } else if (["pending", "initiated"].includes(result?.status)) {
      setNotice({
        type: "info",
        message: "Payment received and awaiting gateway confirmation. Pro activates as soon as it clears.",
      });
    } else if (result?.status === "refunded") {
      setNotice({ type: "info", message: "That payment has been refunded." });
    } else {
      setNotice({
        type: "error",
        message: "Payment was not completed — you have not been charged.",
      });
    }
  };

  // Handle the return leg from eSewa (?data=), Khalti (?pidx=) and Stripe (?billing=).
  useEffect(() => {
    const esewaData = searchParams.get("data");
    const khaltiPidx = searchParams.get("pidx");
    const stripeFlow = searchParams.get("billing");
    if (!esewaData && !khaltiPidx && !stripeFlow) return;

    let cancelled = false;

    const run = async () => {
      setVerifying(true);
      try {
        if (esewaData) {
          const result = await billingAPI.verifyPayment({ provider: "esewa", data: esewaData });
          if (!cancelled) await handleVerifyResult(result);
        } else if (khaltiPidx) {
          const result = await billingAPI.verifyPayment({ provider: "khalti", reference: khaltiPidx });
          if (!cancelled) await handleVerifyResult(result);
        } else if (stripeFlow === "cancel") {
          setNotice({ type: "info", message: "Payment cancelled — you have not been charged." });
        } else if (stripeFlow === "success") {
          await refreshUser();
          setNotice({ type: "success", message: "Payment received. Welcome to Noya Pro!" });
        }
      } catch (err) {
        if (!cancelled) {
          setNotice({
            type: "error",
            message:
              err?.response?.data?.error ||
              "We could not verify that payment. If you were charged, contact support.",
          });
        }
      } finally {
        if (!cancelled) {
          setVerifying(false);
          setSearchParams({}, { replace: true });
        }
      }
    };

    run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitPostForm = (action, fields) => {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = action;
    Object.entries(fields).forEach(([name, value]) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = name;
      input.value = value;
      form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
  };

  const startCheckout = async (providerId) => {
    if (!isLoggedIn) {
      navigate("/login");
      return;
    }
    setProcessing(providerId);
    setNotice(null);
    try {
      const res = await billingAPI.createCheckoutSession("pro", providerId);
      if (res?.checkout_url && res?.method === "post") {
        submitPostForm(res.checkout_url, res.form_fields || {});
        return; // browser navigates away
      }
      if (res?.checkout_url) {
        window.location.href = res.checkout_url;
        return;
      }
      setNotice({
        type: "error",
        message: res?.error || "This payment method is not set up yet. Please try another one.",
      });
      setProcessing("");
    } catch (err) {
      setNotice({
        type: "error",
        message: err?.response?.data?.error || "Could not start checkout. Please try again.",
      });
      setProcessing("");
    }
  };

  const openCheckout = () => {
    if (providers.length === 1) {
      startCheckout(providers[0].id);
      return;
    }
    setShowMethods(true);
  };

  const NoticeBanner = notice && (
    <div className={`billing-notice ${notice.type}`} role="status">
      {React.createElement(NOTICE_ICONS[notice.type] || Info, { size: 18 })}
      <span>{notice.message}</span>
      <button type="button" className="billing-notice-close" onClick={() => setNotice(null)} aria-label="Dismiss">
        <X size={14} />
      </button>
    </div>
  );

  const verifyingBanner = verifying && (
    <div className="billing-notice info" role="status">
      <Loader2 size={18} className="billing-spin" />
      <span>Verifying your payment with the gateway…</span>
    </div>
  );

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

        {verifyingBanner}
        {NoticeBanner}

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
                <span className="billing-amount">{priceLabel}</span>
                <span className="billing-period">/year</span>
              </div>
            </div>
            <ul className="billing-features">
              {PRO_FEATURES.map((feature) => (
                <li key={feature}><Check size={16} /> {feature}</li>
              ))}
            </ul>
            {isPro ? (
              <div className="billing-current">
                {user?.billing_expires_at
                  ? `Pro active until ${new Date(user.billing_expires_at).toLocaleDateString()}`
                  : "Current plan"}
              </div>
            ) : (
              <button
                className="billing-upgrade-btn"
                onClick={openCheckout}
                disabled={processing || verifying || !plansLoaded}
              >
                {processing ? (
                  <><Loader2 size={16} className="billing-spin" /> Redirecting…</>
                ) : (
                  <><CreditCard size={16} /> Upgrade now</>
                )}
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
              <p>Yes. Payments are processed by eSewa and Khalti over encrypted, PCI-compliant gateways. We never store card or wallet details.</p>
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

      {showMethods && (
        <div className="billing-modal-overlay" onClick={() => setShowMethods(false)}>
          <div className="billing-modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <button type="button" className="billing-modal-close" onClick={() => setShowMethods(false)} aria-label="Close">
              <X size={18} />
            </button>
            <h3>Choose payment method</h3>
            <p className="billing-modal-sub">
              {plan.name} — {priceLabel} for 1 year
            </p>

            <div className="billing-methods">
              {providers.map((provider) => {
                const meta = PROVIDER_META[provider.id] || {
                  label: provider.name,
                  hint: provider.description || "",
                  icon: Wallet,
                };
                const Icon = meta.icon;
                const busy = processing === provider.id;
                return (
                  <button
                    key={provider.id}
                    type="button"
                    className={`billing-method-btn ${provider.id}`}
                    onClick={() => startCheckout(provider.id)}
                    disabled={!!processing}
                  >
                    <span className={`billing-method-icon ${provider.id}`}>
                      <Icon size={20} />
                    </span>
                    <span className="billing-method-text">
                      <strong>{meta.label}</strong>
                      <small>{meta.hint}</small>
                    </span>
                    {busy ? (
                      <Loader2 size={18} className="billing-spin" />
                    ) : (
                      <ArrowRight size={18} />
                    )}
                  </button>
                );
              })}

              {providers.length === 0 && (
                <p className="billing-modal-empty">
                  Online payments are not configured yet. Add your eSewa / Khalti keys in
                  <code> backend-main/.env</code> to enable checkout.
                </p>
              )}
            </div>

            <p className="billing-modal-note">
              <Shield size={14} />
              You will be redirected to the gateway to approve the payment. Pro activates after
              the gateway confirms it.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default BillingPage;
