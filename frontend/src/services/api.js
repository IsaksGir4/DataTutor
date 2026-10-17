import { getValidToken } from "./auth";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

function extractErrorMessage(data, status) {
  if (data?.error?.message) {
    return data.error.message;
  }
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item.msg || JSON.stringify(item))
      .join(" | ");
  }
  if (typeof data?.detail === "string") {
    return data.detail;
  }
  return `Error HTTP ${status} al comunicarse con el servidor.`;
}

async function apiRequest(path, options = {}) {
  const token = await getValidToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const hasBody = options.body !== undefined && options.body !== null;
  if (
    hasBody &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers,
    });
  } catch (networkErr) {
    const err = new Error(
      "No fue posible conectar con la API de DataTutor (127.0.0.1:8000). Verifica que Uvicorn esté en ejecución."
    );
    err.status = 0;
    err.code = "network_error";
    throw err;
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const error = new Error(extractErrorMessage(data, response.status));
    error.status = response.status;
    error.code = data?.error?.code || `http_${response.status}`;
    error.requestId = data?.error?.request_id || null;
    error.conversationId = data?.error?.conversation_id || null;
    throw error;
  }

  return data;
}

export const api = {
  getMe: () => apiRequest("/me"),
  listConversations: () => apiRequest("/conversations"),
  getConversationMessages: (convId) =>
    apiRequest(`/conversations/${convId}/messages`),
  deleteConversation: (convId) =>
    apiRequest(`/conversations/${convId}`, { method: "DELETE" }),
  sendMessage: (question, conversationId) =>
    apiRequest("/chat", {
      method: "POST",
      body: JSON.stringify({
        question,
        conversation_id: conversationId || null,
      }),
    }),
  listDocuments: () => apiRequest("/documents"),
  getDocument: (docId) => apiRequest(`/documents/${docId}`),
  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest("/documents", {
      method: "POST",
      body: formData,
    });
  },
  deleteDocument: (docId) =>
    apiRequest(`/documents/${docId}`, { method: "DELETE" }),
};