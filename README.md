# Mercer HR - Coding Assessment Platform

A production-grade, HackerRank-like coding assessment platform for conducting technical interviews and coding tests.

## Features

### Admin Features
- Secure login with JWT authentication
- Manage candidates (add, edit, delete, CSV import)
- Create and manage coding questions with test cases
- Create assessments with time limits and question weights
- Real-time proctoring monitoring
- Comprehensive results dashboard with leaderboards
- Export results to CSV/Excel
- Google Drive backup integration

### Candidate Features
- Simple login with assessment links
- HackerRank-style coding interface
- Multi-language support (Python, C, C++, Java)
- Real-time code execution with Monaco editor
- Auto-save functionality
- Timer and progress tracking

### Technical Features
- Sandboxed code execution with resource limits
- Background job processing with Redis + RQ
- Comprehensive proctoring (tab switches, copy-paste detection)
- Docker containerization
- Render.com deployment ready
- PostgreSQL database with migrations

## Quick Start

### Local Development with Docker

1. Clone the repository
2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
3. Start all services:
   ```bash
   docker-compose up -d
   ```
4. Run database migrations:
   ```bash
   docker-compose exec web alembic upgrade head
   ```
5. Access the application:
   - Web interface: http://localhost:8000
   - Admin login: admin@mercer.com / admin123

### Manual Setup

1. Install Python 3.11+
2. Install Redis and PostgreSQL
3. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up environment variables in `.env`
5. Run migrations:
   ```bash
   alembic upgrade head
   ```
6. Start the web server:
   ```bash
   uvicorn app.main:app --reload
   ```
7. Start the worker:
   ```bash
   python -m app.workers.worker
   ```

## Deployment

### Render.com

1. Connect your GitHub repository to Render
2. The `render.yaml` file will automatically configure all services
3. Set up environment variables in the Render dashboard
4. Deploy!

### Manual Production Deployment

1. Set up PostgreSQL and Redis instances
2. Configure environment variables
3. Run migrations
4. Deploy web server and worker processes
5. Set up reverse proxy (nginx/Apache)

## Architecture

```
mercer-hr/
├── app/
│   ├── core/          # Configuration, database, logging
│   ├── models/        # SQLAlchemy models
│   ├── routers/       # FastAPI route handlers
│   ├── services/      # Business logic and external services
│   ├── workers/       # Background job processors
│   ├── templates/     # Jinja2 HTML templates
│   └── static/        # CSS, JS, and assets
├── docker-compose.yml # Local development setup
├── render.yaml        # Production deployment config
└── requirements.txt   # Python dependencies
```

## Security Features

- JWT-based authentication
- Bcrypt password hashing
- Rate limiting on API endpoints
- Sandboxed code execution
- Comprehensive audit logging
- Proctoring event tracking

## Usage

### Creating an Assessment

1. Login as admin
2. Go to "Questions" and create coding problems with test cases
3. Go to "Assessments" and create a new assessment
4. Assign questions with weights and time limits
5. Go to "Candidates" and assign the assessment
6. Share the candidate login link

### Taking an Assessment

1. Candidates receive a unique link
2. Login with name and email
3. Solve problems in the Monaco code editor
4. Use "Run Code" to test against public test cases
5. Submit final solutions
6. View results after completion

## API Documentation

Visit `/docs` for interactive API documentation (Swagger UI).

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.