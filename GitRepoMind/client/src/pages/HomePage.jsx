import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyzeRepository } from '../services/api'
import RepoForm from '../components/RepoForm'
import LoadingScreen from '../components/LoadingScreen'

export default function HomePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleAnalyze = async (repoUrl, branch) => {
    setLoading(true)
    setError(null)
    
    try {
      const result = await analyzeRepository(repoUrl, branch)
      
      // Save to localStorage
      const repos = JSON.parse(localStorage.getItem('repos') || '[]')
      const newRepo = {
        id: result.repo_id || Date.now().toString(),
        name: result.repo_name || repoUrl.split('/').pop(),
        url: repoUrl,
        branch: branch,
        timestamp: new Date().toISOString()
      }
      
      repos.push(newRepo)
      localStorage.setItem('repos', JSON.stringify(repos))
      
      // Redirect to chat
      navigate(`/chat/${newRepo.id}`)
    } catch (err) {
      const errorMsg = err.response?.data?.message || err.response?.data?.error || 'Failed to analyze repository. Please check the URL and try again.'
      const errorHint = err.response?.data?.hint ? ` (${err.response?.data?.hint})` : ''
      setError(errorMsg + errorHint)
      console.error('Analysis error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <LoadingScreen message="Analyzing repository..." />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-900 via-dark-800 to-dark-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400 mb-4">
            GitRepoMind
          </h1>
          <p className="text-xl text-gray-300">
            Chat with your GitHub repositories using AI
          </p>
          <p className="text-sm text-gray-400 mt-2">
            Analyze any public repository and ask intelligent questions about its code
          </p>
        </div>

        {/* Form Card */}
        <div className="glass-effect rounded-2xl p-8 shadow-2xl">
          <RepoForm onSubmit={handleAnalyze} loading={loading} />
          
          {error && (
            <div className="mt-6 p-4 bg-red-900/20 border border-red-700/50 rounded-lg text-red-300 text-sm fade-in">
              <p className="font-semibold">Error</p>
              <p>{error}</p>
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="mt-12 text-center text-gray-400 text-sm">
          <p>Example: https://github.com/username/repository</p>
          <p className="mt-2">Supported branches: main, master, develop</p>
        </div>
      </div>
    </div>
  )
}
