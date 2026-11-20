import { useCallback, useEffect, useState } from "react";
import {
  ArrowUp,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  Eye,
  EyeOff,
  FileText,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquareText,
  Plus,
  SlidersHorizontal,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload,
  UserRound,
  X,
} from "lucide-react";
import { useRef } from "react";
import { API_BASE_URL, authApi, workspaceApi } from "./services/api.js";
import DatabaseDashboard from "./components/DatabaseDashboard.jsx";

const prompts = [
  "Help me organize my week",
  "Summarize a complex idea",
  "Draft a thoughtful email",
];

function getErrorMessage(error) {
  const data = error?.response?.data;
  if (data?.database === "unavailable" || data?.database?.status === "unavailable") {
    return "Django is running but cannot connect to the configured database. Check backend/.env and run migrations.";
  }
  if (typeof data?.detail === "string") return data.detail;
  if (data && typeof data === "object") {
    const first = Object.values(data).flat().find((value) => typeof value === "string");
    if (first) return first;
  }
  if (!error?.response && (error?.code === "ERR_NETWORK" || error?.request)) {
    return `Cannot reach the Django API at ${API_BASE_URL}. Start the backend with "python manage.py runserver" from the backend folder.`;
  }
  return error?.message || "Something went wrong. Please try again.";
}

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("syntrix-token"));
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [health, setHealth] = useState({ status: "checking", ai_mode: null });
  const [conversations, setConversations] = useState([]);
  const [dashboardProfile, setDashboardProfile] = useState(null);
  const [dashboardSettings, setDashboardSettings] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [usageSummary, setUsageSummary] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState("");
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [activePage, setActivePage] = useState("dashboard");
  const [activeConversation, setActiveConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [notice, setNotice] = useState("");

  const loadConversations = useCallback(async () => {
    const response = await workspaceApi.conversations();
    setConversations(response.data);
  }, []);

  const loadUsageSummary = useCallback(async () => {
    const response = await workspaceApi.usageSummary();
    setUsageSummary(response.data);
  }, []);

  useEffect(() => {
    workspaceApi
      .health()
      .then(({ data }) => setHealth(data))
      .catch((error) =>
        setHealth({
          status: "offline",
          ai_mode: null,
          detail: getErrorMessage(error),
        }),
      );
  }, []);

  useEffect(() => {
    let active = true;
    if (!token) {
      setReady(true);
      setUser(null);
      return () => {
        active = false;
      };
    }

    setReady(false);
    Promise.all([authApi.me(), workspaceApi.conversations()])
      .then(([profile, list]) => {
        if (!active) return;
        setUser(profile.data);
        setConversations(list.data);
      })
      .catch(() => {
        if (!active) return;
        sessionStorage.removeItem("syntrix-token");
        setToken(null);
        setUser(null);
      })
      .finally(() => {
        if (active) setReady(true);
      });

    return () => {
      active = false;
    };
  }, [token]);

  useEffect(() => {
    if (!token || !user) return undefined;
    let active = true;
    setDashboardLoading(true);
    setDashboardError("");

    Promise.allSettled([
      authApi.profile(),
      workspaceApi.settings(),
      workspaceApi.documents(),
      workspaceApi.usageSummary(),
    ])
      .then(([profile, settings, docs, usage]) => {
        if (!active) return;
        if (profile.status === "fulfilled") setDashboardProfile(profile.value.data);
        if (settings.status === "fulfilled") setDashboardSettings(settings.value.data);
        if (docs.status === "fulfilled") setDocuments(docs.value.data);
        if (usage.status === "fulfilled") setUsageSummary(usage.value.data);
        const failed = [profile, settings, docs, usage].find(
          (result) => result.status === "rejected",
        );
        if (failed) setDashboardError(getErrorMessage(failed.reason));
      })
      .finally(() => {
        if (active) setDashboardLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token, user?.id]);

  const startNewChat = useCallback(() => {
    setActiveConversation(null);
    setMessages([]);
    setActivePage("chat");
    setMobileNavOpen(false);
    setNotice("");
  }, []);

  const openConversation = useCallback(async (conversation) => {
    setActivePage("chat");
    setActiveConversation(conversation);
    setMessages([]);
    setConversationLoading(true);
    setMobileNavOpen(false);
    setNotice("");
    try {
      const { data } = await workspaceApi.conversation(conversation.id);
      setActiveConversation(data.conversation);
      setMessages(data.messages);
    } catch (error) {
      setNotice(getErrorMessage(error));
    } finally {
      setConversationLoading(false);
    }
  }, []);

  const handleAuth = async (mode, values) => {
    setAuthLoading(true);
    setNotice("");
    try {
      const action = mode === "register" ? authApi.register : authApi.login;
      const { data } = await action(values);
      sessionStorage.setItem("syntrix-token", data.token);
      setUser(data.user);
      setToken(data.token);
      setActivePage("dashboard");
    } catch (error) {
      setNotice(getErrorMessage(error));
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    setNotice("");
    try {
      await authApi.logout();
    } catch (error) {
      setNotice(getErrorMessage(error));
    } finally {
      sessionStorage.removeItem("syntrix-token");
      setToken(null);
      setUser(null);
      setConversations([]);
      setMessages([]);
      setActiveConversation(null);
      setDashboardProfile(null);
      setDashboardSettings(null);
      setDocuments([]);
      setUsageSummary(null);
    }
  };

  const handleSend = async (text) => {
    const content = text.trim();
    if (!content || sending) return;
    setSending(true);
    setNotice("");
    try {
      const { data } = await workspaceApi.sendMessage(
        content,
        activeConversation?.id,
      );
      setActiveConversation(data.conversation);
      setMessages((current) => [
        ...current,
        data.user_message,
        data.assistant_message,
      ]);
      setHealth((current) => ({ ...current, ai_mode: data.mode }));
      await loadConversations();
      await loadUsageSummary();
    } catch (error) {
      setNotice(getErrorMessage(error));
      return false;
    } finally {
      setSending(false);
    }
    return true;
  };

  const handleUploadDocument = async (file) => {
    if (!file || uploadingDocument) return;
    setUploadingDocument(true);
    setNotice("");
    try {
      const { data } = await workspaceApi.uploadDocument(file);
      setDocuments((current) => [data, ...current]);
    } catch (error) {
      setNotice(getErrorMessage(error));
    } finally {
      setUploadingDocument(false);
    }
  };

  const handleDeleteDocument = async (document) => {
    if (!window.confirm(`Delete "${document.original_name}"? This cannot be undone.`)) return;
    try {
      await workspaceApi.deleteDocument(document.id);
      setDocuments((current) => current.filter((item) => item.id !== document.id));
    } catch (error) {
      setNotice(getErrorMessage(error));
    }
  };

  const handleUpdateProfile = async (values) => {
    try {
      const { data } = await authApi.updateProfile(values);
      setDashboardProfile(data);
      setNotice("Profile saved.");
      return true;
    } catch (error) {
      setNotice(getErrorMessage(error));
      return false;
    }
  };

  const handleUpdateSettings = async (values) => {
    try {
      const { data } = await workspaceApi.updateSettings(values);
      setDashboardSettings(data);
      setNotice("Settings saved.");
      return true;
    } catch (error) {
      setNotice(getErrorMessage(error));
      return false;
    }
  };

  const handleDeleteConversation = async (conversation) => {
    if (!window.confirm(`Delete "${conversation.title}"? This cannot be undone.`)) return;
    try {
      await workspaceApi.deleteConversation(conversation.id);
      setConversations((current) =>
        current.filter((item) => item.id !== conversation.id),
      );
      if (activeConversation?.id === conversation.id) startNewChat();
    } catch (error) {
      setNotice(getErrorMessage(error));
    }
  };

  if (!ready) return <LoadingScreen />;
  if (!user) {
    return (
      <AuthScreen
        onSubmit={handleAuth}
        loading={authLoading}
        notice={notice}
        aiMode={health.ai_mode}
        apiOnline={health.status === "ok"}
        apiMessage={health.detail}
      />
    );
  }

  return (
    <div className="app-shell">
      {mobileNavOpen && (
        <button
          className="mobile-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileNavOpen(false)}
        />
      )}
      <Sidebar
        activePage={activePage}
        conversations={conversations}
        activeConversation={activeConversation}
        user={user}
        isOpen={mobileNavOpen}
        onNavigate={(page) => {
          setActivePage(page);
          setMobileNavOpen(false);
        }}
        onNewChat={startNewChat}
        onOpenConversation={openConversation}
        onDeleteConversation={handleDeleteConversation}
        onLogout={handleLogout}
      />
      <main className="workspace-main">
        <header className="mobile-header">
          <button
            className="icon-button mobile-menu-button"
            aria-label="Open navigation"
            onClick={() => setMobileNavOpen(true)}
          >
            <Menu size={20} />
          </button>
          <BrandMark compact />
          <button
            className="icon-button"
            aria-label="Start a new chat"
            onClick={startNewChat}
          >
            <Plus size={20} />
          </button>
        </header>
        {notice && (
          <div className="notice-banner" role="alert">
            <span>{notice}</span>
            <button
              className="icon-button notice-dismiss"
              onClick={() => setNotice("")}
              aria-label="Dismiss message"
            >
              <X size={17} />
            </button>
          </div>
        )}
        {activePage === "database" && user.is_staff ? (
          <DatabaseDashboard />
        ) : activePage === "chat" ? (
          <ChatPage
            user={user}
            conversation={activeConversation}
            messages={messages}
            loading={conversationLoading}
            sending={sending}
            aiMode={health.ai_mode}
            onSend={handleSend}
            onNewChat={startNewChat}
          />
        ) : (
          <Dashboard
            user={user}
            conversations={conversations}
            profile={dashboardProfile}
            settings={dashboardSettings}
            documents={documents}
            usage={usageSummary}
            dataLoading={dashboardLoading}
            dataError={dashboardError}
            uploadingDocument={uploadingDocument}
            aiMode={health.ai_mode}
            onNewChat={startNewChat}
            onOpenConversation={openConversation}
            onUploadDocument={handleUploadDocument}
            onDeleteDocument={handleDeleteDocument}
            onUpdateProfile={handleUpdateProfile}
            onUpdateSettings={handleUpdateSettings}
          />
        )}
      </main>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div className="loading-screen">
      <div className="loading-mark">
        <Sparkles size={23} />
      </div>
      <LoaderCircle className="spin" size={18} />
      <span>Preparing your workspace</span>
    </div>
  );
}

function BrandMark({ compact = false }) {
  return (
    <div className={`brand-lockup ${compact ? "brand-compact" : ""}`}>
      <div className="brand-icon">
        <Sparkles size={19} strokeWidth={2.2} />
      </div>
      {!compact && (
        <div className="brand-wordmark">
          <span>syntrix</span>
          <span className="brand-ai">AI</span>
        </div>
      )}
    </div>
  );
}

function Sidebar({
  activePage,
  conversations,
  activeConversation,
  user,
  isOpen,
  onNavigate,
  onNewChat,
  onOpenConversation,
  onDeleteConversation,
  onLogout,
}) {
  return (
    <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`}>
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <BrandMark />
          <span className="workspace-label">WORKSPACE</span>
        </div>
        <button
          className="icon-button sidebar-close"
          aria-label="Close navigation"
          onClick={() => onNavigate(activePage)}
        >
          <X size={18} />
        </button>
        <div className="workspace-switcher">
          <span className="workspace-avatar">S</span>
          <span className="workspace-switcher-copy">
            <strong>Personal space</strong>
            <small>Free workspace</small>
          </span>
          <ChevronDown size={15} />
        </div>
        <nav className="primary-nav" aria-label="Main navigation">
          <button
            className={`nav-item ${activePage === "dashboard" ? "nav-item-active" : ""}`}
            onClick={() => onNavigate("dashboard")}
          >
            <LayoutDashboard size={18} />
            <span>Overview</span>
          </button>
          <button
            className={`nav-item ${activePage === "chat" ? "nav-item-active" : ""}`}
            onClick={onNewChat}
          >
            <MessageSquareText size={18} />
            <span>AI chat</span>
            <span className="nav-shortcut">⌘ K</span>
          </button>
          {user.is_staff && (
            <button
              className={`nav-item ${activePage === "database" ? "nav-item-active" : ""}`}
              onClick={() => onNavigate("database")}
            >
              <Database size={18} />
              <span>Database</span>
            </button>
          )}
        </nav>
        <div className="sidebar-section-heading">
          <span>RECENT</span>
          <button
            className="icon-button sidebar-add"
            aria-label="New conversation"
            onClick={onNewChat}
          >
            <Plus size={17} />
          </button>
        </div>
        <div className="conversation-list">
          {conversations.length ? (
            conversations.slice(0, 12).map((conversation) => (
              <div
                className={`conversation-row ${activeConversation?.id === conversation.id ? "conversation-row-active" : ""}`}
                key={conversation.id}
              >
                <button
                  className="conversation-link"
                  title={conversation.title}
                  onClick={() => onOpenConversation(conversation)}
                >
                  <MessageSquareText size={16} />
                  <span>{conversation.title}</span>
                </button>
                <button
                  className="conversation-delete"
                  aria-label={`Delete ${conversation.title}`}
                  onClick={() => onDeleteConversation(conversation)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          ) : (
            <p className="empty-history">Your conversations will appear here.</p>
          )}
        </div>
      </div>
      <div className="sidebar-bottom">
        <div className="sidebar-help">
          <div className="help-icon">
            <CircleHelp size={17} />
          </div>
          <div>
            <strong>Need a hand?</strong>
            <span>Your AI workspace is ready.</span>
          </div>
        </div>
        <div className="user-menu">
          <div className="user-avatar">
            {(user.username || "U").slice(0, 1).toUpperCase()}
          </div>
          <div className="user-details">
            <strong>{user.username}</strong>
            <span>{user.email || "Syntrix member"}</span>
          </div>
          <button className="icon-button logout-button" onClick={onLogout} aria-label="Sign out">
            <LogOut size={17} />
          </button>
        </div>
      </div>
    </aside>
  );
}

function Dashboard({
  user,
  conversations,
  profile,
  settings,
  documents,
  usage,
  dataLoading,
  dataError,
  uploadingDocument,
  aiMode,
  onNewChat,
  onOpenConversation,
  onUploadDocument,
  onDeleteDocument,
  onUpdateProfile,
  onUpdateSettings,
}) {
  const firstName =
    profile?.display_name || user.username?.split(/[._-]/)[0] || user.username;
  const recent = conversations.slice(0, 4);

  return (
    <div className="dashboard-page page-enter">
      <div className="topline">
        <div className="breadcrumb">Workspace <span>/</span> Overview</div>
        <ModeBadge mode={aiMode} />
      </div>
      <section className="welcome-section">
        <div className="welcome-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> YOUR THINKING SPACE</div>
          <h1>Good to see you, {firstName}.</h1>
          <p>Bring your ideas, questions, and work. Let’s make something of them.</p>
        </div>
        <button className="button-primary hero-action" onClick={onNewChat}>
          <Sparkles size={17} />
          Start a conversation
        </button>
      </section>
      <section className="dashboard-grid">
        <article className="workspace-card chat-launch-card">
          <div className="card-icon card-icon-teal"><MessageSquareText size={20} /></div>
          <div className="card-kicker">AI ASSISTANT</div>
          <h2>A little help goes a long way.</h2>
          <p>Think through a problem, shape an idea, or get a first draft on the page.</p>
          <button className="text-action" onClick={onNewChat}>
            Open AI chat <span aria-hidden="true">→</span>
          </button>
          <div className="launch-decoration" aria-hidden="true"><Sparkles size={120} /></div>
        </article>
        <article className="workspace-card recent-card">
          <div className="section-title-row">
            <div>
              <div className="card-kicker">PICK UP WHERE YOU LEFT OFF</div>
              <h2>Recent conversations</h2>
            </div>
            <div className="recent-count">{conversations.length}</div>
          </div>
          {recent.length ? (
            <div className="recent-list">
              {recent.map((conversation) => (
                <button
                  className="recent-item"
                  key={conversation.id}
                  onClick={() => onOpenConversation(conversation)}
                >
                  <span className="recent-item-icon"><MessageSquareText size={17} /></span>
                  <span className="recent-item-copy">
                    <strong>{conversation.title}</strong>
                    <small><Clock3 size={12} /> {formatDate(conversation.updated_at)}</small>
                  </span>
                  <span className="recent-item-arrow">→</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="recent-empty">
              <div className="empty-illustration"><MessageSquareText size={22} /></div>
              <strong>Your story starts here</strong>
              <span>Start a conversation and it will show up here.</span>
              <button className="text-action" onClick={onNewChat}>Create your first chat <span>→</span></button>
            </div>
          )}
        </article>
      </section>
      <section className="dashboard-data-section">
        <div className="database-section-heading">
          <div>
            <div className="eyebrow"><span className="eyebrow-dot" /> YOUR WORKSPACE DATA</div>
            <h2>Everything in one place.</h2>
          </div>
          <span className="database-sync-badge"><Database size={14} /> Synced to your account</span>
        </div>
        {dataError && (
          <div className="dashboard-data-error" role="status">{dataError}</div>
        )}
        <div className="database-card-grid">
          <article className="workspace-card database-card">
            <div className="database-card-heading">
              <span className="database-card-icon"><Database size={17} /></span>
              <div><strong>AI usage</strong><small>Across your conversations</small></div>
            </div>
            {dataLoading ? (
              <DataLoading />
            ) : (
              <div className="usage-metrics">
                <div><strong>{formatNumber(usage?.requests)}</strong><span>Requests</span></div>
                <div><strong>{formatNumber(usage?.input_tokens)}</strong><span>Input tokens</span></div>
                <div><strong>{formatNumber(usage?.output_tokens)}</strong><span>Output tokens</span></div>
              </div>
            )}
          </article>

          <article className="workspace-card database-card documents-data-card">
            <div className="database-card-heading">
              <span className="database-card-icon"><FileText size={17} /></span>
              <div><strong>Documents</strong><small>{documents.length} saved to your workspace</small></div>
              <label className="document-upload-button" aria-label="Upload a document">
                {uploadingDocument ? <LoaderCircle className="spin" size={15} /> : <Upload size={15} />}
                <span>{uploadingDocument ? "Uploading" : "Upload"}</span>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  disabled={uploadingDocument}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) onUploadDocument(file);
                    event.target.value = "";
                  }}
                />
              </label>
            </div>
            {dataLoading ? (
              <DataLoading />
            ) : documents.length ? (
              <div className="workspace-document-list">
                {documents.slice(0, 4).map((document) => (
                  <div className="workspace-document-row" key={document.id}>
                    <span className="document-file-icon"><FileText size={15} /></span>
                    <div className="document-file-copy">
                      <strong title={document.original_name}>{document.original_name}</strong>
                      <small>{formatBytes(document.size_bytes)}</small>
                    </div>
                    <span className={`document-status status-${document.status}`}>
                      {document.status}
                    </span>
                    <button
                      className="document-delete-button"
                      aria-label={`Delete ${document.original_name}`}
                      onClick={() => onDeleteDocument(document)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="database-empty-state">Your uploaded documents will appear here.</div>
            )}
          </article>

          <article className="workspace-card database-card">
            <div className="database-card-heading">
              <span className="database-card-icon"><UserRound size={17} /></span>
              <div><strong>Your profile</strong><small>Personal workspace account</small></div>
            </div>
            <ProfileEditor
              user={user}
              profile={profile}
              onSave={onUpdateProfile}
            />
          </article>

          <article className="workspace-card database-card">
            <div className="database-card-heading">
              <span className="database-card-icon"><SlidersHorizontal size={17} /></span>
              <div><strong>Workspace settings</strong><small>Your saved preferences</small></div>
            </div>
            <SettingsEditor settings={settings} onSave={onUpdateSettings} />
          </article>
        </div>
      </section>
      <section className="principle-strip">
        <div className="principle-icon"><ShieldCheck size={18} /></div>
        <div>
          <strong>Your space, your conversations</strong>
          <span>Conversations are private to your account and securely stored in your workspace.</span>
        </div>
        <div className="principle-tag">PRIVATE BY DESIGN</div>
      </section>
      <footer className="dashboard-footer">
        <span>Syntrix AI <span className="footer-dot">·</span> Think Smarter. Work Faster. Create Without Limits.</span>
        <span>Made for your next big idea.</span>
      </footer>
    </div>
  );
}

function ProfileEditor({ user, profile, onSave }) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [values, setValues] = useState({});

  useEffect(() => {
    if (!editing) {
      setValues({
        display_name: profile?.display_name || "",
        bio: profile?.bio || "",
        timezone: profile?.timezone || "UTC",
        avatar_url: profile?.avatar_url || "",
      });
    }
  }, [editing, profile]);

  const update = (field) => (event) => {
    setValues((current) => ({ ...current, [field]: event.target.value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      if (await onSave(values)) setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <>
        <div className="profile-record">
          <div className="profile-record-avatar">
            {(user.username || "U").slice(0, 1).toUpperCase()}
          </div>
          <div className="profile-record-copy">
            <strong>{profile?.display_name || user.username}</strong>
            <span>{user.email || "No email address"}</span>
          </div>
          <button className="record-edit-button" type="button" onClick={() => setEditing(true)}>
            Edit
          </button>
        </div>
        <div className="record-detail-row">
          <span>Username</span><strong>{user.username}</strong>
        </div>
        <div className="record-detail-row">
          <span>Timezone</span><strong>{profile?.timezone || "UTC"}</strong>
        </div>
        {profile?.bio && <p className="profile-bio">{profile.bio}</p>}
      </>
    );
  }

  return (
    <form className="workspace-edit-form" onSubmit={submit}>
      <label>
        Display name
        <input value={values.display_name || ""} onChange={update("display_name")} maxLength={120} />
      </label>
      <label>
        Bio
        <textarea value={values.bio || ""} onChange={update("bio")} maxLength={500} rows={2} />
      </label>
      <label>
        Timezone
        <input value={values.timezone || ""} onChange={update("timezone")} maxLength={64} required />
      </label>
      <label>
        Avatar URL
        <input type="url" value={values.avatar_url || ""} onChange={update("avatar_url")} maxLength={500} />
      </label>
      <div className="workspace-edit-actions">
        <button className="record-edit-button" type="button" disabled={saving} onClick={() => setEditing(false)}>
          Cancel
        </button>
        <button className="button-primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save profile"}
        </button>
      </div>
    </form>
  );
}

function SettingsEditor({ settings, onSave }) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [values, setValues] = useState({});

  useEffect(() => {
    if (!editing) {
      setValues({
        theme: settings?.theme || "system",
        response_tone: settings?.response_tone || "balanced",
        email_notifications: settings?.email_notifications ?? true,
      });
    }
  }, [editing, settings]);

  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      if (await onSave(values)) setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  if (!editing) {
    return (
      <>
        <button className="record-edit-button settings-edit-button" type="button" onClick={() => setEditing(true)}>
          Edit settings
        </button>
        <div className="record-detail-row">
          <span>Appearance preference</span>
          <strong className="record-value-capitalize">{settings?.theme || "system"}</strong>
        </div>
        <div className="record-detail-row">
          <span>Response style</span><strong>{settings?.response_tone || "balanced"}</strong>
        </div>
        <div className="record-detail-row">
          <span>Email notifications</span>
          <strong>{settings?.email_notifications ? "On" : "Off"}</strong>
        </div>
      </>
    );
  }

  return (
    <form className="workspace-edit-form" onSubmit={submit}>
      <label>
        Appearance preference
        <select
          value={values.theme || "system"}
          onChange={(event) => setValues((current) => ({ ...current, theme: event.target.value }))}
        >
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </label>
      <label>
        Response style
        <input
          value={values.response_tone || ""}
          onChange={(event) => setValues((current) => ({ ...current, response_tone: event.target.value }))}
          maxLength={32}
          required
        />
      </label>
      <label className="workspace-edit-checkbox">
        <input
          type="checkbox"
          checked={Boolean(values.email_notifications)}
          onChange={(event) => setValues((current) => ({ ...current, email_notifications: event.target.checked }))}
        />
        Email notifications
      </label>
      <div className="workspace-edit-actions">
        <button className="record-edit-button" type="button" disabled={saving} onClick={() => setEditing(false)}>
          Cancel
        </button>
        <button className="button-primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save settings"}
        </button>
      </div>
    </form>
  );
}

function DataLoading() {
  return (
    <div className="database-loading">
      <LoaderCircle className="spin" size={15} />
      <span>Loading your records…</span>
    </div>
  );
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(value || 0);
}

function formatBytes(value) {
  if (!value) return "0 bytes";
  if (value < 1024) return `${value} bytes`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function ChatPage({ user, conversation, messages, loading, sending, aiMode, onSend, onNewChat }) {
  const title = conversation?.title || "New conversation";

  return (
    <div className="chat-page page-enter">
      <div className="chat-topbar">
        <div className="chat-topbar-title">
          <div className="breadcrumb">Workspace <span>/</span> AI chat</div>
          <h1>{title}</h1>
        </div>
        <div className="chat-topbar-actions">
          <ModeBadge mode={aiMode} />
          <button className="button-secondary new-chat-button" onClick={onNewChat}>
            <Plus size={16} /> New chat
          </button>
        </div>
      </div>
      <div className="chat-content">
        {loading ? (
          <div className="chat-loading"><LoaderCircle className="spin" size={20} /> Loading conversation…</div>
        ) : messages.length ? (
          <MessageList messages={messages} sending={sending} user={user} />
        ) : (
          <div className="chat-welcome">
            <div className="chat-welcome-icon"><Sparkles size={24} /></div>
            <div className="eyebrow"><span className="eyebrow-dot" /> YOUR AI WORKSPACE</div>
            <h2>What’s on your mind?</h2>
            <p>Ask a question, explore an idea, or get help moving your work forward.</p>
            <div className="prompt-grid">
              {prompts.map((prompt) => (
                <button className="prompt-card" key={prompt} onClick={() => onSend(prompt)}>
                  <span>{prompt}</span><span className="prompt-arrow">↗</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
      <ChatComposer onSend={onSend} sending={sending} />
      <div className="chat-disclaimer">
        <ShieldCheck size={13} />
        <span>Private to your workspace</span>
        <span className="disclaimer-separator">·</span>
        <span>AI can make mistakes. Check important information.</span>
      </div>
    </div>
  );
}

function MessageList({ messages, sending, user }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [endRef, messages, sending]);

  return (
    <div className="message-list">
      <div className="message-date-label">Conversation</div>
      {messages.map((message) => (
        <article
          className={`message-row ${message.role === "user" ? "message-row-user" : ""}`}
          key={message.id}
        >
          <div className={`message-avatar ${message.role === "user" ? "message-avatar-user" : ""}`}>
            {message.role === "user" ? (user.username || "U").slice(0, 1).toUpperCase() : <Sparkles size={16} />}
          </div>
          <div className="message-body">
            <div className="message-author">
              {message.role === "user" ? user.username : "Syntrix"}
              <span>{formatTime(message.created_at)}</span>
            </div>
            <div className="message-text">{message.content}</div>
          </div>
        </article>
      ))}
      {sending && (
        <div className="message-row">
          <div className="message-avatar"><Sparkles size={16} /></div>
          <div className="message-body">
            <div className="message-author">Syntrix <span>Thinking</span></div>
            <div className="typing-indicator"><i /><i /><i /></div>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}

function ChatComposer({ onSend, sending }) {
  const [value, setValue] = useState("");
  const submit = async (event) => {
    event?.preventDefault();
    const message = value.trim();
    if (!message || sending) return;
    setValue("");
    try {
      const sent = await onSend(message);
      if (sent === false) setValue(message);
    } catch {
      setValue(message);
    }
  };

  return (
    <form className="composer-wrap" onSubmit={submit}>
      <label className="visually-hidden" htmlFor="chat-message">Message Syntrix</label>
      <textarea
        id="chat-message"
        className="chat-textarea"
        placeholder="Message Syntrix…"
        rows={1}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
        disabled={sending}
      />
      <div className="composer-toolbar">
        <span className="composer-hint">Shift + Enter for a new line</span>
        <button
          className="send-button"
          type="submit"
          disabled={!value.trim() || sending}
          aria-label="Send message"
        >
          {sending ? <LoaderCircle className="spin" size={17} /> : <ArrowUp size={18} />}
        </button>
      </div>
    </form>
  );
}

function AuthScreen({ onSubmit, loading, notice, aiMode, apiOnline, apiMessage }) {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();
    const values = { username: username.trim(), password };
    if (mode === "register") values.email = email.trim();
    onSubmit(mode, values);
  };

  return (
    <div className="auth-page">
      <div className="auth-showcase">
        <BrandMark />
        <div className="auth-showcase-content">
          <div className="auth-showcase-tag"><Sparkles size={14} /> YOUR INTELLIGENT WORKSPACE</div>
          <h1>Room for your<br /><span>best thinking.</span></h1>
          <p>A calmer space to think things through, make progress, and turn ideas into something real.</p>
          <div className="auth-quote">
            <div className="quote-mark">“</div>
            <p>Think Smarter. Work Faster.<br />Create Without Limits.</p>
          </div>
        </div>
        <div className="auth-showcase-footer">Designed for the way you think.</div>
        <div className="auth-orb auth-orb-one" />
        <div className="auth-orb auth-orb-two" />
      </div>
      <div className="auth-panel">
        <div className="auth-mobile-brand"><BrandMark /></div>
        <div className="auth-form-wrap">
          <div className="auth-form-eyebrow">{mode === "login" ? "WELCOME BACK" : "GET STARTED"}</div>
          <h2>{mode === "login" ? "Sign in to Syntrix" : "Create your workspace"}</h2>
          <p className="auth-subtitle">
            {mode === "login"
              ? "Your thoughts and conversations are right where you left them."
              : "A focused place for your ideas, conversations, and work."}
          </p>
          {notice && <div className="auth-error" role="alert">{notice}</div>}
          <form onSubmit={handleSubmit} className="auth-form">
            <label htmlFor="username">Username</label>
            <input id="username" autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} />
            {mode === "register" && (
              <>
                <label htmlFor="email">Email address</label>
                <input id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
              </>
            )}
            <label htmlFor="password">Password</label>
            <div className="password-input-wrap">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={8}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                className="password-visibility-toggle"
                type="button"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
            <button className="button-primary auth-submit" type="submit" disabled={loading}>
              {loading ? <LoaderCircle className="spin" size={17} /> : null}
              {mode === "login" ? "Sign in" : "Create account"}
              {!loading && <ArrowUp className="auth-submit-arrow" size={17} />}
            </button>
          </form>
          <div className="auth-switch">
            {mode === "login" ? "New to Syntrix?" : "Already have an account?"}
            <button onClick={() => { setMode(mode === "login" ? "register" : "login"); }}>
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </div>
          <div className="auth-security-note"><ShieldCheck size={15} /> Your conversations are private to your account.</div>
          <div className={`connection-status ${apiOnline ? "connection-online" : "connection-offline"}`}>
            <span /> {apiOnline ? `API connected · ${aiMode === "demo" ? "Demo AI mode" : "OpenAI connected"}` : "API connection unavailable"}
          </div>
          {!apiOnline && apiMessage && (
            <p className="connection-help">{apiMessage}</p>
          )}
        </div>
        <span className="auth-panel-footer">© 2026 Syntrix AI</span>
      </div>
    </div>
  );
}

function ModeBadge({ mode }) {
  const isLive = mode === "live";
  const isDemo = mode === "demo";
  const label = isLive
    ? "AI connected"
    : isDemo
      ? "Demo mode"
      : "AI status unavailable";
  const title = isLive
    ? "OpenAI responses enabled"
    : isDemo
      ? "OpenAI key not configured; demo responses enabled"
      : "Connect to the API to check the AI mode";
  return (
    <span className={`mode-badge ${isLive ? "mode-live" : isDemo ? "mode-demo" : "mode-unknown"}`} title={title}>
      <span className="mode-dot" />
      {label}
    </span>
  );
}

function formatDate(value) {
  if (!value) return "Just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Just now";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
}

function formatTime(value) {
  if (!value) return "Now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Now";
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
}

export default App;
