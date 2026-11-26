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

## WSL and Docker development

- Use the repository checkout in WSL for local development.
- Run the application, tests, builds, and dependency installation through Docker Compose from the
  WSL repository root. Do not install Python, Node.js, or project dependencies on the host.
- Start the application with `docker compose up --build`.
- Run backend tests with `docker compose run --build --no-deps --entrypoint python backend -m pytest -q`.
- Run frontend tests with `docker compose run --build --no-deps --entrypoint npm frontend test`.
- Stop the application with `docker compose down`.

## Registration scope

Academy registration is operator-only. Do not add public self-service registration or login unless
a task explicitly asks for it.
