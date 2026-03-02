# NexusAPI

NexusAPI is a multi-tenant, credit-gated backend API built with FastAPI. It is designed to ensure that multiple organizations can use the system securely without data mixing.

## Features
- **Multi-Tenancy**: Securely partitions data across multiple organizations.
- **Credit-Gated Access**: Monitors and strictly controls API usage based on assigned credits.
- **Authentication**: Integrates with Google OAuth and utilizes JWT for secure session management.
- **Asynchronous Processing**: Uses Redis and ARQ for handling background tasks and summarization.
- **Database**: Fully asynchronous PostgreSQL integration using `asyncpg` and `SQLAlchemy`.

## Tech Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL (SQLAlchemy + asyncpg)
- **Migrations**: Alembic
- **Background Tasks**: Redis + ARQ
- **Authentication**: JWT, Google OAuth

## Local Development Setup

### 1. Prerequisites
- Python 3.10+
- PostgreSQL
- Redis

### 2. Installation
Clone the repository and install the dependencies:
```bash
python -m venv venv
.\venv\Scripts\activate   # On Windows
# source venv/bin/activate # On Unix/MacOS
pip install -r requirements.txt
```

### 3. Environment Variables
Copy the `.env.example` file to `.env` and fill in your configuration:
```bash
copy .env.example .env
```

### 4. Database Migrations
Run Alembic migrations to set up your database schema:
```bash
alembic upgrade head
```

### 5. Running the Application
Start the development server:
```bash
uvicorn src.main:app --reload
```
The API will be available at `http://localhost:8000`. You can access the interactive API documentation at `http://localhost:8000/docs`.