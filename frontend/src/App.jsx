import React, { useEffect, useRef, useState } from "react";
import { initKeycloak, keycloak, logoutUser } from "./services/auth";
import { api } from "./services/api";

const MAX_UPLOAD_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB || 30);
const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;

function DataTutorMascot({ compact = false }) {
  return (
    <div
      className={`mascot ${compact ? "mascot-compact" : ""}`}
      role="img"
      aria-label="Mascota robótica de DataTutor"
    >
      <div className="mascot-aura" aria-hidden="true" />
      <div className="mascot-antenna" aria-hidden="true">
        <span />
      </div>
      <div className="mascot-screen">
        <span className="mascot-eye mascot-eye-left" />
        <span className="mascot-eye mascot-eye-right" />
        <span className="mascot-mouth" />
      </div>
      <div className="mascot-body">
        <span className="mascot-chip">DT</span>
        <span className="mascot-scanline" />
      </div>
      <span className="mascot-foot mascot-foot-left" aria-hidden="true" />
      <span className="mascot-foot mascot-foot-right" aria-hidden="true" />
    </div>
  );
}

export default function App() {
  const [authReady, setAuthReady] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [userProfile, setUserProfile] = useState(null);

  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);

  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [deletingDocId, setDeletingDocId] = useState(null);
  const [errorBanner, setErrorBanner] = useState(null);

  const didLoadRef = useRef(false);
  const pollingInFlightRef = useRef(false);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const hasPendingDocs = documents.some(
    (d) => d.status === "pending" || d.status === "processing"
  );

  useEffect(() => {
    if (didLoadRef.current) return;
    didLoadRef.current = true;

    initKeycloak()
      .then(async (authenticated) => {
        if (!authenticated) {
          await keycloak.login({ redirectUri: window.location.origin + "/" });
          return;
        }
        setAuthReady(true);
        await loadInitialData();
      })
      .catch((err) => {
        setAuthError(
          `Error iniciando sesión con Keycloak: ${
            err?.message ||
            "Verifica que datatutor-keycloak esté activo en el puerto 8080."
          }`
        );
      });
  }, []);

  useEffect(() => {
    if (!authReady || !hasPendingDocs) return;

    const timer = setInterval(async () => {
      if (pollingInFlightRef.current) return;
      pollingInFlightRef.current = true;
      try {
        const docs = await api.listDocuments();
        setDocuments(docs);
      } catch (err) {
        // Silencioso durante polling periódico
      } finally {
        pollingInFlightRef.current = false;
      }
    }, 3000);

    return () => clearInterval(timer);
  }, [authReady, hasPendingDocs]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function loadInitialData() {
    try {
      setErrorBanner(null);
      const [me, convs, docs] = await Promise.all([
        api.getMe(),
        api.listConversations(),
        api.listDocuments(),
      ]);
      setUserProfile(me);
      setConversations(convs);
      setDocuments(docs);
    } catch (err) {
      setErrorBanner(err.message);
    }
  }

  async function handleSelectConversation(convId) {
    if (sending || loadingMessages) return;
    setErrorBanner(null);
    setActiveConvId(convId);
    setLoadingMessages(true);
    try {
      const msgs = await api.getConversationMessages(convId);
      setMessages(msgs);
    } catch (err) {
      setErrorBanner(err.message);
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  }

  function handleNewConversation() {
    if (sending) return;
    setActiveConvId(null);
    setMessages([]);
    setErrorBanner(null);
  }

  async function handleDeleteConversation(e, convId) {
    e.stopPropagation();
    if (sending) return;

    const confirmed = window.confirm(
      "¿Estás seguro de que deseas eliminar esta conversación y todos sus mensajes?"
    );
    if (!confirmed) return;

    try {
      setErrorBanner(null);
      await api.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) {
        setActiveConvId(null);
        setMessages([]);
      }
    } catch (err) {
      setErrorBanner(err.message);
    }
  }

  async function handleSendQuestion(e) {
    e.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 2 || sending) return;

    setErrorBanner(null);
    setSending(true);

    const tempId = `temp-user-${Date.now()}`;
    const optimisticUserMsg = {
      id: tempId,
      role: "user",
      content: trimmed,
    };

    const convIdForRequest = activeConvId;
    setMessages((prev) => [...prev, optimisticUserMsg]);
    setQuestion("");

    try {
      const response = await api.sendMessage(trimmed, convIdForRequest);
      setActiveConvId(response.conversation_id);

      const assistantMsg = {
        id: `resp-assistant-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        decision: response.decision,
        sources: response.sources || [],
        latency_ms: response.latency_ms,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      try {
        const updatedConvs = await api.listConversations();
        setConversations(updatedConvs);
      } catch (refreshErr) {
        // Un error refrescando la barra lateral no invalida la respuesta ya recibida
      }
    } catch (err) {
      // Si el backend creó la conversación y guardó la pregunta antes de fallar (503),
      // fijamos ese conversationId para no duplicar conversaciones al reintentar.
      if (err.conversationId) {
        setActiveConvId(err.conversationId);
        try {
          const [updatedConvs, persistedMsgs] = await Promise.all([
            api.listConversations(),
            api.getConversationMessages(err.conversationId),
          ]);
          setConversations(updatedConvs);
          setMessages(persistedMsgs);
        } catch (syncErr) {
          // Conservamos el mensaje optimista en pantalla si falla la sincronización
        }
      } else {
        setMessages((prev) => prev.filter((m) => m.id !== tempId));
        setQuestion(trimmed);
      }
      setErrorBanner(err.message);
    } finally {
      setSending(false);
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    setErrorBanner(null);
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setErrorBanner("Solo se admiten archivos PDF (.pdf).");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size === 0) {
      setErrorBanner("El archivo seleccionado está vacío.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      setErrorBanner(
        `El archivo supera el tamaño máximo permitido de ${MAX_UPLOAD_MB} MB.`
      );
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setUploading(true);
    try {
      await api.uploadDocument(file);
      const docs = await api.listDocuments();
      setDocuments(docs);
    } catch (err) {
      setErrorBanner(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleDeleteDocument(docId) {
    if (deletingDocId) return;
    setErrorBanner(null);
    setDeletingDocId(docId);
    try {
      await api.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      setErrorBanner(err.message);
    } finally {
      setDeletingDocId(null);
    }
  }

  if (authError) {
    return (
      <main className="page-state" role="alert">
        <h2>Error de Autenticación</h2>
        <p style={{ marginTop: 12, color: "#991b1b" }}>{authError}</p>
      </main>
    );
  }

  if (!authReady) {
    return (
      <main className="page-state" aria-live="polite">
        <div className="loading-spinner" aria-hidden="true" />
        <p>Verificando sesión segura con Keycloak (OIDC + PKCE S256)...</p>
      </main>
    );
  }

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand-header">
          <div className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">DT</div>
            <div>
              <span className="brand-title">DataTutor</span>
              <span className="brand-subtitle">DATA ENGINEERING LAB</span>
            </div>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleNewConversation}
            disabled={sending}
            aria-label="Iniciar una nueva conversación"
          >
            + Nuevo Chat
          </button>
        </div>

        <div className="user-bar">
          <div>
            <strong>{userProfile?.preferred_username || "Estudiante"}</strong>
            <div className="doc-meta">
              Roles: {userProfile?.roles?.join(", ") || "user"}
            </div>
          </div>
          <span className="online-dot" title="Sesión activa" aria-label="Sesión activa" />
          <button
            type="button"
            className="btn btn-secondary"
            onClick={logoutUser}
            aria-label="Cerrar sesión"
          >
            Salir
          </button>
        </div>

        <div>
          <div className="section-title">Historial de Conversaciones</div>
          <div className="item-list">
            {conversations.length === 0 && (
              <div className="empty-list-message">Sin conversaciones guardadas.</div>
            )}
            {conversations.map((c) => (
              <div
                key={c.id}
                className={`list-item ${activeConvId === c.id ? "active" : ""}`}
                onClick={() => handleSelectConversation(c.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelectConversation(c.id);
                  }
                }}
                aria-current={activeConvId === c.id ? "true" : undefined}
              >
                <span
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  title={c.title}
                >
                  {c.title}
                </span>
                <button
                  type="button"
                  className="btn btn-danger"
                  title="Eliminar conversación"
                  aria-label={`Eliminar conversación: ${c.title}`}
                  onClick={(e) => handleDeleteConversation(e, c.id)}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="section-title">
            Base de Conocimiento (PDF máx. {MAX_UPLOAD_MB} MB)
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileUpload}
            disabled={uploading}
            style={{ display: "none" }}
          />
          <button
            type="button"
            className="btn btn-primary"
            style={{ width: "100%", marginBottom: 10 }}
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
            aria-label={`Subir documento PDF de máximo ${MAX_UPLOAD_MB} MB`}
          >
            {uploading ? "Subiendo PDF..." : "Subir Documento PDF"}
          </button>

          <div className="item-list" style={{ maxHeight: 280 }}>
            {documents.length === 0 && (
              <div className="empty-list-message">
                Aún no hay documentos disponibles.
              </div>
            )}
            {documents.map((doc) => (
              <div key={doc.id} className="list-item" style={{ cursor: "default" }}>
                <div style={{ overflow: "hidden", flex: 1 }}>
                  <div
                    style={{
                      fontWeight: 600,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={doc.filename}
                  >
                    {doc.filename}
                  </div>
                  <div className="doc-meta">
                    <span className={`badge badge-${doc.status}`}>
                      {doc.status}
                    </span>{" "}
                    · {doc.scope} · {doc.pages} págs ({doc.chunks_count} chunks)
                  </div>
                  {doc.error && (
                    <div
                      style={{
                        color: "#f87171",
                        fontSize: "0.72rem",
                        marginTop: 2,
                      }}
                    >
                      {doc.error}
                    </div>
                  )}
                </div>
                {doc.scope === "user" &&
                  doc.status !== "pending" &&
                  doc.status !== "processing" && (
                    <button
                      type="button"
                      className="btn btn-danger"
                      title="Eliminar documento propio"
                      aria-label={`Eliminar documento: ${doc.filename}`}
                      disabled={deletingDocId === doc.id}
                      onClick={() => handleDeleteDocument(doc.id)}
                    >
                      ✕
                    </button>
                  )}
              </div>
            ))}
          </div>
        </div>
      </aside>

      <main className="chat-main">
        <header className="workspace-header">
          <div>
            <span className="eyebrow">KNOWLEDGE OPERATIONS / 01</span>
            <h1>{activeConvId ? "Conversación activa" : "Centro de conocimiento"}</h1>
          </div>
          <div className="system-status">
            <span className="status-pulse" aria-hidden="true" />
            <span>SISTEMA OPERATIVO</span>
          </div>
        </header>
        {errorBanner && (
          <div className="alert-banner" role="alert" aria-live="assertive">
            <span>⚠️ {errorBanner}</span>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setErrorBanner(null)}
              aria-label="Cerrar mensaje de error"
            >
              Cerrar
            </button>
          </div>
        )}

        <div className="messages-container">
          {loadingMessages ? (
            <div className="empty-state" aria-live="polite">
              <div className="loading-spinner" aria-hidden="true" />
              Cargando mensajes de la conversación...
            </div>
          ) : messages.length === 0 ? (
            <div className="empty-state">
              <DataTutorMascot />
              <span className="eyebrow">RAG // READY TO QUERY</span>
              <h3>Explora tu conocimiento</h3>
              <p>
                Formula una pregunta sobre ingeniería de datos, bases de datos o ciencia de datos.
                DataTutor buscará evidencia en tu base documental y mostrará sus fuentes.
              </p>
              <div className="pipeline-preview" aria-label="Flujo del agente">
                <span>INGEST</span><i>→</i><span>EMBED</span><i>→</i><span>RETRIEVE</span><i>→</i><span>ANSWER</span>
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`message-card ${
                  m.role === "user"
                    ? "message-user"
                    : `message-assistant ${m.decision || ""}`
                }`}
              >
                {m.role === "assistant" && (
                  <div className="message-header">
                    <strong>DataTutor</strong>
                    {m.decision && (
                      <span className={`badge badge-${m.decision}`}>
                        {m.decision}
                      </span>
                    )}
                    {m.latency_ms !== undefined && m.latency_ms !== null && (
                      <span>· {m.latency_ms} ms</span>
                    )}
                  </div>
                )}

                <div className="message-body">
                  {m.content || m.answer || m.text || "(Mensaje sin contenido de texto)"}
                </div>

                {m.role === "assistant" &&
                  Array.isArray(m.sources) &&
                  m.sources.length > 0 && (
                    <div className="sources-box">
                      <strong>Fuentes recuperadas ({m.sources.length}):</strong>
                      {m.sources.map((src, idx) => (
                        <div key={idx} className="source-item">
                          <div>
                            <strong>
                              [{idx + 1}] {src.document}
                            </strong>{" "}
                            — Pág. {src.page} (Similitud:{" "}
                            {Number(src.score).toFixed(3)})
                          </div>
                          <div style={{ color: "#475569", marginTop: 4 }}>
                            {src.snippet}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
              </div>
            ))
          )}

          {sending && (
            <div className="message-card message-assistant thinking-message" role="status" aria-live="polite">
              <DataTutorMascot compact />
              <div className="thinking-copy">
                <strong>Pensando<span className="thinking-dots" aria-hidden="true">...</span></strong>
                <span>DataTutor está consultando su memoria documental</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="chat-form" onSubmit={handleSendQuestion}>
          <input
            type="text"
            className="chat-input"
            aria-label="Pregunta para DataTutor"
            placeholder="Escribe una pregunta sobre ingeniería de datos, ciencia de datos o bases de datos..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={sending || loadingMessages}
            maxLength={2000}
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={sending || loadingMessages || question.trim().length < 2}
            aria-label="Enviar pregunta"
          >
            {sending ? "Consultando..." : "Enviar"}
          </button>
        </form>
      </main>
    </div>
  );
}