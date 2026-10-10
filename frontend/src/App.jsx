import React, { useEffect, useState, useCallback } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  Link,
} from "react-router-dom";
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  Compass,
  GraduationCap,
  LibraryBig,
  MessageCircle,
  MoonStar,
  Quote,
  ShieldCheck,
  Sparkles,
  SunMedium,
  Target,
} from "lucide-react";

import ChatView from "./components/ChatView.jsx";
import SubjectSelection from "./components/SubjectSelection.jsx";
import Login from "./components/Login.jsx";
import Signup from "./components/SignUp.jsx";
import { useAuth, AuthProvider } from "./context/AuthContext.jsx";
import { authAPI } from "./services/api";
import noyaLogo from "./assets/noya-logo.svg";

// Vite includes whichever optional Pro UI modules are present in the build.
// An empty glob keeps the base app buildable when billing UI is removed.
const PRO_UI_MODULES = import.meta.glob("./pro/{BillingPage,ChatProFeatures,SettingsPro}.jsx", { eager: true });
const BillingPage = PRO_UI_MODULES["./pro/BillingPage.jsx"]?.default || null;
const proUiAvailable = Boolean(
  BillingPage &&
  PRO_UI_MODULES["./pro/ChatProFeatures.jsx"] &&
  PRO_UI_MODULES["./pro/SettingsPro.jsx"]
);

const ProtectedRoute = ({ children }) => {
  const { isLoggedIn, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <img src={noyaLogo} alt="" className="h-12 w-12 animate-[spin_1.5s_linear_infinite]" />
      </div>
    );
  }
  return isLoggedIn ? children : <Navigate to="/login" replace />;
};

const FeatureCard = ({ icon: Icon, title, description }) => (
  <div className="landing-card group">
    <div className="landing-icon">
      <Icon size={20} aria-hidden="true" />
    </div>
    <h3>{title}</h3>
    <p>{description}</p>
  </div>
);

const ProcessStep = ({ count, title, description }) => (
  <div className="process-step">
    <span>{count}</span>
    <div>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  </div>
);

