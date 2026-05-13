import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import ChatWindow from '../components/ChatWindow'
import ChatInput from '../components/ChatInput'
import { getChatHistory, getRepositories, sendChatMessage } from '../services/api'

const createSessionId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }

  return `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
}

const getSessionStorageKey = (repoId) => `chat_session_${repoId}`

const getHistoryStorageKey = (sessionId) => `chat_${sessionId}`

const mapHistoryMessages = (historyMessages) =>
  historyMessages.map((message, index) => ({
    id: `${message.timestamp || 'history'}-${index}`,
    role: message.role,
    content: message.content,
    sources: message.sources || [],
    timestamp: message.timestamp || new Date().toISOString(),
  }))

export default function ChatPage() {
  const { repoId } = useParams()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [repoInfo, setRepoInfo] = useState(null)
  const [error, setError] = useState(null)
  const [sessionId, setSessionId] = useState('')

  // Load repo info, session, and chat history.
  useEffect(() => {
    let isMounted = true

    const loadChatState = async () => {
      const savedRepos = JSON.parse(localStorage.getItem('repos') || '[]')
      let repo = savedRepos.find((item) => item.id === repoId)

      if (!repo) {
        try {
          const response = await getRepositories()
          const apiRepos = response.repos || []
          const matchedRepo = apiRepos.find((item) => item.repo_id === repoId)

          if (matchedRepo) {
            repo = {
              id: matchedRepo.repo_id,
              name: matchedRepo.repo_name,
              url: matchedRepo.repo_name,
              branch: 'main',
              timestamp: matchedRepo.indexed_at,
            }

            const nextRepos = [...savedRepos.filter((item) => item.id !== repoId), repo]
            localStorage.setItem('repos', JSON.stringify(nextRepos))
          }
        } catch (apiError) {
          console.error('Error loading repositories from API:', apiError)
        }
      }

      if (!repo) {
        navigate('/')
        return
      }

      if (!isMounted) {
        return
      }

      setRepoInfo(repo)

      const storageKey = getSessionStorageKey(repoId)
      const existingSessionId = localStorage.getItem(storageKey) || createSessionId()
      localStorage.setItem(storageKey, existingSessionId)
      setSessionId(existingSessionId)

      try {
        const historyResponse = await getChatHistory(existingSessionId)
        const backendMessages = mapHistoryMessages(historyResponse.messages || [])

        if (!isMounted) {
          return
        }

        if (backendMessages.length > 0) {
          setMessages(backendMessages)
          localStorage.setItem(
            getHistoryStorageKey(existingSessionId),
            JSON.stringify(backendMessages)
          )
          return
        }
      } catch (historyError) {
        console.error('Error loading chat history from API:', historyError)
      }

      const legacyHistoryKey = `chat_${repoId}`
      const savedMessages = JSON.parse(localStorage.getItem(legacyHistoryKey) || '[]')

      if (!isMounted) {
        return
      }

      setMessages(savedMessages)

      if (savedMessages.length > 0) {
        localStorage.setItem(
          getHistoryStorageKey(existingSessionId),
          JSON.stringify(savedMessages)
        )
      }
    }

    loadChatState()

    return () => {
      isMounted = false
    }
  }, [repoId, navigate])

  const handleSendMessage = async (query) => {
    if (!query.trim()) return

    const activeSessionId = sessionId || createSessionId()
    if (!sessionId) {
      const storageKey = getSessionStorageKey(repoId)
      localStorage.setItem(storageKey, activeSessionId)
      setSessionId(activeSessionId)
    }

    const userMessage = {
      id: `${Date.now()}-user`,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    }

    const optimisticMessages = [...messages, userMessage]
    setMessages(optimisticMessages)
    setLoading(true)
    setError(null)

    try {
      const response = await sendChatMessage(repoId, query, activeSessionId)
      const resolvedSessionId = response.session_id || activeSessionId

      if (resolvedSessionId !== sessionId) {
        localStorage.setItem(getSessionStorageKey(repoId), resolvedSessionId)
        setSessionId(resolvedSessionId)
      }

      try {
        const historyResponse = await getChatHistory(resolvedSessionId)
        const syncedMessages = mapHistoryMessages(historyResponse.messages || [])

        if (syncedMessages.length > 0) {
          setMessages(syncedMessages)
          localStorage.setItem(
            getHistoryStorageKey(resolvedSessionId),
            JSON.stringify(syncedMessages)
          )
          return
        }
      } catch (historyError) {
        console.error('Error syncing chat history from API:', historyError)
      }

      const aiMessage = {
        id: `${Date.now()}-assistant`,
        role: 'assistant',
        content: response.answer || 'No response generated',
        sources: response.sources || [],
        timestamp: new Date().toISOString(),
      }

      const fallbackMessages = [...optimisticMessages, aiMessage]
      setMessages(fallbackMessages)
      localStorage.setItem(
        getHistoryStorageKey(resolvedSessionId),
        JSON.stringify(fallbackMessages)
      )
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.error || 'Failed to get response. Please try again.')
      console.error('Chat error:', err)
      setMessages((currentMessages) => currentMessages.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteRepo = (idToDelete) => {
    const repos = JSON.parse(localStorage.getItem('repos') || '[]')
    const filtered = repos.filter((repo) => repo.id !== idToDelete)
    localStorage.setItem('repos', JSON.stringify(filtered))

    localStorage.removeItem(getSessionStorageKey(idToDelete))
    localStorage.removeItem(getHistoryStorageKey(idToDelete))
    localStorage.removeItem(`chat_${idToDelete}`)

    if (idToDelete === repoId) {
      navigate('/')
    }
  }

  const handleSelectRepo = (id) => {
    navigate(`/chat/${id}`)
  }

  return (
    <div className="flex h-screen bg-dark-900">
      {/* Sidebar */}
      <div className="w-1/4 bg-dark-800 border-r border-dark-600 flex flex-col">
        <Sidebar 
          onSelectRepo={handleSelectRepo}
          onDeleteRepo={handleDeleteRepo}
          currentRepoId={repoId}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        {repoInfo && (
          <div className="border-b border-dark-600 bg-dark-800 p-4">
            <h2 className="text-xl font-semibold text-white">
              {repoInfo.name}
            </h2>
            <p className="text-xs text-gray-400">
              {repoInfo.url} • Branch: {repoInfo.branch}
            </p>
            {sessionId && (
              <p className="text-[11px] text-gray-500 mt-1">
                Session: {sessionId}
              </p>
            )}
          </div>
        )}

        {/* Chat Messages */}
        <ChatWindow messages={messages} loading={loading} error={error} />

        {/* Chat Input */}
        <div className="border-t border-dark-600 bg-dark-800 p-4">
          <ChatInput onSend={handleSendMessage} disabled={loading} />
        </div>
      </div>
    </div>
  )
}
