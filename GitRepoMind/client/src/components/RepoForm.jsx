import { useState } from 'react'

export default function RepoForm({ onSubmit, loading }) {
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (repoUrl.trim()) {
      onSubmit(repoUrl, branch)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          GitHub Repository URL
        </label>
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/username/repository"
          className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition"
          disabled={loading}
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Branch (optional)
        </label>
        <input
          type="text"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="main"
          className="w-full px-4 py-3 bg-dark-700 border border-dark-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition"
          disabled={loading}
        />
      </div>

      <button
        type="submit"
        disabled={loading || !repoUrl.trim()}
        className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition duration-200"
      >
        {loading ? 'Analyzing...' : 'Analyze Repository'}
      </button>
    </form>
  )
}
