# News Aggregator API and Web Interface

A FastAPI-powered news aggregator that fetches articles from Google News, stores them in a Supabase database, and provides a REST API and web interface for browsing. Includes scheduled daily updates, search, pagination, and categorization.

## Features

- **Automated News Fetching**:  
  - Fetches news from 6 countries (Nigeria, US, Canada, Russia, Israel, Germany) and 15+ topics (Technology, Sports, Politics, etc.).
  - Removes tracking parameters from URLs to avoid duplicates.
  - Retry mechanism with exponential backoff for reliability.

- **Database Storage**:  
  - Uses Supabase for storing articles with conflict resolution based on URL.
  - Upsert operation to avoid duplicates.

- **REST API**:  
  - `GET /news`: Filter articles by category and limit results.
  - `POST /news`: Add custom articles to the database.

- **Web Interface**:  
  - Homepage with pagination, search, and category filtering.
  - Article detail page with related articles.
  - Built with Jinja2 templates and Bootstrap (example).

- **Scheduled Updates**:  
  - Daily news fetch at 1 AM (configurable).
  - Uses `asyncio` for background task scheduling.

- **Additional Utilities**:  
  - Environment variable configuration via `.env`.
  - Logging and error handling.

## Technologies Used

- **Backend**: FastAPI, Uvicorn
- **Database**: Supabase
- **News Source**: GNews (Python library)
- **Templating**: Jinja2
- **Utilities**: Python-dotenv, asyncio, retry decorators

## Prerequisites

- Python 3.7+
- [Supabase](https://supabase.com/) account (free tier works)
- Pip package manager

## Setup Instructions

### 1. Clone the Repository
```bash
git clone [your-repository-url]
cd [project-directory]
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate    # Windows

pip install fastapi supabase python-dotenv gnews uvicorn jinja2 python-multipart
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:
```env
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-anon-key
GNEWS_LANGUAGE=en
GNEWS_COUNTRY=NG
GNEWS_PERIOD=7d
GNEWS_MAX_RESULTS=10
```

### 4. Database Setup
1. Create a table named `articles` in Supabase with the following columns:
   - `title` (text)
   - `url` (text, primary key)
   - `published_date` (text)
   - `description` (text)
   - `publisher` (JSONB)
   - `source` (text)
   - `category` (text)

### 5. Run the Application
```bash
uvicorn main:app --reload
```
Access the web interface at `http://localhost:8000`.

## API Documentation

### Endpoints

#### `GET /news`
- **Query Parameters**:
  - `category`: Filter by category (e.g., `technology`, `country_NG`).
  - `limit`: Number of articles to return (default: 10).
- **Response**: List of `Article` objects.

#### `POST /news`
- **Body**: `Article` model (JSON).
- **Response**: Created article.

#### Web Endpoints
- `GET /`: Homepage with search and pagination.
- `GET /article/{url}`: Article details page with related articles.

## Scheduled News Fetching

The app automatically fetches news daily at 1 AM. To modify the schedule:
1. Edit the `target_time` variable in the `schedule_news_fetch` function:
   ```python
   target_time = datetime_time(hour=1, minute=0)  # Change hour/minute
   ```

## Deployment

### Production Setup
Use Gunicorn with Uvicorn workers:
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### Docker (Example)
```Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

- **Supabase Connection Errors**:  
  Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`.

- **Missing Templates/Static Files**:  
  Ensure `templates/` and `static/` directories exist in the project root.

- **GNews Configuration**:  
  Adjust `.env` settings like `GNEWS_COUNTRY` and `GNEWS_MAX_RESULTS`.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -am 'Add some feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.