const PublicShell = ({ theme = "dark", onToggleTheme }) => (
  <div className="landing-page min-h-screen bg-[var(--bg)] text-[var(--ink)] transition-colors duration-300">
    <section className="landing-hero">
       {/* <div className="hero-scene" aria-hidden="true"> */}
        {/* <div className="desk-grid" /> */}
         {/* <div className="study-window window-main"> */}
          {/* <div className="window-bar">
            <span />
            <span />
            <span />
          </div>
          <div className="chat-lines">
            <div className="line-question">Explain photosynthesis like I am revising tonight.</div>
            <div className="line-answer">Plants use sunlight to turn water and carbon dioxide into food. Oxygen is released as a by-product.</div>
            <div className="line-source">Class 10 Science / Life Process</div>
          </div> */}
        {/* </div>  */}
        {/* <div className="study-window window-note">
          <span className="note-label">Quick plan</span>
          <strong>Study 25 minutes</strong>
          <p>Ask, check, write it in your own words.</p>
        </div> */}
        {/* <div className="floating-chip chip-one">Exact chapter</div>
        <div className="floating-chip chip-two">Clear answer</div>
        <div className="floating-chip chip-three">No noise</div> */}
      {/* </div>  */}

      <header className="landing-nav">
        <Link to="/" className="brand-lockup" aria-label="Noya home">
          <img src={noyaLogo} alt="" />
          <span>Noya</span>
        </Link>
        <nav aria-label="Landing page">
          <a href="#features">Features</a>
          <a href="#method">Method</a>
          <a href="#faq">FAQ</a>
        </nav>
        <div className="nav-actions">
          <button onClick={onToggleTheme} className="theme-button" aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}>
            {theme === "dark" ? <SunMedium size={18} aria-hidden="true" /> : <MoonStar size={18} aria-hidden="true" />}
          </button>
          <Link to="/login" className="nav-login">Login</Link>
        </div>
      </header>

      <div className="hero-copy">
        {/* <div className="hero-kicker">
          <Sparkles size={16} aria-hidden="true" />
          <span>Built for focused Grade 10 study</span>
        </div> */}
        <h1>Noya</h1>
        <br></br>
        <p>
          An AI RAG system built for Grade 10 students following the CDC Curriculum        </p>
        <div className="hero-actions">
          <Link to="/signup" className="primary-cta">
            Start studying <ArrowRight size={18} aria-hidden="true" />
          </Link>
          <Link to="/login" className="secondary-cta">Log In</Link>
        </div>
      </div>
    </section>

    <main>


      <section id="features" className="landing-section">
        <div className="section-heading">
          
          <h2>Ask it, Understand it.</h2>
          <p>Noya keeps the experience centered on one thing: asking better questions and getting answers you can actually study from.</p>
        </div>
        <div className="feature-grid">
          <FeatureCard
            icon={MessageCircle}
            title="Ask naturally"
            description="Type the question the way you would ask a friend, then get a direct answer without opening five tabs."
          />
          <FeatureCard
            icon={BookOpenCheck}
            title="Stay on the lesson"
            description="Answers are shaped around the selected subject and chapter, so revision stays close to class material."
          />
          <FeatureCard
            icon={Target}
            title="Find the point"
            description="Long textbook sections become small, useful explanations with definitions, examples, and next steps."
          />
          <FeatureCard
            icon={Clock3}
            title="Revise faster"
            description="Use short study loops before exams: ask, compare, clarify, and write your final version."
          />
        </div>
      </section>

      
      <section id="method" className="landing-section method-section">
        <div className="section-heading">
          <h2>Clarity over qauntity</h2>
          <p>Instead of dumping information, Noya helps students move from confusion to confidence in a few clear steps.</p>
        </div>
        <div className="process-grid">
          <ProcessStep count="01" title="Pick a subject" description="Choose the class material you are working on and keep the conversation focused." />
          <ProcessStep count="02" title="Ask the doubt" description="Use everyday language, a textbook sentence, or a rough question from class." />
          <ProcessStep count="03" title="Get a clean explanation" description="Read the answer, ask follow-ups, and turn it into notes you understand." />
        </div>
      </section>

      <section className="landing-section">
        <div className="section-heading">
          <h2>The essentials, without extra clutter.</h2>
        </div>
        <div className="detail-grid">
          <div>
            <LibraryBig size={22} aria-hidden="true" />
            <h3>Organized Study</h3>
            <p>Keep study conversations organized around the lesson you are actually revising.</p>
          </div>
          <div>
            <Compass size={22} aria-hidden="true" />
            <h3>Guided clarity</h3>
            <p>Ask for definitions, examples, summaries, comparisons, or simpler wording.</p>
          </div>
          <div>
            <ShieldCheck size={22} aria-hidden="true" />
            <h3>No distractions</h3>
            <p>A simple UI, with Answers that goes through layers of Grounding checks</p>
          </div>
          <div>
            <GraduationCap size={22} aria-hidden="true" />
            <h3>Exam-friendly tone</h3>
            <p>Answers are Understandable, Solutions are simple, and Responses are readable</p>
          </div>
        </div>
      </section>

      <section className="quote-band">
        <p>
          <strong>Noya</strong> -Shortest path from confusion to conclusion. 
        </p>
      </section>

      <section id="faq" className="landing-section faq-section">
        <div className="section-heading">
          <h2>Before you begin.</h2>
        </div>
        <div className="faq-list">
          <details open>
            <summary>Is this only for chatting?</summary>
            <p>Yes. The product is centered on a focused study chat so students do not have to jump between extra tools.</p>
          </details>
          <details>
            <summary>Can I ask a question from the textbook?</summary>
            <p>Yes. Ask like: Solve Question (x) from Exercise/Lesson (y).</p>
          </details>
          <details>
            <summary>Can it help me with homework?</summary>
            <p>Yes. Yes, Noya is capable of identifying a question from the textbook, and its solution even when procided with just a page number.</p>
          </details>
        </div>
      </section>

      <section className="final-cta">
        <h2>Clear that Doubt, NOW!</h2>
        <Link to="/signup" className="primary-cta">
          Create account <ArrowRight size={18} aria-hidden="true" />
        </Link>
      </section>
    </main>

    <footer className="landing-footer">
      <div className="brand-lockup">
        <img src={noyaLogo} alt="" />
        <span>Noya</span>
      </div>
      <p>Made by Grade 10, Made for Grade 10</p>
      <div>
        <Link to="/login">Login</Link>
        <Link to="/signup">Sign up</Link>
      </div>
    </footer>
  </div>
);

