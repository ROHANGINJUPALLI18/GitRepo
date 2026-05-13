# GitRepoMind Frontend - Setup Guide

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will run on `http://localhost:3000` and proxy API calls to `http://localhost:8000`.

## Environment Variables

Copy `.env.example` to `.env.local`:

```bash
cp .env.example .env.local
```

Edit `VITE_API_BASE_URL` if your backend is on a different host.

## Project Structure

```
client/
├── src/
│   ├── pages/
│   │   ├── HomePage.jsx          # Repository input & analysis
│   │   └── ChatPage.jsx          # Chat interface
│   ├── components/
│   │   ├── RepoForm.jsx          # GitHub repo input form
│   │   ├── Sidebar.jsx           # Repository history sidebar
│   │   ├── ChatWindow.jsx        # Message list display
│   │   ├── ChatInput.jsx         # Message input + send button
│   │   ├── MessageBubble.jsx     # Single message display
│   │   └── LoadingScreen.jsx     # Loading indicator
│   ├── services/
│   │   └── api.js                # Axios API client
│   ├── App.jsx                   # Main app with routing
│   ├── main.jsx                  # React entry point
│   └── index.css                 # Global styles + Tailwind
├── index.html                    # HTML entry point
├── vite.config.js               # Vite configuration
├── tailwind.config.js           # Tailwind CSS config
├── postcss.config.js            # PostCSS config
└── package.json                 # Dependencies

```

## Features Implemented

✅ **HomePage** - Repository analysis form
✅ **ChatPage** - ChatGPT-style chat interface
✅ **Sidebar** - Repository history with delete
✅ **localStorage** - Persistent chat history
✅ **API Integration** - Connected to backend RAG API
✅ **Dark Theme** - Modern dark UI
✅ **Responsive** - Mobile-friendly layout
✅ **Real-time Updates** - Auto-scroll on new messages

## Backend Integration

The frontend connects to:

- `POST /api/analyze` - Analyze GitHub repository
- `POST /api/chat` - Send chat message to RAG pipeline

Ensure the backend is running on `http://localhost:8000`.

## Development

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Tech Stack

- **React 18** - UI framework
- **Vite** - Fast build tool
- **Tailwind CSS** - Styling
- **Axios** - HTTP client
- **React Router** - Navigation
- **localStorage** - Temporary persistence

No Redux, no authentication, no complex state management - just simple, functional React.
