import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
})

export const analyzeRepository = async (repoUrl, branch = 'main') => {
  try {
    const response = await api.post('/api/analyze-repo', {
      repo_url: repoUrl,
      branch: branch
    })
    return response.data
  } catch (error) {
    console.error('Error analyzing repository:', error)
    throw error
  }
}

export const sendChatMessage = async (repoId, query, sessionId = 'default') => {
  try {
    const response = await api.post('/api/chat', {
      repo_id: repoId,
      query: query,
      session_id: sessionId
    })
    return response.data
  } catch (error) {
    console.error('Error sending chat message:', error)
    throw error
  }
}

export const getRepositories = async () => {
  try {
    const response = await api.get('/api/repos')
    return response.data
  } catch (error) {
    console.error('Error fetching repositories:', error)
    throw error
  }
}

export const getRepositoryStats = async (repoId) => {
  try {
    const response = await api.get(`/api/repos/${repoId}/stats`)
    return response.data
  } catch (error) {
    console.error('Error fetching repository stats:', error)
    throw error
  }
}

export const deleteRepository = async (repoId) => {
  try {
    const response = await api.delete(`/api/repos/${repoId}`)
    return response.data
  } catch (error) {
    console.error('Error deleting repository:', error)
    throw error
  }
}

export const getChatHistory = async (sessionId) => {
  try {
    const response = await api.get(`/api/chat/history/${sessionId}`)
    return response.data
  } catch (error) {
    console.error('Error fetching chat history:', error)
    throw error
  }
}

export const clearChatHistory = async (sessionId) => {
  try {
    const response = await api.delete(`/api/chat/history/${sessionId}`)
    return response.data
  } catch (error) {
    console.error('Error clearing chat history:', error)
    throw error
  }
}

export const checkHealth = async () => {
  try {
    const response = await api.get('/api/health')
    return response.data
  } catch (error) {
    console.error('Error checking health:', error)
    throw error
  }
}

export default api
