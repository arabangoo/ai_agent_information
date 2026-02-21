import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import './App.css'

const API_BASE_URL = 'http://localhost:8000'

interface Message {
  type: 'user' | 'ai' | 'system' | 'agent'
  content: string
  aiName?: string
  timestamp: string
  fileInfo?: any
  voteResult?: VoteInfo
  agentResult?: AgentStepResult
}

interface AIResponse {
  ai_name: string
  response: string
  timestamp: string
}

interface Document {
  name: string
  display_name: string
  uri: string
  mime_type: string
  upload_time: number
}

interface VoteInfo {
  ai_name: string
  vote: 'APPROVE' | 'REJECT'
  reason: string
}

interface AgentStepResult {
  step: number
  tool: string
  description: string
  vote: {
    approved: boolean
    approve_count: number
    reject_count: number
    total_voters: number
    votes: VoteInfo[]
    summary: string
  }
  result: any
}

interface AgentResult {
  plan: any
  steps: AgentStepResult[]
  ai_responses: Record<string, string>
  approved: boolean
  summary: string
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState<string>('')
  const [showDocuments, setShowDocuments] = useState(false)
  const [showMemory, setShowMemory] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([])
  const [memoryContent, setMemoryContent] = useState<string>('')
  const [agentMode, setAgentMode] = useState(false)
  const [voteResults, setVoteResults] = useState<Record<string, VoteInfo | null>>({
    GPT: null, Claude: null, Gemini: null
  })
  const [agentExecution, setAgentExecution] = useState<{
    status: 'idle' | 'planning' | 'voting' | 'executing' | 'done'
    output: string
  }>({ status: 'idle', output: '' })

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 에이전트 명령 감지
  const isAgentCommand = (msg: string) => msg.trim().startsWith('/agent ')