function AppContent() {
  const { user, isLoggedIn, logout, loading, setIsLoggedIn, setUser } = useAuth();
  const billingAvailable = Boolean(proUiAvailable && user?.billing_enabled);
  const [isValidating, setIsValidating] = useState(true);
  const [theme, setTheme] = useState(() => {
    if (typeof window === "undefined") return "dark";
    return localStorage.getItem("theme") || (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  });
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [pendingSession, setPendingSession] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }, []);

  useEffect(() => {
    const validateSession = async () => {
      try {
        const isValid = await authAPI.validateAuth();
        if (isValid) {
          const currentUser = await authAPI.getCurrentUser();
          if (currentUser?.data) {
            setUser(currentUser.data);
            setIsLoggedIn(true);
          }
        } else {
          logout();
        }
      } catch (error) {
        console.error("Session validation failed:", error);
        logout();
      }
      setIsValidating(false);
    };

    validateSession();
  }, []);

  const handleNewChat = useCallback(() => {
    setCurrentSessionId(null);
    setPendingSession(false);
  }, []);

  const handleSessionPending = useCallback((pending = true) => {
    setPendingSession(Boolean(pending));
  }, []);

  const handleSessionCreated = useCallback((sessionId) => {
    setPendingSession(false);
    if (!sessionId) return;
    setCurrentSessionId(sessionId);
  }, []);

  // Opening a chat from the sidebar must update App too, otherwise the
  // `externalSessionId` prop and the chat currently on screen disagree.
  const handleSessionSelected = useCallback((sessionId) => {
    setPendingSession(false);
    if (!sessionId) return;
    setCurrentSessionId((current) => (current === sessionId ? current : sessionId));
  }, []);

  if (isValidating || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <img src={noyaLogo} alt="" className="h-12 w-12 animate-[spin_1.5s_linear_infinite]" />
      </div>
    );
  }

  return (
    <Router>
      <div data-theme={theme} className={`${isLoggedIn ? "h-screen" : "min-h-screen"} bg-[var(--bg)] text-[var(--ink)] antialiased transition-colors duration-300 overflow-x-hidden`}>
        <Routes>
          <Route
            path="/"
            element={
              isLoggedIn ? (
                <Navigate to="/subjects" replace />
              ) : (
                <PublicShell theme={theme} onToggleTheme={toggleTheme} />
              )
            }
          />
          <Route path="/login" element={!isLoggedIn ? <Login /> : <Navigate to="/subjects" replace />} />
          <Route path="/signup" element={!isLoggedIn ? <Signup /> : <Navigate to="/subjects" replace />} />
          <Route
            path="/subjects"
            element={
              <ProtectedRoute>
                <SubjectSelection />
              </ProtectedRoute>
            }
          />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatView
                  sessionId={currentSessionId}
                  onNewChat={handleNewChat}
                  onSessionPending={handleSessionPending}
                  onSessionCreated={handleSessionCreated}
                  onSessionSelected={handleSessionSelected}
                  theme={theme}
                  onToggleTheme={toggleTheme}
                  billingAvailable={billingAvailable}
                />
              </ProtectedRoute>
            }
          />
          <Route path="/pricing" element={<Navigate to="/" replace />} />
          {billingAvailable && (
            <Route
              path="/billing"
              element={
                <ProtectedRoute>
                  <BillingPage theme={theme} onToggleTheme={toggleTheme} />
                </ProtectedRoute>
              }
            />
          )}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
