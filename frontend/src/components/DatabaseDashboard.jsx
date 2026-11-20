import { useEffect, useState } from "react";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  FileText,
  Layers3,
  LoaderCircle,
  MessageSquareText,
  RefreshCw,
  Search,
  Table2,
  Users,
  XCircle,
} from "lucide-react";
import { workspaceApi } from "../services/api.js";
import "./DatabaseDashboard.css";

const PAGE_SIZE = 10;

const RESOURCE_TABLES = [
  {
    resource: "users",
    title: "Users",
    description: "Account identity and status; credentials are never included.",
    searchPlaceholder: "Search name, username, or email",
    defaultSort: "-date_joined",
    sortOptions: [
      ["-date_joined", "Newest"],
      ["date_joined", "Oldest"],
      ["username", "Username A–Z"],
      ["-username", "Username Z–A"],
    ],
    columns: [
      ["id", "ID"],
      ["full_name", "Full name"],
      ["username", "Username"],
      ["email", "Email"],
      ["account_status", "Status"],
      ["date_joined", "Date joined"],
    ],
  },
  {
    resource: "profiles",
    title: "User profiles",
    description: "Profile information from each user's saved profile.",
    searchPlaceholder: "Search user, display name, or bio",
    defaultSort: "user__username",
    sortOptions: [
      ["user__username", "Username A–Z"],
      ["-user__username", "Username Z–A"],
      ["-created_at", "Newest"],
      ["created_at", "Oldest"],
    ],
    columns: [
      ["user_id", "User ID"],
      ["full_name", "Full name"],
      ["display_name", "Display name"],
      ["bio", "Bio"],
      ["timezone", "Timezone"],
      ["avatar_url", "Avatar URL"],
      ["created_at", "Created"],
    ],
  },
  {
    resource: "settings",
    title: "User settings",
    description: "Saved preferences associated with each account.",
    searchPlaceholder: "Search user, theme, or response style",
    defaultSort: "user__username",
    sortOptions: [
      ["user__username", "Username A–Z"],
      ["-user__username", "Username Z–A"],
      ["-created_at", "Newest"],
      ["created_at", "Oldest"],
    ],
    columns: [
      ["user_id", "User ID"],
      ["user_name", "Username"],
      ["theme", "Theme"],
      ["response_tone", "Response style"],
      ["email_notifications", "Email notifications"],
      ["created_at", "Created"],
    ],
  },
  {
    resource: "conversations",
    title: "Conversations",
    description: "Conversation owners, titles, timestamps, and message totals.",
    searchPlaceholder: "Search title or user",
    defaultSort: "-updated_at",
    sortOptions: [
      ["-updated_at", "Recently updated"],
      ["updated_at", "Least recently updated"],
      ["-created_at", "Newest"],
      ["created_at", "Oldest"],
      ["title", "Title A–Z"],
      ["-title", "Title Z–A"],
    ],
    columns: [
      ["conversation_id", "Conversation ID"],
      ["user_name", "User"],
      ["title", "Title"],
      ["message_count", "Messages"],
      ["created_at", "Created"],
      ["updated_at", "Updated"],
    ],
  },
  {
    resource: "messages",
    title: "Messages",
    description: "Message content is restricted to administrators.",
    searchPlaceholder: "Search message text, type, or user",
    defaultSort: "-created_at",
    sortOptions: [
      ["-created_at", "Newest"],
      ["created_at", "Oldest"],
      ["role", "Type A–Z"],
      ["-role", "Type Z–A"],
    ],
    columns: [
      ["message_id", "Message ID"],
      ["conversation_id", "Conversation ID"],
      ["user_name", "User"],
      ["message_type", "Type"],
      ["content", "Content"],
      ["created_at", "Created"],
    ],
  },
  {
    resource: "usage_logs",
    title: "AI usage logs",
    description: "Model and token usage from actual AI usage records.",
    searchPlaceholder: "Search user, model, or provider",
    defaultSort: "-created_at",
    sortOptions: [
      ["-created_at", "Newest"],
      ["created_at", "Oldest"],
      ["model", "Model A–Z"],
      ["-model", "Model Z–A"],
      ["-input_tokens", "Most input tokens"],
      ["input_tokens", "Fewest input tokens"],
    ],
    columns: [
      ["log_id", "Log ID"],
      ["user_name", "User"],
      ["model_name", "Model"],
      ["provider", "Provider"],
      ["input_tokens", "Input tokens"],
      ["output_tokens", "Output tokens"],
      ["total_tokens", "Total"],
      ["created_at", "Created"],
    ],
  },
  {
    resource: "documents",
    title: "Uploaded documents",
    description: "Document metadata only; private file contents are not exposed.",
    searchPlaceholder: "Search file name, type, or user",
    defaultSort: "-created_at",
    sortOptions: [
      ["-created_at", "Newest"],
      ["created_at", "Oldest"],
      ["original_name", "File name A–Z"],
      ["-original_name", "File name Z–A"],
      ["-size_bytes", "Largest"],
      ["size_bytes", "Smallest"],
    ],
    columns: [
      ["document_id", "Document ID"],
      ["user_name", "User"],
      ["file_name", "File name"],
      ["file_type", "File type"],
      ["size_bytes", "Size (bytes)"],
      ["status", "Status"],
      ["uploaded_at", "Uploaded"],
    ],
  },
];

function getErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    "Database information could not be loaded. Please try again."
  );
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(value || 0);
}

function formatValue(value, field) {
  if (value === null || value === undefined || value === "") return "—";
  if (field.endsWith("_at") || field === "date_joined") return formatDate(value);
  if (field === "email_notifications") return value ? "On" : "Off";
  return String(value);
}

function DatabaseResourceTable({ config, refreshKey }) {
  const [data, setData] = useState(null);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState(config.defaultSort);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    workspaceApi
      .adminDatabase({
        resource: config.resource,
        search,
        sort,
        page,
        page_size: PAGE_SIZE,
      })
      .then(({ data: response }) => {
        if (active) {
          setData(response);
          setError("");
        }
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [config.resource, page, refreshKey, search, sort]);

  const totalPages = Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE));

  return (
    <section className="db-panel">
      <div className="db-panel-heading">
        <div>
          <h2>{config.title}</h2>
          <p>{config.description}</p>
        </div>
        <span className="db-panel-count">{formatNumber(data?.count)} records</span>
      </div>
      <div className="db-table-toolbar">
        <label className="db-search">
          <Search size={16} />
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder={config.searchPlaceholder}
            aria-label={`Search ${config.title.toLowerCase()}`}
          />
        </label>
        <label className="db-sort">
          <span>Sort by</span>
          <select
            value={sort}
            onChange={(event) => {
              setSort(event.target.value);
              setPage(1);
            }}
            aria-label={`Sort ${config.title.toLowerCase()}`}
          >
            {config.sortOptions.map(([value, label]) => (
              <option value={value} key={value}>{label}</option>
            ))}
          </select>
        </label>
      </div>
      {error && <div className="db-table-error" role="alert">{error}</div>}
      {loading ? (
        <div className="db-loading">
          <LoaderCircle className="spin" size={18} />
          Loading {config.title.toLowerCase()}…
        </div>
      ) : (
        <div className="db-table-wrap">
          <table className="db-table">
            <thead>
              <tr>
                {config.columns.map(([, label]) => <th key={label}>{label}</th>)}
              </tr>
            </thead>
            <tbody>
              {(data?.results || []).map((record, rowIndex) => {
                const rowKey =
                  record.id ??
                  record.user_id ??
                  record.conversation_id ??
                  record.message_id ??
                  record.log_id ??
                  record.document_id ??
                  `${config.resource}-${rowIndex}`;
                return (
                  <tr key={rowKey}>
                    {config.columns.map(([field]) => (
                      <td key={field} title={String(record[field] ?? "")}>
                        {formatValue(record[field], field)}
                      </td>
                    ))}
                  </tr>
                );
              })}
              {!data?.results?.length && (
                <tr>
                  <td className="db-empty-cell" colSpan={config.columns.length}>
                    No {config.title.toLowerCase()} match this search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
      <div className="db-pager">
        <span>{formatNumber(data?.count)} records</span>
        <div className="db-pager-controls">
          <span>Page {page} of {totalPages}</span>
          <button
            type="button"
            aria-label={`Previous ${config.title} page`}
            disabled={!data?.previous || loading}
            onClick={() => setPage((current) => current - 1)}
          >
            <ChevronLeft size={16} />
          </button>
          <button
            type="button"
            aria-label={`Next ${config.title} page`}
            disabled={!data?.next || loading}
            onClick={() => setPage((current) => current + 1)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </section>
  );
}

function DatabaseDashboard() {
  const [overview, setOverview] = useState(null);
  const [loadingOverview, setLoadingOverview] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoadingOverview(true);
    workspaceApi
      .adminDatabase({ resource: "overview" })
      .then(({ data }) => {
        if (active) {
          setOverview(data);
          setError("");
        }
      })
      .catch((requestError) => {
        if (active) setError(getErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setLoadingOverview(false);
      });
    return () => {
      active = false;
    };
  }, [refreshKey]);

  const summary = overview?.summary || {};
  const database = overview?.database;

  return (
    <div className="database-dashboard-page page-enter">
      <div className="db-page-topline">
        <div className="breadcrumb">Workspace <span>/</span> Database</div>
        <button
          type="button"
          className="db-refresh-button"
          disabled={loadingOverview}
          onClick={() => {
            setError("");
            setRefreshKey((key) => key + 1);
          }}
        >
          <RefreshCw size={16} className={loadingOverview ? "spin" : ""} />
          Refresh data
        </button>
      </div>

      <header className="db-page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-dot" /> ADMINISTRATION</div>
          <h1>Database overview</h1>
          <p>Inspect protected database records and workspace activity.</p>
        </div>
      </header>

      {error && (
        <div className="db-error-banner" role="alert">
          <XCircle size={17} />
          <span>{error}</span>
          <button type="button" onClick={() => setRefreshKey((key) => key + 1)}>
            Retry
          </button>
        </div>
      )}

      <section className="db-summary-grid" aria-label="Database summary">
        <SummaryCard icon={<Database size={18} />} label="Connection">
          <strong className="db-connection-value">
            {loadingOverview ? "Checking…" : database?.status || "Unavailable"}
          </strong>
          <small>{database?.engine || "Database engine"}</small>
        </SummaryCard>
        <SummaryCard icon={<Table2 size={18} />} label="Database">
          <strong className="db-summary-name">
            {loadingOverview ? "Loading…" : database?.name || "Unavailable"}
          </strong>
          <small>Configured database name</small>
        </SummaryCard>
        <SummaryCard icon={<Users size={18} />} label="Total users">
          <strong>{formatNumber(summary.users)}</strong>
          <small>Registered accounts</small>
        </SummaryCard>
        <SummaryCard icon={<MessageSquareText size={18} />} label="Conversations">
          <strong>{formatNumber(summary.conversations)}</strong>
          <small>Saved conversations</small>
        </SummaryCard>
        <SummaryCard icon={<MessageSquareText size={18} />} label="Messages">
          <strong>{formatNumber(summary.messages)}</strong>
          <small>Stored chat messages</small>
        </SummaryCard>
        <SummaryCard icon={<FileText size={18} />} label="Documents">
          <strong>{formatNumber(summary.documents)}</strong>
          <small>Uploaded document records</small>
        </SummaryCard>
        <SummaryCard icon={<Layers3 size={18} />} label="AI usage logs">
          <strong>{formatNumber(summary.ai_usage_logs)}</strong>
          <small>Recorded AI requests</small>
        </SummaryCard>
        <SummaryCard icon={<Layers3 size={18} />} label="Tables & models">
          <strong>{formatNumber(overview?.tables?.length)} tables</strong>
          <small>{formatNumber(overview?.models?.length)} registered models</small>
        </SummaryCard>
      </section>

      <section className="db-panel">
        <div className="db-panel-heading">
          <div>
            <h2>Database schema</h2>
            <p>Actual tables and registered Django model record counts.</p>
          </div>
          <span className="db-panel-count">{formatNumber(overview?.models?.length)} models</span>
        </div>
        {loadingOverview ? (
          <div className="db-loading"><LoaderCircle className="spin" size={18} /> Loading schema…</div>
        ) : (
          <div className="db-table-wrap">
            <table className="db-table">
              <thead>
                <tr><th>Model</th><th>Table</th><th className="db-align-right">Records</th></tr>
              </thead>
              <tbody>
                {(overview?.models || []).map((model) => (
                  <tr key={model.name}>
                    <td>{model.name}</td>
                    <td><code>{model.table}</code></td>
                    <td className="db-align-right">{formatNumber(model.record_count)}</td>
                  </tr>
                ))}
                {!overview?.models?.length && (
                  <tr><td className="db-empty-cell" colSpan="3">No model data available.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        <div className="db-table-list">
          {(overview?.tables || []).map((table) => <span key={table}>{table}</span>)}
        </div>
      </section>

      {RESOURCE_TABLES.map((config) => (
        <DatabaseResourceTable
          key={config.resource}
          config={config}
          refreshKey={refreshKey}
        />
      ))}

      <footer className="db-dashboard-footer">
        <span>
          {database?.status === "connected" ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
          {database?.status === "connected"
            ? "Database connection is healthy"
            : "Database status unavailable"}
        </span>
        <span>AI mode: {overview?.ai_mode || "—"}</span>
      </footer>
    </div>
  );
}

function SummaryCard({ icon, label, children }) {
  return (
    <article className="db-summary-card">
      <div className="db-summary-icon">{icon}</div>
      <span>{label}</span>
      {children}
    </article>
  );
}

export default DatabaseDashboard;
