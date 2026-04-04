import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import "./App.css";

const API_BASE_URL = "http://localhost:8000";
const SESSION_STORAGE_KEY = "multiclaw.session_id";
const DEFAULT_SESSION_ID = "default";

interface Message {
  type: "user" | "ai" | "system" | "agent";
  content: string;
  aiName?: string;
  timestamp: string;
  agentResult?: AgentStepResult;
}

interface Document {
  name: string;
  display_name: string;
  uri: string;
  mime_type: string;
  upload_time: number;
}

interface VoteInfo {
  ai_name: string;
  vote: "APPROVE" | "REJECT";
  reason: string;
}

interface AgentStepResult {
  step: number;
  tool: string;
  description: string;
  vote: {
    approved: boolean;
    approve_count: number;
    reject_count: number;
    total_voters: number;
    votes: VoteInfo[];
    summary: string;
  };
  result: Record<string, unknown>;
}

interface AgentResult {
  session_id?: string;
  plan: unknown;
  steps: AgentStepResult[];
  ai_responses: Record<string, string>;
  approved: boolean;
  summary: string;
  pipeline?: Record<string, string>;
}

interface HistoryResponse {
  success: boolean;
  session_id: string;
  history: Array<{
    type: "user" | "ai" | "system" | "agent";
    message: string;
    ai_name?: string;
    timestamp: string;
  }>;
}

