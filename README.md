# EduComic - Educational Comic Generation Platform

Transform classroom lessons into engaging, personalized graphic novels using AI.

## 🚀 Quick Start

### 1. Install UV (Python Package Manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Configure Environment Variables
```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys (Supabase, OpenAI, etc.)

# Frontend (optional, defaults work)
cp frontend/.env.example frontend/.env
```

### 3. Start Development Servers
```bash
./start-dev.sh
```

That's it! The script will:
- ✅ Install backend dependencies (if needed)
- ✅ Install frontend dependencies (if needed)
- ✅ Start backend on http://localhost:8000
- ✅ Start frontend on http://localhost:8080
- ✅ Show you when everything is ready

Visit http://localhost:8080 to use the app!

### Stop Servers
```bash
# Press Ctrl+C in the terminal running start-dev.sh
# Or run:
./stop-dev.sh
```

### Manual Start (Alternative)
If you prefer to run servers separately:
```bash
# Terminal 1 - Backend
cd backend/src
uv run uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

## 📚 Documentation

- **[SUPABASE_SETUP.md](SUPABASE_SETUP.md)** - Database setup instructions

## 🏗️ Project Structure

```
EduComic/
├── backend/              # FastAPI backend
│   ├── src/
│   │   ├── main.py      # API entry point
│   │   ├── database/    # Supabase integration
│   │   └── services/    # Business logic (story, avatar generation)
│   ├── pyproject.toml   # Python dependencies
│   └── uv.lock          # Locked dependencies
├── frontend/            # React + Vite frontend
│   ├── src/
│   │   ├── pages/       # Page components
│   │   ├── components/  # Reusable components
│   │   └── lib/         # API client & utilities
│   └── package.json     # Node dependencies
└── docs/                # Documentation & assets
```

## 🛠️ Tech Stack

**Backend:**
- FastAPI - Modern Python web framework
- Supabase - PostgreSQL database
- OpenAI - Story generation
- Black Forest Labs - Image generation

**Frontend:**
- React 18 - UI framework
- Vite - Build tool
- TailwindCSS - Styling
- shadcn/ui - Component library

**Development:**
- UV - Python package manager
- TypeScript - Type safety
- ESLint - Code linting

## 🧪 Testing

### Test Backend API
```bash
# Health check
curl http://localhost:8000/health

# Generate story options
curl -X POST "http://localhost:8000/story/generate-options?classroom_id=YOUR_ID&lesson_prompt=Newton's%20Laws"
```

## 👥 Team Collaboration

### Pulling Changes
```bash
git pull
cd backend && uv sync
cd ../frontend && npm install
```

### Adding Dependencies

**Backend:**
```bash
cd backend
uv add package-name
git add pyproject.toml uv.lock
```

**Frontend:**
```bash
cd frontend
npm install package-name
git add package.json package-lock.json
```

## 🔑 Environment Variables

### Backend (.env)
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_key
BFL_API_KEY=your_black_forest_labs_key
ENVIRONMENT=development
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000
```

## 📖 Features

- **Classroom Management** - Create and manage classrooms with students
- **Story Generation** - AI-powered story creation based on lesson content
- **Avatar Creation** - Generate student avatars using AI
- **Comic Viewer** - Read generated comics in an engaging format
- **Teacher Dashboard** - Manage multiple classrooms and stories

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test locally
4. Submit a pull request

## 📝 License

[Add your license here]

## 🆘 Need Help?

- Open an issue for bugs or questions
