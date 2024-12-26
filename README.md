# Movie Search Application

A FastAPI-based movie search application that allows users to search and find movie information.

## Setup

1. Clone the repository:
```bash
git clone [your-repository-url]
cd [repository-name]
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create .env file and add your API key:
```
GROQ_API_KEY=your_api_key_here
```

5. Run the application:
```bash
uvicorn server:app --reload
```

## Project Structure
```
movie_search/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── movie_search.py
├── server.py
└── templates/
    └── index.html
```

## Features
- Movie search with filters
- Quality selection (720p, 1080p, 2160p)
- Rating filters
- Detailed movie information
- Download options with torrent information

## API Endpoints
- POST /api/search - Search for movies
- GET /api/movie/{movie_id} - Get detailed movie information