function toSessionId(value: string): string {
  const normalized = value.trim().replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^[._-]+|[._-]+$/g, "");
  return normalized || DEFAULT_SESSION_ID;
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleTimeString("ko-KR");
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState("");
  const [showDocuments, setShowDocuments] = useState(false);
  const [showMemory, setShowMemory] = useState(false);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [memoryContent, setMemoryContent] = useState("");
  const [agentMode, setAgentMode] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    const saved = window.localStorage.getItem(SESSION_STORAGE_KEY);
    return toSessionId(saved || DEFAULT_SESSION_ID);
  });
  const [sessionInput, setSessionInput] = useState(sessionId);
  const [voteResults, setVoteResults] = useState<Record<string, VoteInfo | null>>({
    GPT: null,
    Claude: null,
    Gemini: null,
  });
  const [agentExecution, setAgentExecution] = useState<{
    status: "idle" | "planning" | "voting" | "executing" | "done";
    output: string;
  }>({ status: "idle", output: "" });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const requestAbortRef = useRef<AbortController | null>(null);

  const latestResponses = useMemo(() => {
    const map: Record<string, Message | undefined> = {};
    for (const aiName of ["GPT", "Claude", "Gemini"]) {
      map[aiName] = [...messages]
        .reverse()
        .find((message) => message.type === "ai" && message.aiName === aiName);
    }
    return map;
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    setSessionInput(sessionId);
  }, [sessionId]);

  useEffect(() => {
    void loadHistory(sessionId);
  }, [sessionId]);

  const getAIImage = (aiName: string) => {
    const imageMap: Record<string, string> = {
      GPT: "/app/ai_image/ChatGPT_Image.png",
      Claude: "/app/ai_image/Claude_Image.png",
      Gemini: "/app/ai_image/Gemini_Image.png",
    };
    return imageMap[aiName] || "";
  };

  const getAIColor = (aiName: string) => {
    const colorMap: Record<string, string> = {
      GPT: "#10a37f",
      Claude: "#cc785c",
      Gemini: "#4285f4",
    };
    return colorMap[aiName] || "#666";
  };

  const appendMessage = (message: Message) => {
    setMessages((current) => [...current, message]);
  };

  const loadHistory = async (targetSessionId: string) => {
    try {
      const response = await axios.get<HistoryResponse>(`${API_BASE_URL}/api/history`, {
        params: { session_id: targetSessionId },
      });
      const restoredMessages: Message[] = (response.data.history || []).map((entry) => ({
        type: entry.type,
        content: entry.message,
        aiName: entry.ai_name,
        timestamp: entry.timestamp,
      }));
      setMessages(restoredMessages);
      setVoteResults({ GPT: null, Claude: null, Gemini: null });
      setAgentExecution({ status: "idle", output: "" });
      setAgentMode(false);
    } catch (error) {
      console.error("Load history error:", error);
      setMessages([]);
    }
  };

  const handleApplySession = async () => {
    const nextSessionId = toSessionId(sessionInput);
    if (nextSessionId === sessionId) {
      await loadHistory(nextSessionId);
      return;
    }
    setSessionId(nextSessionId);
  };

  const handleResetSession = async () => {
    const nextSessionId = DEFAULT_SESSION_ID;
    setSessionInput(nextSessionId);
    if (nextSessionId === sessionId) {
      await loadHistory(nextSessionId);
      return;
    }
    setSessionId(nextSessionId);
  };

  const handleSend = async () => {
    if (!input.trim() && !selectedFile) {
      return;
    }

    const userMessage = input.trim();
    const fileToUpload = selectedFile;

    setInput("");
    setSelectedFile(null);
    setLoading(true);

    if (fileToUpload) {
      try {
        setUploadProgress("Uploading file...");
        const formData = new FormData();
        formData.append("file", fileToUpload);

        await axios.post(`${API_BASE_URL}/api/upload`, formData, {
          params: { session_id: sessionId },
          headers: { "Content-Type": "multipart/form-data" },
        });

        appendMessage({
          type: "system",
          content: `File uploaded: ${fileToUpload.name}`,
          timestamp: new Date().toISOString(),
        });
        setUploadProgress("");
      } catch (error: unknown) {
        console.error("Upload error:", error);
        const detail = axios.isAxiosError(error)
          ? error.response?.data?.detail || error.message
          : "Unknown error";
        appendMessage({
          type: "system",
          content: `File upload failed: ${detail}`,
          timestamp: new Date().toISOString(),
        });
        setUploadProgress("");
        setLoading(false);
        return;
      }
    }

    if (!userMessage) {
      setLoading(false);
      return;
    }

    appendMessage({
      type: "user",
      content: userMessage,
      timestamp: new Date().toISOString(),
    });

    await handleConversation(userMessage);

    setLoading(false);
  };

  const handleCancel = async () => {
    requestAbortRef.current?.abort();
    requestAbortRef.current = null;

    try {
      await axios.post(`${API_BASE_URL}/api/chat/cancel`, null, {
        params: { session_id: sessionId },
      });
    } catch (error) {
      console.error("Cancel request error:", error);
    }

    setLoading(false);
    setAgentExecution({
      status: "done",
      output: "Execution stopped by user.",
    });
    appendMessage({
      type: "system",
      content: `Conversation cancelled in session "${sessionId}".`,
      timestamp: new Date().toISOString(),
    });
  };

  const handleConversation = async (userMessage: string) => {
    try {
      setAgentMode(true);
      setVoteResults({ GPT: null, Claude: null, Gemini: null });
      setAgentExecution({ status: "planning", output: "" });

      appendMessage({
        type: "system",
        content: `Agent orchestration active in session "${sessionId}".`,
        timestamp: new Date().toISOString(),
      });

      const abortController = new AbortController();
      requestAbortRef.current = abortController;
      const response = await axios.post(
        `${API_BASE_URL}/api/chat`,
        {
          message: userMessage,
          include_context: true,
          session_id: sessionId,
        },
        {
          signal: abortController.signal,
        }
      );
      requestAbortRef.current = null;

      const agentResult: AgentResult = response.data.agent_result;
      const pipeline = agentResult.pipeline || {};
      if (pipeline.execute === "completed") {
        setAgentExecution((current) => ({ ...current, status: "executing" }));
      } else {
        setAgentExecution({ status: "voting", output: "" });
      }

      const nextVotes: Record<string, VoteInfo | null> = {
        GPT: null,
        Claude: null,
        Gemini: null,
      };

      (agentResult.steps || []).forEach((step) => {
        (step.vote?.votes || []).forEach((vote) => {
          nextVotes[vote.ai_name] = vote;
        });
      });
      setVoteResults(nextVotes);

      if (agentResult.steps && agentResult.steps.length > 0) {
        setAgentExecution({
          status: "done",
          output: agentResult.steps
            .map((step) => {
              const lines = [
                `[Step ${step.step}] ${step.description}`,
                `Vote: ${step.vote.summary}`,
              ];
              if (step.result?.stdout) {
                lines.push(`Output:\n${String(step.result.stdout)}`);
              }
              if (step.result?.content) {
                lines.push(`Content:\n${String(step.result.content).slice(0, 500)}`);
              }
              if (Array.isArray(step.result?.entries)) {
                lines.push(
                  `Files:\n${step.result.entries
                    .map((entry: { type: string; name: string }) =>
                      `  ${entry.type === "directory" ? "[dir]" : "[file]"} ${entry.name}`
                    )
                    .join("\n")}`
                );
              }
              if (step.result?.error) {
                lines.push(`Error: ${String(step.result.error)}`);
              }
              return lines.join("\n");
            })
            .join("\n---\n"),
        });

        agentResult.steps.forEach((step) => {
          appendMessage({
            type: "agent",
            content: `**${step.description}**\n\n${step.vote.summary}`,
            timestamp: new Date().toISOString(),
            agentResult: step,
          });
        });
      } else {
        setAgentExecution({ status: "done", output: "No tool steps were needed." });
      }

      Object.entries(agentResult.ai_responses || {}).forEach(([aiName, content]) => {
        appendMessage({
          type: "ai",
          content,
          aiName,
          timestamp: new Date().toISOString(),
        });
      });
    } catch (error: unknown) {
      requestAbortRef.current = null;
      console.error("Conversation error:", error);
      if (
        axios.isCancel(error) ||
        (error instanceof Error && error.name === "CanceledError")
      ) {
        return;
      }
      setAgentExecution({ status: "idle", output: "" });
      const detail = axios.isAxiosError(error)
        ? error.response?.data?.detail || error.message
        : "Unknown error";
      appendMessage({
        type: "system",
        content: `Conversation failed: ${detail}`,
        timestamp: new Date().toISOString(),
      });
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm(`Clear chat history for session "${sessionId}"?`)) {
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/api/history`, {
        params: { session_id: sessionId },
      });
      setMessages([]);
      setAgentMode(false);
      setVoteResults({ GPT: null, Claude: null, Gemini: null });
      setAgentExecution({ status: "idle", output: "" });
    } catch (error) {
      console.error("Clear history error:", error);
    }
  };

  const loadDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents`);
      if (response.data.success) {
        setDocuments(response.data.documents);
      }
    } catch (error) {
      console.error("Load documents error:", error);
    }
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!window.confirm("Delete this uploaded document?")) {
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}`);
      appendMessage({
        type: "system",
        content: "Document deleted.",
        timestamp: new Date().toISOString(),
      });
      await loadDocuments();
    } catch (error: unknown) {
      console.error("Delete document error:", error);
      const detail = axios.isAxiosError(error)
        ? error.response?.data?.error || error.message
        : "Unknown error";
      window.alert(`Delete failed: ${detail}`);
    }
  };

  const handleClearAllDocuments = async () => {
    if (!window.confirm("Delete all uploaded documents? This cannot be undone.")) {
      return;
    }

    try {
      const response = await axios.delete(`${API_BASE_URL}/api/documents`);
      appendMessage({
        type: "system",
        content: response.data.message || "All documents deleted.",
        timestamp: new Date().toISOString(),
      });
      await loadDocuments();
    } catch (error: unknown) {
      console.error("Clear all documents error:", error);
      const detail = axios.isAxiosError(error)
        ? error.response?.data?.error || error.message
        : "Unknown error";
      window.alert(`Delete failed: ${detail}`);
    }
  };

  const handleOpenDocuments = async () => {
    await loadDocuments();
    setShowDocuments(true);
  };

  const handleOpenMemory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/memory`, {
        params: { session_id: sessionId },
      });
      setMemoryContent(response.data.content || "Memory is empty.");
      setShowMemory(true);
    } catch (error) {
      console.error("Load memory error:", error);
      setMemoryContent("Could not load memory.");
      setShowMemory(true);
    }
  };

  const handleClearMemory = async () => {
    if (!window.confirm(`Clear memory for session "${sessionId}"?`)) {
      return;
    }

    try {
      await axios.delete(`${API_BASE_URL}/api/memory`, {
        params: { session_id: sessionId },
      });
      setMemoryContent("Memory cleared.");
    } catch (error) {
      console.error("Clear memory error:", error);
    }
  };

  return (
    <div className="app-container">
      <header className="header multiclaw-header">
        <div className="header-title-group">
          <h1>MultiClaw</h1>
          <div className="header-subtitle">Multi-AI voting agent</div>
        </div>
        <div className="session-toolbar">
          <label className="session-label" htmlFor="session-id-input">
            Session
          </label>
          <input
            id="session-id-input"
            value={sessionInput}
            onChange={(event) => setSessionInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !loading) {
                void handleApplySession();
              }
            }}
            className="session-input"
            placeholder="default"
            disabled={loading}
          />
          <button onClick={() => void handleApplySession()} className="session-btn" disabled={loading}>
            Switch
          </button>
          <button onClick={() => void handleResetSession()} className="session-btn session-btn-secondary" disabled={loading}>
            Reset
          </button>
          <span className="session-active">Active: {sessionId}</span>
        </div>
        <div className="header-buttons">
          <button onClick={() => void handleOpenMemory()} className="memory-btn">
            Memory
          </button>
          <button onClick={() => void handleOpenDocuments()} className="docs-btn">
            Documents
          </button>
          <button onClick={() => void handleClearHistory()} className="clear-btn">
            Clear Chat
          </button>
        </div>
      </header>

      {showDocuments && (
        <div className="modal-overlay" onClick={() => setShowDocuments(false)}>
          <div className="modal-content" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h2>Uploaded Documents</h2>
              <button onClick={() => setShowDocuments(false)} className="modal-close">
                X
              </button>
            </div>
            <div className="modal-body">
              {documents.length === 0 ? (
                <p className="no-documents">No uploaded documents yet.</p>
              ) : (
                <>
                  <div className="documents-list">
                    {documents.map((doc) => (
                      <div key={doc.name} className="document-item">
                        <div className="document-info">
                          <div className="document-name">{doc.display_name}</div>
                          <div className="document-meta">
                            {doc.mime_type} · {new Date(doc.upload_time * 1000).toLocaleString("ko-KR")}
                          </div>
                        </div>
                        <button onClick={() => void handleDeleteDocument(doc.name)} className="delete-doc-btn">
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="modal-footer">
                    <button onClick={() => void handleClearAllDocuments()} className="clear-all-btn">
                      Delete All
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {showMemory && (
        <div className="modal-overlay" onClick={() => setShowMemory(false)}>
          <div className="modal-content memory-modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h2>Session Memory</h2>
              <button onClick={() => setShowMemory(false)} className="modal-close">
                X
              </button>
            </div>
            <div className="modal-body">
              <div className="memory-session-note">Session: {sessionId}</div>
              <div className="memory-content">
                <ReactMarkdown>{memoryContent}</ReactMarkdown>
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={() => void handleClearMemory()} className="clear-all-btn">
                Clear Memory
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="main-content">
        <div className="ai-panels">
          {["GPT", "Claude", "Gemini"].map((aiName) => {
            const latestResponse = latestResponses[aiName];
            const vote = voteResults[aiName];
            return (
              <div key={aiName} className="ai-panel" style={{ borderColor: getAIColor(aiName) }}>
                <div className="ai-header">
                  <img src={getAIImage(aiName)} alt={aiName} className="ai-avatar" />
                  <div className="ai-name-tag">
                    <h3 style={{ color: getAIColor(aiName) }}>{aiName}</h3>
                  </div>
                  {vote && (
                    <div className={`vote-badge ${vote.vote === "APPROVE" ? "vote-approve" : "vote-reject"}`}>
                      {vote.vote}
                    </div>
                  )}
                  {agentMode && !vote && loading && <div className="vote-badge vote-pending">Voting...</div>}
                </div>
                <div className="ai-response">
                  {vote && (
                    <div className={`vote-reason ${vote.vote === "APPROVE" ? "vote-reason-approve" : "vote-reason-reject"}`}>
                      <strong>Reason:</strong> {vote.reason}
                    </div>
                  )}
                  {latestResponse ? (
                    <ReactMarkdown>{latestResponse.content}</ReactMarkdown>
                  ) : (
                    <p className="placeholder">Waiting for response...</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="right-panel">
          {agentMode && agentExecution.status !== "idle" && (
            <div className="agent-result-panel">
              <h3>Agent Execution</h3>
              <div className="agent-status">
                {agentExecution.status === "planning" && "Creating plan..."}
                {agentExecution.status === "voting" && "Collecting votes..."}
                {agentExecution.status === "executing" && "Executing tools..."}
                {agentExecution.status === "done" && "Execution completed"}
              </div>
              {agentExecution.output && <pre className="agent-output">{agentExecution.output}</pre>}
            </div>
          )}

          <div className="chat-history">
            <div className="chat-history-header">
              <h3>Chat History</h3>
              <span className="chat-history-session">{sessionId}</span>
            </div>
            <div className="history-messages">
              {messages.map((msg, idx) => (
                <div key={`${msg.timestamp}-${idx}`} className={`history-message ${msg.type}`}>
                  {msg.type === "user" && (
                    <div className="user-message">
                      <div className="message-header">
                        <span className="sender-badge user-badge">You</span>
                        <span className="timestamp">{formatTimestamp(msg.timestamp)}</span>
                      </div>
                      <div className="message-content">{msg.content}</div>
                    </div>
                  )}
                  {msg.type === "ai" && (
                    <div className="ai-message" style={{ borderLeftColor: getAIColor(msg.aiName || "") }}>
                      <div className="message-header">
                        <span className="sender-badge ai-badge" style={{ backgroundColor: getAIColor(msg.aiName || "") }}>
                          {msg.aiName}
                        </span>
                        <span className="timestamp">{formatTimestamp(msg.timestamp)}</span>
                      </div>
                      <div className="message-content">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                  {msg.type === "system" && (
                    <div className="system-message">
                      <div className="message-header">
                        <span className="sender-badge system-badge">System</span>
                        <span className="timestamp">{formatTimestamp(msg.timestamp)}</span>
                      </div>
                      <div className="message-content">{msg.content}</div>
                    </div>
                  )}
                  {msg.type === "agent" && (
                    <div className="agent-message">
                      <div className="message-header">
                        <span className="sender-badge agent-badge">Agent</span>
                        <span className="timestamp">{formatTimestamp(msg.timestamp)}</span>
                      </div>
                      <div className="message-content">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>
      </div>

      <div className="input-area">
        <div className="input-container">
          <input
            type="file"
            ref={fileInputRef}
            onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
            accept=".pdf,.docx,.txt,.json,.png,.jpg,.jpeg"
            style={{ display: "none" }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="file-btn"
            title="Select a file to upload before sending"
            disabled={loading}
          >
            File
          </button>

          {selectedFile && (
            <span className="file-preview">
              {selectedFile.name}
              <button onClick={() => setSelectedFile(null)} className="file-remove">
                X
              </button>
            </span>
          )}

          {uploadProgress && <span className="upload-progress">{uploadProgress}</span>}

          <input
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !loading) {
                void handleSend();
              }
            }}
            placeholder='Ask anything. MultiClaw will decide whether to read files, write files, run commands, or just answer.'
            disabled={loading}
            className="message-input"
          />

          <button
            onClick={() => void handleSend()}
            disabled={loading || (!input.trim() && !selectedFile)}
            className="send-btn"
          >
            {loading ? "..." : "Send"}
          </button>
          <button
            onClick={() => void handleCancel()}
            disabled={!loading}
            className="cancel-btn"
          >
            Stop
          </button>
        </div>

        <div className="input-hint">
          Every message is agent-enabled by default. Each session keeps its own chat history, memory, votes, and audit trail.
        </div>
      </div>
    </div>
  );
}

export default App;