  // 메시지 전송 (파일 업로드 포함)
  const handleSend = async () => {
    if (!input.trim() && !selectedFile) return

    const userMessage = input.trim()
    const fileToUpload = selectedFile

    setInput('')
    setSelectedFile(null)
    setLoading(true)

    // 파일이 있으면 먼저 업로드
    if (fileToUpload) {
      try {
        setUploadProgress('파일 업로드 중...')
        const formData = new FormData()
        formData.append('file', fileToUpload)

        await axios.post(`${API_BASE_URL}/api/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        setMessages(prev => [...prev, {
          type: 'system',
          content: `📎 파일 업로드 완료: ${fileToUpload.name}`,
          timestamp: new Date().toISOString()
        }])

        setUploadProgress('')
      } catch (error: any) {
        console.error('Upload error:', error)
        setMessages(prev => [...prev, {
          type: 'system',
          content: `❌ 파일 업로드 실패: ${error.response?.data?.detail || error.message}`,
          timestamp: new Date().toISOString()
        }])
        setUploadProgress('')
        setLoading(false)
        return
      }
    }

    if (!userMessage) {
      setLoading(false)
      return
    }

    // 사용자 메시지 추가
    const newUserMessage: Message = {
      type: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, newUserMessage])

    // 에이전트 명령 처리
    if (isAgentCommand(userMessage)) {
      await handleAgentCommand(userMessage)
    } else {
      await handleChatMessage(userMessage)
    }

    setLoading(false)
  }

  // 일반 채팅 처리
  const handleChatMessage = async (userMessage: string) => {
    try {
      setAgentMode(false)
      setVoteResults({ GPT: null, Claude: null, Gemini: null })

      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        message: userMessage,
        include_context: true
      })

      response.data.responses.forEach((aiResp: AIResponse) => {
        setMessages(prev => [...prev, {
          type: 'ai',
          content: aiResp.response,
          aiName: aiResp.ai_name,
          timestamp: aiResp.timestamp
        }])
      })

    } catch (error: any) {
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        type: 'system',
        content: `❌ 오류: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date().toISOString()
      }])
    }
  }

  // 에이전트 명령 처리
  const handleAgentCommand = async (userMessage: string) => {
    try {
      setAgentMode(true)
      setVoteResults({ GPT: null, Claude: null, Gemini: null })
      setAgentExecution({ status: 'planning', output: '' })

      // 에이전트 시작 메시지
      setMessages(prev => [...prev, {
        type: 'system',
        content: '🦀 멀티클로 에이전트 실행 중... 3개 AI가 투표 진행합니다.',
        timestamp: new Date().toISOString()
      }])

      setAgentExecution({ status: 'voting', output: '' })

      const response = await axios.post(`${API_BASE_URL}/api/agent`, {
        message: userMessage,
      })

      const agentResult: AgentResult = response.data.agent_result

      // 투표 결과 업데이트
      const newVoteResults: Record<string, VoteInfo | null> = {
        GPT: null, Claude: null, Gemini: null
      }

      if (agentResult.steps && agentResult.steps.length > 0) {
        // 모든 단계의 투표 결과를 합산
        agentResult.steps.forEach(step => {
          if (step.vote && step.vote.votes) {
            step.vote.votes.forEach(vote => {
              newVoteResults[vote.ai_name] = vote
            })
          }
        })
      }

      setVoteResults(newVoteResults)

      // 에이전트 실행 결과 표시
      if (agentResult.steps && agentResult.steps.length > 0) {
        setAgentExecution({
          status: 'done',
          output: agentResult.steps.map(step => {
            const voteEmoji = step.vote.approved ? '✅' : '❌'
            let output = `[단계 ${step.step}] ${step.description}\n`
            output += `투표: ${voteEmoji} ${step.vote.summary}\n`
            if (step.result) {
              if (step.result.stdout) output += `출력:\n${step.result.stdout}\n`
              if (step.result.content) output += `내용:\n${step.result.content.substring(0, 500)}\n`
              if (step.result.entries) output += `파일 목록:\n${step.result.entries.map((e: any) => `  ${e.type === 'directory' ? '📁' : '📄'} ${e.name}`).join('\n')}\n`
              if (step.result.error) output += `오류: ${step.result.error}\n`
            }
            return output
          }).join('\n---\n')
        })

        // 투표 결과 메시지
        agentResult.steps.forEach(step => {
          setMessages(prev => [...prev, {
            type: 'agent',
            content: `🗳️ **[${step.description}]** ${step.vote.summary}`,
            timestamp: new Date().toISOString(),
            agentResult: step
          }])
        })
      } else {
        setAgentExecution({ status: 'done', output: '도구 사용 없이 응답 생성' })
      }

      // AI 응답 추가
      Object.entries(agentResult.ai_responses || {}).forEach(([aiName, resp]) => {
        setMessages(prev => [...prev, {
          type: 'ai',
          content: resp as string,
          aiName: aiName,
          timestamp: new Date().toISOString()
        }])
      })

    } catch (error: any) {
      console.error('Agent error:', error)
      setAgentExecution({ status: 'idle', output: '' })
      setMessages(prev => [...prev, {
        type: 'system',
        content: `❌ 에이전트 오류: ${error.response?.data?.detail || error.message}`,
        timestamp: new Date().toISOString()
      }])
    }
  }

  // 히스토리 초기화
  const handleClearHistory = async () => {
    if (!confirm('대화 기록을 모두 삭제하시겠습니까?')) return

    try {
      await axios.delete(`${API_BASE_URL}/api/history`)
      setMessages([])
      setAgentMode(false)
      setVoteResults({ GPT: null, Claude: null, Gemini: null })
      setAgentExecution({ status: 'idle', output: '' })
    } catch (error) {
      console.error('Clear history error:', error)
    }
  }

  // 문서 목록 불러오기
  const loadDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents`)
      if (response.data.success) {
        setDocuments(response.data.documents)
      }
    } catch (error) {
      console.error('Load documents error:', error)
    }
  }

  // 문서 삭제
  const handleDeleteDocument = async (documentId: string) => {
    if (!confirm('이 문서를 삭제하시겠습니까?')) return

    try {
      await axios.delete(`${API_BASE_URL}/api/documents/${encodeURIComponent(documentId)}`)
      setMessages(prev => [...prev, {
        type: 'system',
        content: `🗑️ 문서 삭제 완료`,
        timestamp: new Date().toISOString()
      }])
      loadDocuments()
    } catch (error: any) {
      console.error('Delete document error:', error)
      alert(`문서 삭제 실패: ${error.response?.data?.error || error.message}`)
    }
  }

  // 모든 문서 삭제
  const handleClearAllDocuments = async () => {
    if (!confirm('모든 문서를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) return

    try {
      const response = await axios.delete(`${API_BASE_URL}/api/documents`)
      setMessages(prev => [...prev, {
        type: 'system',
        content: `🗑️ ${response.data.message}`,
        timestamp: new Date().toISOString()
      }])
      loadDocuments()
    } catch (error: any) {
      console.error('Clear all documents error:', error)
      alert(`문서 삭제 실패: ${error.response?.data?.error || error.message}`)
    }
  }

  // 문서 관리 모달 열기
  const handleOpenDocuments = () => {
    loadDocuments()
    setShowDocuments(true)
  }

  // 메모리 조회
  const handleOpenMemory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/memory`)
      setMemoryContent(response.data.content || '메모리가 비어있습니다.')
      setShowMemory(true)
    } catch (error) {
      console.error('Load memory error:', error)
      setMemoryContent('메모리를 불러올 수 없습니다.')
      setShowMemory(true)
    }
  }

  // 메모리 초기화
  const handleClearMemory = async () => {
    if (!confirm('장기 메모리를 모두 삭제하시겠습니까?')) return

    try {
      await axios.delete(`${API_BASE_URL}/api/memory`)
      setMemoryContent('메모리가 초기화되었습니다.')
    } catch (error) {
      console.error('Clear memory error:', error)
    }
  }

  // AI 이미지 매핑
  const getAIImage = (aiName: string) => {
    const imageMap: Record<string, string> = {
      'GPT': '/app/ai_image/ChatGPT_Image.png',
      'Claude': '/app/ai_image/Claude_Image.png',
      'Gemini': '/app/ai_image/Gemini_Image.png'
    }
    return imageMap[aiName] || ''
  }

  // AI 색상 매핑
  const getAIColor = (aiName: string) => {
    const colorMap: Record<string, string> = {
      'GPT': '#10a37f',
      'Claude': '#cc785c',
      'Gemini': '#4285f4'
    }
    return colorMap[aiName] || '#666'
  }

  return (
    <div className="app-container">
      {/* 헤더 */}
      <header className="header multiclaw-header">
        <h1>🦀 멀티클로 MultiClaw</h1>
        <div className="header-subtitle">AI 다수결 투표 에이전트</div>
        <div className="header-buttons">
          <button onClick={handleOpenMemory} className="memory-btn">
            🧠 메모리
          </button>
          <button onClick={handleOpenDocuments} className="docs-btn">
            📚 문서 관리
          </button>
          <button onClick={handleClearHistory} className="clear-btn">
            🗑️ 대화 초기화
          </button>
        </div>
      </header>

      {/* 문서 관리 모달 */}
      {showDocuments && (
        <div className="modal-overlay" onClick={() => setShowDocuments(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📚 업로드된 문서</h2>
              <button onClick={() => setShowDocuments(false)} className="modal-close">❌</button>
            </div>
            <div className="modal-body">
              {documents.length === 0 ? (
                <p className="no-documents">업로드된 문서가 없습니다.</p>
              ) : (
                <>
                  <div className="documents-list">
                    {documents.map((doc, idx) => (
                      <div key={idx} className="document-item">
                        <div className="document-info">
                          <div className="document-name">📄 {doc.display_name}</div>
                          <div className="document-meta">
                            {doc.mime_type} • {new Date(doc.upload_time * 1000).toLocaleString('ko-KR')}
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteDocument(doc.name)}
                          className="delete-doc-btn"
                        >
                          🗑️ 삭제
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="modal-footer">
                    <button onClick={handleClearAllDocuments} className="clear-all-btn">
                      🗑️ 모든 문서 삭제
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 메모리 모달 */}
      {showMemory && (
        <div className="modal-overlay" onClick={() => setShowMemory(false)}>
          <div className="modal-content memory-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🧠 장기 메모리</h2>
              <button onClick={() => setShowMemory(false)} className="modal-close">❌</button>
            </div>
            <div className="modal-body">
              <div className="memory-content">
                <ReactMarkdown>{memoryContent}</ReactMarkdown>
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={handleClearMemory} className="clear-all-btn">
                🗑️ 메모리 초기화
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="main-content">
        {/* 왼쪽: AI 응답 패널들 */}
        <div className="ai-panels">
          {['GPT', 'Claude', 'Gemini'].map(aiName => {
            const latestResponse = [...messages]
              .reverse()
              .find(m => m.type === 'ai' && m.aiName === aiName)

            const vote = voteResults[aiName]

            return (
              <div key={aiName} className="ai-panel" style={{ borderColor: getAIColor(aiName) }}>
                <div className="ai-header">
                  <img src={getAIImage(aiName)} alt={aiName} className="ai-avatar" />
                  <div className="ai-name-tag">
                    <h3 style={{ color: getAIColor(aiName) }}>{aiName}</h3>
                  </div>
                  {/* 투표 배지 */}
                  {vote && (
                    <div className={`vote-badge ${vote.vote === 'APPROVE' ? 'vote-approve' : 'vote-reject'}`}>
                      {vote.vote === 'APPROVE' ? '✅ 승인' : '❌ 거부'}
                    </div>
                  )}
                  {agentMode && !vote && loading && (
                    <div className="vote-badge vote-pending">
                      🗳️ 투표 중...
                    </div>
                  )}
                </div>
                <div className="ai-response">
                  {/* 투표 이유 표시 */}
                  {vote && (
                    <div className={`vote-reason ${vote.vote === 'APPROVE' ? 'vote-reason-approve' : 'vote-reason-reject'}`}>
                      <strong>투표 이유:</strong> {vote.reason}
                    </div>
                  )}
                  {latestResponse ? (
                    <ReactMarkdown>{latestResponse.content}</ReactMarkdown>
                  ) : (
                    <p className="placeholder">대기 중...</p>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* 오른쪽: 대화 히스토리 + 에이전트 결과 */}
        <div className="right-panel">
          {/* 에이전트 실행 결과 */}
          {agentMode && agentExecution.status !== 'idle' && (
            <div className="agent-result-panel">
              <h3>🦀 에이전트 실행</h3>
              <div className="agent-status">
                {agentExecution.status === 'planning' && '📋 작업 계획 생성 중...'}
                {agentExecution.status === 'voting' && '🗳️ AI 투표 진행 중...'}
                {agentExecution.status === 'executing' && '⚡ 작업 실행 중...'}
                {agentExecution.status === 'done' && '✅ 실행 완료'}
              </div>
              {agentExecution.output && (
                <pre className="agent-output">{agentExecution.output}</pre>
              )}
            </div>
          )}

          {/* 대화 히스토리 */}
          <div className="chat-history">
            <h3>💬 대화 히스토리</h3>
            <div className="history-messages">
              {messages.map((msg, idx) => (
                <div key={idx} className={`history-message ${msg.type}`}>
                  {msg.type === 'user' && (
                    <div className="user-message">
                      <div className="message-header">
                        <span className="sender-badge user-badge">👤 You</span>
                        <span className="timestamp">
                          {new Date(msg.timestamp).toLocaleTimeString('ko-KR')}
                        </span>
                      </div>
                      <div className="message-content">{msg.content}</div>
                    </div>
                  )}
                  {msg.type === 'ai' && (
                    <div className="ai-message" style={{ borderLeftColor: getAIColor(msg.aiName!) }}>
                      <div className="message-header">
                        <span className="sender-badge ai-badge" style={{ backgroundColor: getAIColor(msg.aiName!) }}>
                          🤖 {msg.aiName}
                        </span>
                        <span className="timestamp">
                          {new Date(msg.timestamp).toLocaleTimeString('ko-KR')}
                        </span>
                      </div>
                      <div className="message-content">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                  {msg.type === 'system' && (
                    <div className="system-message">
                      <div className="message-header">
                        <span className="sender-badge system-badge">⚙️ System</span>
                        <span className="timestamp">
                          {new Date(msg.timestamp).toLocaleTimeString('ko-KR')}
                        </span>
                      </div>
                      <div className="message-content">{msg.content}</div>
                    </div>
                  )}
                  {msg.type === 'agent' && (
                    <div className="agent-message">
                      <div className="message-header">
                        <span className="sender-badge agent-badge">🦀 Agent</span>
                        <span className="timestamp">
                          {new Date(msg.timestamp).toLocaleTimeString('ko-KR')}
                        </span>
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

      {/* 입력 영역 */}
      <div className="input-area">
        <div className="input-container">
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            accept=".pdf,.docx,.txt,.json,.png,.jpg,.jpeg"
            style={{ display: 'none' }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="file-btn"
            title="파일 첨부 (전송 시 업로드)"
            disabled={loading}
          >
            📎
          </button>

          {selectedFile && (
            <span className="file-preview">
              📄 {selectedFile.name}
              <button onClick={() => setSelectedFile(null)} className="file-remove">❌</button>
            </span>
          )}

          {uploadProgress && <span className="upload-progress">{uploadProgress}</span>}

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !loading && handleSend()}
            placeholder="/agent 파일 목록 보여줘  |  일반 대화도 가능합니다  |  @GPT @Claude @Gemini AI 지명"
            disabled={loading}
            className="message-input"
          />

          <button
            onClick={handleSend}
            disabled={loading || (!input.trim() && !selectedFile)}
            className="send-btn"
          >
            {loading ? '⏳' : '📤'}
          </button>
        </div>

        <div className="input-hint">
          🦀 <strong>/agent</strong> 명령으로 에이전트 실행 (3 AI 투표) | @GPT, @Claude, @Gemini로 AI 지명 | 📎 파일은 전송 시 업로드
        </div>
      </div>
    </div>
  )
}

export default App
