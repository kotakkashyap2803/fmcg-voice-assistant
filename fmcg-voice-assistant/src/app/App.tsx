import { useEffect, useState, type FormEvent } from "react";
import {
  login,
  logout,
  getCurrentUser,
  getStoredUser,
  type AuthUser,
} from "../services/authService";
import { clearTokens } from "../services/api";
import {
  getDashboardAnalytics,
  type DashboardAnalytics,
} from "../services/analyticsService";
import "./App.css";

import { getRetailers, type Retailer } from "../services/retailerService";

import { useVoiceAgent } from "../hooks/useVoiceAgent";

import PastInteractions from "../features/conversations/PastInteractions";

function formatCurrency(value: string | number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function formatLabel(value: string): string {
  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function App() {
  const [user, setUser] = useState<AuthUser | null>(getStoredUser());
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [error, setError] = useState("");

  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");

  const [startDate, setStartDate] = useState("2026-11-01");
  const [endDate, setEndDate] = useState("2026-11-11");

  const [retailers, setRetailers] = useState<Retailer[]>([]);
  const [retailersLoading, setRetailersLoading] = useState(false);
  const [retailersError, setRetailersError] = useState("");

  const [selectedRetailerId, setSelectedRetailerId] = useState("");
  const [language, setLanguage] = useState("en");
  const [messageInput, setMessageInput] = useState("");

  const voiceAgent = useVoiceAgent(Number(selectedRetailerId) || 0, language);

  const [activePage, setActivePage] = useState<"dashboard" | "past-interactions">("dashboard");

  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      const accessToken = localStorage.getItem("access_token");

      if (!accessToken) {
        setCheckingSession(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();

        if (!cancelled) {
          setUser(currentUser);
        }
      } catch {
        clearTokens();
        localStorage.removeItem("fmcg_user");

        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setCheckingSession(false);
        }
      }
    };

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!user) return;

    let cancelled = false;

    const loadAnalytics = async () => {
      setAnalyticsLoading(true);
      setAnalyticsError("");

      try {
        const result = await getDashboardAnalytics(startDate, endDate);

        if (!cancelled) {
          setAnalytics(result);
        }
      } catch (err: any) {
        if (!cancelled) {
          setAnalyticsError(
            err.response?.data?.message ||
              err.response?.data?.detail ||
              err.message ||
              "Unable to load dashboard analytics.",
          );
        }
      } finally {
        if (!cancelled) {
          setAnalyticsLoading(false);
        }
      }
    };

    loadAnalytics();

    return () => {
      cancelled = true;
    };
  }, [user, startDate, endDate]);

  useEffect(() => {
    if (!user) return;

    let cancelled = false;

    const loadRetailers = async () => {
      setRetailersLoading(true);
      setRetailersError("");

      try {
        const result = await getRetailers();

        if (!cancelled) {
          setRetailers(result);

          if (result.length > 0) {
            setSelectedRetailerId(String(result[0].id));
          }
        }
      } catch (err: any) {
        if (!cancelled) {
          setRetailersError(
            err.response?.data?.message ||
              err.response?.data?.detail ||
              err.message ||
              "Unable to load retailers.",
          );
        }
      } finally {
        if (!cancelled) {
          setRetailersLoading(false);
        }
      }
    };

    loadRetailers();

    return () => {
      cancelled = true;
    };
  }, [user]);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const identifier = username.trim();

      const credentials = {
        ...(identifier.includes("@")
          ? { email: identifier }
          : { username: identifier }),
        password,
      };

      const loggedInUser = await login(credentials);
      setUser(loggedInUser);
      setPassword("");
    } catch (err: any) {
      setError(
        err.response?.data?.message ||
          err.response?.data?.detail ||
          err.message ||
          "Unable to login. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // Local credentials are cleared by logout.
    }

    setUser(null);
    setAnalytics(null);
    setUsername("");
    setPassword("");
    setError("");
  };

  const handleDateFilter = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (startDate > endDate) {
      setAnalyticsError("Start date cannot be after end date.");
    }
  };

  if (checkingSession) {
    return (
      <main className="loading-screen">
        <div className="loader" />
        <p>Checking your session...</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="login-page">
        <section className="login-brand">
          <div className="brand-mark">M</div>
          <p className="brand-label">MARICO</p>
          <h1>
            Smarter conversations.
            <br />
            Better business.
          </h1>
          <p className="brand-description">
            Your intelligent FMCG sales assistant for retailer engagement, order
            management and business insights.
          </p>
          <div className="brand-footer">FMCG VOICE ASSISTANT</div>
        </section>

        <section className="login-panel">
          <div className="login-card">
            <div className="mobile-brand">MARICO</div>
            <p className="eyebrow">WELCOME BACK</p>
            <h2>Sign in to your account</h2>
            <p className="login-subtitle">
              Enter your credentials to continue.
            </p>

            <form onSubmit={handleLogin}>
              <label htmlFor="username">Username or email</label>
              <input
                id="username"
                type="text"
                placeholder="Enter username or email"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                required
              />

              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />

              {error && (
                <div className="error-message" role="alert">
                  {error}
                </div>
              )}

              <button className="login-button" type="submit" disabled={loading}>
                {loading ? "Signing in..." : "Sign in"}
              </button>
            </form>

            <p className="login-note">Authorized personnel only.</p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="dashboard-shell">
      <header className="app-header">
        <div className="app-brand">
          <div className="app-brand-mark">M</div>
          <div>
            <strong>MARICO</strong>
            <span>FMCG VOICE ASSISTANT</span>
          </div>
        </div>

        <div className="user-section">
            <div className="user-avatar">
                {(user.first_name || user.username).charAt(0).toUpperCase()}
            </div>
            <div className="user-details">
                <strong>{user.full_name || user.username}</strong>
                <span>{user.email}</span>
            </div>
            <button
                className="history-nav-button"
                onClick={() =>
                    setActivePage(
                        activePage === "dashboard"
                            ? "past-interactions"
                            : "dashboard"
                    )
                }
            >
                {activePage === "dashboard" ? "Past Interactions" : "Dashboard"}
            </button>
            <button className="logout-button" onClick={handleLogout}>
                Sign out
            </button>
        </div>
      </header>
        {activePage === "past-interactions" ? (
            <PastInteractions
                onBack={() => setActivePage("dashboard")}
            />
        ) : (
            <>
                <section className="dashboard-content">
                    <section className="panel voice-assistant-panel">
                    <div className="panel-heading">
                        <div>
                            <p className="eyebrow">RETAILER ENGAGEMENT</p>
                            <h2>AI Voice Assistant</h2>
                            <p>Start an intelligent sales conversation with a retailer.</p>
                        </div>
                        <span className="panel-tag">VOICE AI</span>
                    </div>

                    <div className="voice-setup">
                        <div className="voice-field">
                            <label htmlFor="retailer">Select Retailer</label>

                            <select
                                id="retailer"
                                value={selectedRetailerId}
                                onChange={(event) => setSelectedRetailerId(event.target.value)}
                                disabled={retailersLoading || retailers.length === 0}
                            >
                                {retailers.length === 0 && (
                                <option value="">
                                    {retailersLoading
                                    ? "Loading retailers..."
                                    : "No retailers available"}
                                </option>
                                )}

                                {retailers.map((retailer) => (
                                <option key={retailer.id} value={retailer.id}>
                                    {retailer.shop_name} â€” {retailer.name}
                                </option>
                                ))}
                            </select>
                        </div>

                        <div className="voice-field">
                            <label htmlFor="language">Conversation Language</label>

                            <select
                                id="language"
                                value={language}
                                onChange={(event) => setLanguage(event.target.value)}
                            >
                                <option value="en">English</option>
                                <option value="hi">Hindi</option>
                                <option value="mr">Marathi</option>
                            </select>
                        </div>

                        <button
                            className="login-button voice-start-button"
                            type="button"
                            disabled={
                                !selectedRetailerId ||
                                retailersLoading ||
                                voiceAgent.isLoading ||
                                voiceAgent.conversationId !== null
                            }
                            onClick={() => voiceAgent.startSession()}
                        >
                            {voiceAgent.isLoading ? "Starting..." : "Start Conversation"}
                        </button>
                    </div>

                    {retailersError && (
                        <div className="analytics-error" role="alert">
                            {retailersError}
                        </div>
                    )}

                    {voiceAgent.error && (
                        <div className="analytics-error" role="alert">
                            {voiceAgent.error}
                        </div>
                    )}

                    {voiceAgent.conversationId !== null && (
                        <div className="voice-conversation">
                        <div className="conversation-status">
                            <span className="status-dot" />
                            Conversation #{voiceAgent.conversationId}
                        </div>

                        <div className="conversation-messages">
                            {voiceAgent.messages.map((message, index) => (
                            <div key={index} className={`chat-message ${message.role}`}>
                                <strong>
                                {message.role === "assistant"
                                    ? "AI Assistant"
                                    : "Retailer"}
                                </strong>
                                <p>{message.text}</p>
                            </div>
                            ))}
                        </div>

                        <div className="voice-controls">
                            <button
                            type="button"
                            onClick={
                                voiceAgent.isListening
                                ? voiceAgent.stopListening
                                : voiceAgent.startListening
                            }
                            disabled={voiceAgent.isLoading}
                            >
                            {voiceAgent.isListening
                                ? "Stop Listening"
                                : "Start Microphone"}
                            </button>

                            <button
                            type="button"
                            onClick={voiceAgent.sendTranscript}
                            disabled={
                                !voiceAgent.transcript.trim() || voiceAgent.isLoading
                            }
                            >
                            Send Voice Message
                            </button>

                            <button type="button" onClick={voiceAgent.stopSpeaking}>
                            Stop Audio
                            </button>
                        </div>

                        {voiceAgent.transcript && (
                            <div className="voice-transcript">
                            <strong>Recognized speech:</strong>
                            <p>{voiceAgent.transcript}</p>
                            </div>
                        )}

                        <form
                            className="voice-text-form"
                            onSubmit={async (event) => {
                            event.preventDefault();

                            if (!messageInput.trim()) return;

                            const message = messageInput.trim();
                            setMessageInput("");

                            await voiceAgent.sendUserMessage(message);
                            }}
                        >
                            <input
                            type="text"
                            placeholder="Or type a message..."
                            value={messageInput}
                            onChange={(event) => setMessageInput(event.target.value)}
                            />

                            <button
                            type="submit"
                            disabled={!messageInput.trim() || voiceAgent.isLoading}
                            >
                            Send
                            </button>
                        </form>

                        <button
                            type="button"
                            className="logout-button"
                            onClick={voiceAgent.finishSession}
                            disabled={voiceAgent.isLoading}
                        >
                            End Conversation
                        </button>
                        </div>
                    )}


                    {voiceAgent.completion && (
                        <div className="voice-conversation">
                            <div className="panel-heading">
                                <div>
                                    <p className="eyebrow">CONVERSATION COMPLETED</p>
                                    <h2>Conversation Summary</h2>
                                </div>
                                <span className="panel-tag">
                                    {formatLabel(voiceAgent.completion.outcome)}
                                </span>
                            </div>

                            <div className="voice-transcript">
                                <strong>Outcome</strong>
                                <p>{formatLabel(voiceAgent.completion.outcome)}</p>
                            </div>

                            <div className="voice-transcript">
                                <strong>Summary</strong>
                                <p>{voiceAgent.completion.summary}</p>
                            </div>
                        </div>
                    )}

                </section>
                <div className="dashboard-heading">
                    <div>
                        <p className="eyebrow">BUSINESS OVERVIEW</p>
                        <h1>Sales Dashboard</h1>
                        <p>
                        Monitor sales, retailer engagement and voice assistant
                        performance.
                        </p>
                    </div>

                    <form className="date-filter" onSubmit={handleDateFilter}>
                        <div>
                            <label htmlFor="startDate">From</label>
                            <input
                                id="startDate"
                                type="date"
                                value={startDate}
                                max={endDate}
                                onChange={(event) => setStartDate(event.target.value)}
                            />
                        </div>
                        <div>
                            <label htmlFor="endDate">To</label>
                            <input
                                id="endDate"
                                type="date"
                                value={endDate}
                                min={startDate}
                                onChange={(event) => setEndDate(event.target.value)}
                            />
                        </div>
                        <button type="submit">Apply</button>
                    </form>
                </div>

                {analyticsLoading && (
                    <div className="analytics-loading">
                        <div className="loader" />
                        Loading business analytics...
                    </div>
                )}

                {analyticsError && (
                    <div className="analytics-error" role="alert">
                        {analyticsError}
                    </div>
                )}

                {analytics && (
                    <>
                        <div className="dashboard-meta">
                        Reporting period: {analytics.period.start_date} to{" "}
                        {analytics.period.end_date}
                        <span>Live API data</span>
                        </div>

                        <section className="kpi-grid">
                            <article className="kpi-card">
                                <div className="kpi-top">
                                <span>Total Revenue</span>
                                <span className="kpi-icon green">â‚¹</span>
                                </div>
                                <h2>{formatCurrency(analytics.orders.revenue)}</h2>
                                <p>Confirmed order revenue</p>
                            </article>

                            <article className="kpi-card">
                                <div className="kpi-top">
                                <span>Total Orders</span>
                                <span className="kpi-icon blue">â–¤</span>
                                </div>
                                <h2>{analytics.orders.total}</h2>
                                <p>
                                {analytics.orders.confirmed} confirmed Â·{" "}
                                {analytics.orders.draft} draft
                                </p>
                            </article>

                            <article className="kpi-card">
                                <div className="kpi-top">
                                <span>Active Retailers</span>
                                <span className="kpi-icon purple">â™™</span>
                                </div>
                                <h2>{analytics.retailers.active}</h2>
                                <p>{analytics.retailers.total} total retailers</p>
                            </article>

                            <article className="kpi-card">
                                <div className="kpi-top">
                                <span>Conversations</span>
                                <span className="kpi-icon orange">â—‰</span>
                                </div>
                                <h2>{analytics.conversations.total}</h2>
                                <p>
                                {analytics.conversations.completed} completed Â·{" "}
                                {analytics.conversations.active} active
                                </p>
                            </article>

                            <article className="kpi-card">
                                <div className="kpi-top">
                                <span>Average Order Value</span>
                                <span className="kpi-icon green">â†—</span>
                                </div>
                                <h2>{formatCurrency(analytics.orders.average_order_value)}</h2>
                                <p>Per confirmed order</p>
                            </article>

                            <article className="kpi-card">
                                <div className="kpi-top">
                                <span>Pending Follow-ups</span>
                                <span className="kpi-icon orange">â—·</span>
                                </div>
                                <h2>{analytics.followups.pending}</h2>
                                <p>{analytics.followups.overdue} overdue</p>
                            </article>
                        </section>

                        <section className="dashboard-grid">
                            <article className="panel sales-panel">
                                <div className="panel-heading">
                                <div>
                                    <h2>Daily Sales Performance</h2>
                                    <p>Confirmed revenue by date</p>
                                </div>
                                <span className="panel-tag">Revenue</span>
                                </div>

                                {analytics.daily_sales.length === 0 ? (
                                <p className="empty-state">
                                    No confirmed sales in this period.
                                </p>
                                ) : (
                                <div className="sales-chart">
                                    {analytics.daily_sales.map((sale) => {
                                    const maxRevenue = Math.max(
                                        ...analytics.daily_sales.map((item) =>
                                        Number(item.revenue),
                                        ),
                                        1,
                                    );
                                    const percentage = Math.max(
                                        (Number(sale.revenue) / maxRevenue) * 100,
                                        4,
                                    );

                                    return (
                                        <div className="sales-bar-row" key={sale.sales_date}>
                                        <span>{sale.sales_date}</span>
                                        <div className="sales-bar-track">
                                            <div
                                            className="sales-bar"
                                            style={{ width: `${percentage}%` }}
                                            />
                                        </div>
                                        <strong>{formatCurrency(sale.revenue)}</strong>
                                        </div>
                                    );
                                    })}
                                </div>
                                )}
                            </article>

                            <article className="panel">
                                <div className="panel-heading">
                                <div>
                                    <h2>Order Summary</h2>
                                    <p>Order status breakdown</p>
                                </div>
                                </div>

                                <div className="order-summary">
                                <div>
                                    <span>Confirmed</span>
                                    <strong>{analytics.orders.confirmed}</strong>
                                </div>
                                <div>
                                    <span>Draft</span>
                                    <strong>{analytics.orders.draft}</strong>
                                </div>
                                <div>
                                    <span>Cancelled</span>
                                    <strong>{analytics.orders.cancelled}</strong>
                                </div>
                                <div>
                                    <span>Subtotal</span>
                                    <strong>{formatCurrency(analytics.orders.subtotal)}</strong>
                                </div>
                                <div>
                                    <span>Discounts</span>
                                    <strong>{formatCurrency(analytics.orders.discount)}</strong>
                                </div>
                                </div>
                            </article>

                            <article className="panel">
                                <div className="panel-heading">
                                <div>
                                    <h2>Top Products</h2>
                                    <p>Best performing products by revenue</p>
                                </div>
                                </div>

                                {analytics.top_products.length === 0 ? (
                                <p className="empty-state">No product sales available.</p>
                                ) : (
                                <div className="data-list">
                                    {analytics.top_products.map((product, index) => (
                                    <div
                                        className="data-row"
                                        key={`${product.product_name}-${product.variant_name}`}
                                    >
                                        <div className="rank">{index + 1}</div>
                                        <div className="data-main">
                                        <strong>{product.product_name}</strong>
                                        <span>
                                            {product.variant_name} Â·{" "}
                                            {Number(product.units_sold)} units
                                        </span>
                                        </div>
                                        <strong>{formatCurrency(product.revenue)}</strong>
                                    </div>
                                    ))}
                                </div>
                                )}
                            </article>

                            <article className="panel">
                                <div className="panel-heading">
                                <div>
                                    <h2>Top Retailers</h2>
                                    <p>Retailers ranked by revenue</p>
                                </div>
                                </div>

                                {analytics.top_retailers.length === 0 ? (
                                <p className="empty-state">No retailer sales available.</p>
                                ) : (
                                <div className="data-list">
                                    {analytics.top_retailers.map((retailer, index) => (
                                    <div className="data-row" key={retailer.retailer_id}>
                                        <div className="rank">{index + 1}</div>
                                        <div className="data-main">
                                        <strong>{retailer.retailer__name}</strong>
                                        <span>
                                            {retailer.retailer__shop_name} Â·{" "}
                                            {retailer.order_count} orders
                                        </span>
                                        </div>
                                        <strong>{formatCurrency(retailer.revenue)}</strong>
                                    </div>
                                    ))}
                                </div>
                                )}
                            </article>

                            <article className="panel">
                                <div className="panel-heading">
                                <div>
                                    <h2>Conversation Insights</h2>
                                    <p>Retailer engagement outcomes</p>
                                </div>
                                </div>

                                <div className="order-summary">
                                <div>
                                    <span>Completed</span>
                                    <strong>{analytics.conversations.completed}</strong>
                                </div>
                                <div>
                                    <span>Active</span>
                                    <strong>{analytics.conversations.active}</strong>
                                </div>
                                <div>
                                    <span>Failed</span>
                                    <strong>{analytics.conversations.failed}</strong>
                                </div>
                                </div>

                                <div className="distribution-list">
                                {analytics.conversation_outcomes.map((item) => (
                                    <div className="distribution-row" key={item.outcome}>
                                    <span>{formatLabel(item.outcome)}</span>
                                    <strong>{item.count}</strong>
                                    </div>
                                ))}
                                </div>
                            </article>

                            <article className="panel">
                                <div className="panel-heading">
                                <div>
                                    <h2>Channel & Language</h2>
                                    <p>How retailers interact with the assistant</p>
                                </div>
                                </div>

                                <div className="distribution-list">
                                {analytics.channel_distribution.map((item) => (
                                    <div className="distribution-row" key={item.channel}>
                                    <span>{formatLabel(item.channel)}</span>
                                    <strong>{item.count}</strong>
                                    </div>
                                ))}
                                {analytics.language_distribution.map((item) => (
                                    <div className="distribution-row" key={item.language}>
                                    <span>Language: {item.language.toUpperCase()}</span>
                                    <strong>{item.count}</strong>
                                    </div>
                                ))}
                                </div>
                            </article>

                            <article className="panel">
                                <div className="panel-heading">
                                <div>
                                    <h2>Top Conversation Intents</h2>
                                    <p>Most frequently detected intents</p>
                                </div>
                                </div>

                                <div className="distribution-list">
                                {analytics.intent_distribution.slice(0, 6).map((item) => (
                                    <div className="distribution-row" key={item.intent}>
                                    <span>{formatLabel(item.intent)}</span>
                                    <strong>{item.count}</strong>
                                    </div>
                                ))}
                                </div>
                            </article>
                        </section>
                    </>
                )}
                </section>
            </>
        )}
    </main>
  );
}

export default App;
