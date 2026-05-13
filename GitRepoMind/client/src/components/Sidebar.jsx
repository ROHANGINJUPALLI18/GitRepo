import { useEffect, useState } from 'react'

export default function Sidebar({ onSelectRepo, onDeleteRepo, currentRepoId }) {
  const [repos, setRepos] = useState([])

  useEffect(() => {
    const savedRepos = JSON.parse(localStorage.getItem('repos') || '[]')
    setRepos(savedRepos)
  }, [])

  const handleDeleteClick = (e, repoId) => {
    e.stopPropagation()
    onDeleteRepo(repoId)
    setRepos(repos.filter(r => r.id !== repoId))
  }

  return (
    <div className="flex flex-col h-full">
      {/* New Chat Button */}
      <div className="p-4 border-b border-dark-600">
        <button
          onClick={() => window.location.href = '/'}
          className="w-full px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg transition text-sm font-medium"
        >
          + New Chat
        </button>
      </div>

      {/* Repositories List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-4">
          <h3 className="text-xs uppercase text-gray-500 font-semibold mb-2">
            Repository History
          </h3>
        </div>

        {repos.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            No repositories yet
          </p>
        ) : (
          <div className="space-y-2">
            {repos.map((repo) => (
              <div
                key={repo.id}
                onClick={() => onSelectRepo(repo.id)}
                className={`p-3 rounded-lg cursor-pointer transition group ${
                  currentRepoId === repo.id
                    ? 'bg-blue-600/20 border border-blue-500/50'
                    : 'hover:bg-dark-700 border border-transparent'
                }`}
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      {repo.name}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {repo.url}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDeleteClick(e, repo.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-600/20 rounded text-red-400 transition text-xs"
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-dark-600 p-4 text-xs text-gray-500 text-center">
        <p>GitRepoMind v1.0</p>
      </div>
    </div>
  )
}
