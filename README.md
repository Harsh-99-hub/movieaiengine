# 🎬 MovieAI — AI-Powered Movie Discovery Engine

An intelligent movie discovery engine built with **FastAPI** + **React**, powered by the TMDB API.

> Built by **Harshith**

---

## ✨ Features

- 🔍 **Smart Search** — handles typos, slang, camelCase, aliases (`tdk`, `lotr`, `johnwick`)
- 🧠 **Vibe AI** — natural language search: *"less complicated than Interstellar"*
- 🎯 **TF-IDF Recommendations** — "More like this" using NLP text similarity
- 👤 **Taste Profile** — learns your preferences from your watch history
- ✨ **For You Feed** — personalized recommendations based on what you watch
- 📊 **Stats Dashboard** — genre breakdown, vibe radar, rating charts
- ✓ **Watched List** — mark, rate, and track movies you've seen

---

## 🚀 Quick Start

### The only thing you need to change is your TMDB API key.

### Step 1 — Get a free TMDB API key
1. Go to [https://www.themoviedb.org](https://www.themoviedb.org)
2. Sign up for a free account
3. Go to **Settings → API → Request API Key**
4. Choose **Developer** → fill the form → copy your **API Key (v3 auth)**

---

### Step 2 — Add your API key

Open this file:
```
backend/services/tmdb.py
```

Find this line (line 5):
```python
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "YOUR_TMDB_API_KEY_HERE")
```

Replace `YOUR_TMDB_API_KEY_HERE` with your actual key:
```python
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "paste_your_key_here")
```

---

### Step 3 — Run the backend

Open a terminal inside the `backend/` folder:

```bash
# Create virtual environment (first time only)
python -m venv venv

# Activate it
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

Backend runs at: `http://127.0.0.1:8000`  
API docs at: `http://127.0.0.1:8000/docs`

---

### Step 4 — Run the frontend

Open a **new terminal** inside the `frontend/` folder:

```bash
# Install dependencies (first time only)
npm install

# Start the app
npm run dev
```

Frontend runs at: `http://localhost:5173`

Open that link in your browser and you're good to go! 🎉

---

## 📁 Project Structure

```
movieai/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt         # Python dependencies
│   ├── routers/
│   │   ├── search.py            # GET /api/search
│   │   ├── movies.py            # GET /api/movies/trending
│   │   ├── vibe.py              # GET /api/vibe
│   │   └── recommend.py        # POST /api/recommend/*
│   └── services/
│       ├── tmdb.py              # ← PUT YOUR API KEY HERE
│       ├── search_engine.py     # Intelligent search pipeline
│       ├── vibe_engine.py       # NLP vibe matching
│       └── recommender.py      # TF-IDF recommendation engine
│
└── frontend/
    └── src/
        ├── App.jsx              # Main React app
        ├── App.css              # Styles
        └── StatsTab.jsx         # Stats dashboard charts
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q=inception` | Smart movie search |
| GET | `/api/movies/trending` | Trending this week |
| GET | `/api/vibe?q=less complicated than Interstellar` | Vibe-based search |
| GET | `/api/recommend/similar?movie_id=550` | TF-IDF recommendations |
| POST | `/api/recommend/taste` | Build taste profile |
| POST | `/api/recommend/foryou` | Personalized feed |
| GET | `/docs` | Interactive API docs |

---

## 🤖 AI Techniques Used

| Technique | Where |
|-----------|-------|
| TF-IDF (Term Frequency-Inverse Document Frequency) | "More Like This" recommendations |
| Cosine Similarity | Vibe matching + recommendation ranking |
| NLP Intent Parsing | Natural language vibe queries |
| Multi-dimensional Attribute Vectors | Movie scoring across 6 dimensions |
| Weighted Genre Profiling | Taste profile + For You feed |

---

## ⚠️ Troubleshooting

**Search returns no results?**
→ Your API key is wrong or not set. Double check `backend/services/tmdb.py`

**CORS error in browser?**
→ Make sure the backend is running (`uvicorn main:app --reload`)

**`ModuleNotFoundError`?**
→ Make sure your venv is activated before running uvicorn

**`npm` not recognized?**
→ Install Node.js from [nodejs.org](https://nodejs.org)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python) |
| Frontend | React + Vite |
| HTTP Client | httpx (async) |
| Movie Data | TMDB API v3 |
| AI/ML | Custom NLP, TF-IDF, Cosine Similarity |
| Charts | HTML Canvas API |
