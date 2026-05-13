export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-2xl px-4 py-3 rounded-lg ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-none'
            : 'bg-dark-700 text-gray-100 rounded-bl-none'
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
          {message.content}
        </p>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-600/50">
            <p className="text-xs font-semibold text-gray-300 mb-2">Sources:</p>
            <ul className="space-y-1">
              {message.sources.map((source, idx) => (
                <li key={idx} className="text-xs text-gray-400 hover:text-gray-300">
                  • {source}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
