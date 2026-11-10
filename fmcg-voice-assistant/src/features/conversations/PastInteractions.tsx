
import { useEffect, useMemo, useState } from "react";
import api from "../../services/api";

interface ConversationRecord {
    id: number;
    retailer_name?: string;
    retailer?: number | { name?: string };
    status?: string;
    outcome?: string;
    summary?: string;
    channel?: string;
    language?: string;
    created_at?: string;
    started_at?: string;
    ended_at?: string;
    message_count?: number;
    messages?: any[];
    captures?: any[];
    orders?: any[];
    followups?: any[];
    [key: string]: any;
}

const formatLabel = (value?: string) => {
    if (!value) return "Not available";

    return value
        .replace(/_/g, " ")
        .toLowerCase()
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const formatDate = (value?: string) => {
    if (!value) return "Date unavailable";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return value;

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
};

const getRetailerName = (conversation: ConversationRecord) => {
    if (conversation.retailer_name) return conversation.retailer_name;

    if (
        conversation.retailer &&
        typeof conversation.retailer === "object"
    ) {
        return conversation.retailer.name || "Unknown retailer";
    }

    return "Unknown retailer";
};

const unwrapData = (response: any): any => {
    const body = response?.data ?? response;

    if (body?.results !== undefined) return body.results;
    if (body?.data !== undefined) return body.data;

    return body;
};

export default function PastInteractions({
    onBack,
}: {
    onBack?: () => void;
}) {
    const [conversations, setConversations] = useState<ConversationRecord[]>([]);
    const [selectedConversation, setSelectedConversation] =
        useState<ConversationRecord | null>(null);

    const [search, setSearch] = useState("");
    const [outcomeFilter, setOutcomeFilter] = useState("ALL");
    const [loading, setLoading] = useState(true);
    const [detailLoading, setDetailLoading] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        const loadConversations = async () => {
            try {
                setLoading(true);
                setError("");

                const response = await api.get("/conversations/");
                const data = unwrapData(response);

                setConversations(
                    Array.isArray(data)
                        ? data
                        : Array.isArray(data?.results)
                            ? data.results
                            : []
                );
            } catch (err: any) {
                setError(
                    err?.response?.data?.message ||
                    "Unable to load past conversations."
                );
            } finally {
                setLoading(false);
            }
        };

        loadConversations();
    }, []);

    const filteredConversations = useMemo(() => {
        return conversations.filter((conversation) => {
            const retailerName = getRetailerName(conversation).toLowerCase();
            const summary = (conversation.summary || "").toLowerCase();
            const searchText = search.toLowerCase();

            const matchesSearch =
                retailerName.includes(searchText) ||
                summary.includes(searchText);

            const matchesOutcome =
                outcomeFilter === "ALL" ||
                conversation.outcome === outcomeFilter;

            return matchesSearch && matchesOutcome;
        });
    }, [conversations, search, outcomeFilter]);

    const openConversation = async (conversation: ConversationRecord) => {
        try {
            setDetailLoading(true);
            setError("");

            const response = await api.get(
                `/conversations/${conversation.id}/`
            );

            const detail = unwrapData(response);

            setSelectedConversation(
                detail && typeof detail === "object"
                    ? detail
                    : conversation
            );
        } catch (err: any) {
            // The list endpoint may already contain the nested details.
            setSelectedConversation(conversation);
            setError(
                err?.response?.data?.message ||
                "Could not load additional conversation details."
            );
        } finally {
            setDetailLoading(false);
        }
    };

    const closeDetail = () => {
        setSelectedConversation(null);
        setError("");
    };

    if (selectedConversation) {
        const conversation = selectedConversation;

        return (
            <section className="history-page">
                <div className="history-page-heading">
                    <div>
                        <button
                            className="history-back-button"
                            onClick={closeDetail}
                        >
                            ← Back to conversations
                        </button>

                        <p className="eyebrow">PAST INTERACTIONS</p>
                        <h2>{getRetailerName(conversation)}</h2>
                        <p className="history-muted">
                            {formatDate(
                                conversation.started_at ||
                                conversation.created_at
                            )}
                        </p>
                    </div>

                    <span className="panel-tag">
                        {formatLabel(conversation.outcome)}
                    </span>
                </div>

                {detailLoading && (
                    <p className="history-muted">Loading details...</p>
                )}

                {error && (
                    <div className="history-error">{error}</div>
                )}

                <div className="history-detail-grid">
                    <div className="panel history-detail-card">
                        <h3>Conversation Summary</h3>
                        <p>
                            {conversation.summary ||
                                "No summary is available for this conversation."}
                        </p>

                        <div className="history-meta">
                            <span>Outcome</span>
                            <strong>
                                {formatLabel(conversation.outcome)}
                            </strong>
                        </div>

                        <div className="history-meta">
                            <span>Status</span>
                            <strong>
                                {formatLabel(conversation.status)}
                            </strong>
                        </div>

                        <div className="history-meta">
                            <span>Channel</span>
                            <strong>
                                {formatLabel(conversation.channel)}
                            </strong>
                        </div>

                        <div className="history-meta">
                            <span>Language</span>
                            <strong>
                                {formatLabel(conversation.language)}
                            </strong>
                        </div>
                    </div>

                    <div className="panel history-detail-card">
                        <h3>Captured Products</h3>

                        {conversation.captures?.length ? (
                            conversation.captures.map((capture, index) => (
                                <div
                                    className="history-item"
                                    key={capture.id || index}
                                >
                                    <strong>
                                        {capture.product_name ||
                                            capture.variant_name ||
                                            "Product"}
                                    </strong>
                                    {capture.variant_name && (
                                        <span>{capture.variant_name}</span>
                                    )}
                                    {capture.quantity != null && (
                                        <span>
                                            Quantity: {capture.quantity}
                                        </span>
                                    )}
                                    {capture.notes && (
                                        <p>{capture.notes}</p>
                                    )}
                                </div>
                            ))
                        ) : (
                            <p className="history-muted">
                                No product captures recorded.
                            </p>
                        )}
                    </div>
                </div>

                <div className="panel history-section">
                    <h3>Conversation Transcript</h3>

                    {conversation.messages?.length ? (
                        <div className="history-transcript">
                            {conversation.messages.map((message, index) => (
                                <div
                                    className={`history-message ${
                                        message.speaker === "RETAILER"
                                            ? "history-message-retailer"
                                            : "history-message-agent"
                                    }`}
                                    key={message.id || index}
                                >
                                    <div className="history-message-heading">
                                        <strong>
                                            {formatLabel(message.speaker)}
                                        </strong>
                                        <span>
                                            {formatDate(message.created_at)}
                                        </span>
                                    </div>
                                    <p>{message.content}</p>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="history-muted">
                            No transcript messages are available.
                        </p>
                    )}
                </div>

                <div className="history-detail-grid">
                    <div className="panel history-detail-card">
                        <h3>Orders</h3>

                        {conversation.orders?.length ? (
                            conversation.orders.map((order, index) => (
                                <div
                                    className="history-item"
                                    key={order.id || index}
                                >
                                    <strong>
                                        {order.order_number ||
                                            `Order ${index + 1}`}
                                    </strong>
                                    <span>
                                        Status: {formatLabel(order.status)}
                                    </span>
                                    {order.total_amount != null && (
                                        <span>
                                            Total: ₹{order.total_amount}
                                        </span>
                                    )}
                                </div>
                            ))
                        ) : (
                            <p className="history-muted">
                                No order details available.
                            </p>
                        )}
                    </div>

                    <div className="panel history-detail-card">
                        <h3>Follow-ups</h3>

                        {conversation.followups?.length ? (
                            conversation.followups.map((followup, index) => (
                                <div
                                    className="history-item"
                                    key={followup.id || index}
                                >
                                    <strong>{followup.title}</strong>
                                    <span>
                                        Status: {formatLabel(followup.status)}
                                    </span>
                                    {followup.due_at && (
                                        <span>
                                            Due: {formatDate(followup.due_at)}
                                        </span>
                                    )}
                                    {followup.description && (
                                        <p>{followup.description}</p>
                                    )}
                                </div>
                            ))
                        ) : (
                            <p className="history-muted">
                                No follow-ups recorded.
                            </p>
                        )}
                    </div>
                </div>
            </section>
        );
    }

    return (
        <section className="history-page">
            <div className="history-page-heading">
                <div>
                    <p className="eyebrow">CONVERSATION MANAGEMENT</p>
                    <h2>Past Interactions</h2>
                    <p className="history-muted">
                        Review previous retailer conversations and their outcomes.
                    </p>
                </div>

                {onBack && (
                    <button
                        className="history-back-button"
                        onClick={onBack}
                    >
                        Back to Dashboard
                    </button>
                )}
            </div>

            <div className="history-toolbar">
                <input
                    type="search"
                    placeholder="Search retailer or summary..."
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                />

                <select
                    value={outcomeFilter}
                    onChange={(event) => setOutcomeFilter(event.target.value)}
                >
                    <option value="ALL">All outcomes</option>
                    <option value="ORDER_REQUESTED">Order requested</option>
                    <option value="FOLLOWUP_REQUIRED">Follow-up required</option>
                    <option value="INTERESTED">Interested</option>
                    <option value="ENQUIRY">Enquiry</option>
                    <option value="NOT_INTERESTED">Not interested</option>
                    <option value="NO_ACTION">No action</option>
                </select>
            </div>

            {error && <div className="history-error">{error}</div>}

            {loading ? (
                <div className="panel history-empty">
                    Loading conversations...
                </div>
            ) : filteredConversations.length === 0 ? (
                <div className="panel history-empty">
                    <h3>No conversations found</h3>
                    <p>
                        Completed retailer conversations will appear here.
                    </p>
                </div>
            ) : (
                <div className="history-list">
                    {filteredConversations.map((conversation) => (
                        <article
                            className="panel history-card"
                            key={conversation.id}
                        >
                            <div className="history-card-top">
                                <div>
                                    <h3>{getRetailerName(conversation)}</h3>
                                    <span className="history-muted">
                                        {formatDate(
                                            conversation.started_at ||
                                            conversation.created_at
                                        )}
                                    </span>
                                </div>

                                <span className="panel-tag">
                                    {formatLabel(conversation.outcome)}
                                </span>
                            </div>

                            <p className="history-summary">
                                {conversation.summary ||
                                    "No summary available."}
                            </p>

                            <div className="history-card-bottom">
                                <span>
                                    {formatLabel(conversation.status)}
                                </span>
                                <button
                                    className="history-view-button"
                                    onClick={() =>
                                        openConversation(conversation)
                                    }
                                >
                                    View conversation →
                                </button>
                            </div>
                        </article>
                    ))}
                </div>
            )}
        </section>
    );
}
