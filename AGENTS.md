# DanceHub CRM agent context

## Product

DanceHub CRM is a dance academy CRM. An academy can have multiple individual administrators.
For now, protected account creation is operated manually by the product operator. Registering an
academy creates the academy and its first administrator together.

Academy attributes:

- UUID v7 id
- Name unique case-insensitively
- Unique phone

Administrator attributes:

- Unique email
- Name
- Password of at least 12 characters with an uppercase letter, a digit, and one of `-`, `!`, `#`, `=`, or `?`

Sign-in uses email and password.

## Technology stack

- Frontend: React, TypeScript, Axios, Zustand, TanStack Query
- Backend: FastAPI
- Database: PostgreSQL
- Containers: Docker Compose with PostgreSQL 18 Alpine, Python 3.11, and Node 24
- Backend startup waits for database readiness and runs migrations/schema updates before serving

## Current iteration

The current implementation is intentionally minimal: the backend exposes a string response endpoint
and the frontend displays it. Do not implement registration or login unless a task explicitly asks
for it.
