# DanceHub CRM

DanceHub CRM is a web application for dance academies. Each academy can have multiple administrators. The current application supports operator-managed academy setup and administrator sign-in; academy registration is not public self-service.

## Architecture

The application runs as three Docker Compose services:

- **Frontend:** React single-page app served by Vite. It provides administrator sign-in, a signed-in home screen, and a protected operator registration page.
- **Backend:** FastAPI service that handles authentication, operator-only academy registration, and the health check. It uses SQLAlchemy and Alembic to access and migrate the database.
- **Database:** PostgreSQL stores academies, administrators, and refresh sessions. The database is persisted in the `postgres_data` Docker volume.

The frontend sends API requests to the backend at `http://localhost:8000` and uses HTTP-only cookies for authentication. On backend startup, the service waits for PostgreSQL, applies Alembic migrations, and then starts the API.

## Technologies

- React 19, TypeScript, Vite, Axios, Zustand, and TanStack Query
- Python 3.11, FastAPI, SQLAlchemy, Alembic, and Pydantic Settings
- PostgreSQL 18 Alpine
- Docker Compose

## Start the project

Run these commands from the repository root in WSL. Docker and Docker Compose must be installed.

1. Create a local environment file:

   ```sh
   cp .env.example .env
   ```

2. Set `JWT_SECRET` in `.env` to a stable, randomly generated secret of at least 32 bytes. Set `OPERATOR_SECRET` to a strong secret for operator-managed registration. Keep these values private and do not commit `.env`.

3. Build and start the application:

   ```sh
   docker compose up --build
   ```

   The services are available at:

   - Web app: <http://localhost:5173>
   - Backend API: <http://localhost:8000>
   - Interactive API documentation: <http://localhost:8000/docs>
   - Health check: <http://localhost:8000/api/health>

Use the operator registration page at <http://localhost:5173/operator/register> to create an academy and its first administrator. This page requires the configured operator secret. The administrator password must be at least 12 characters and include an uppercase letter, a digit, and one of `-`, `!`, `#`, `=`, or `?`. After registration, sign in at <http://localhost:5173>.

To stop the services, run:

```sh
docker compose down
```

The database volume is retained when stopping the services. To remove the database and all stored data as well, run `docker compose down -v`.

## Tests

Run the backend and frontend test suites from the WSL repository root:

```sh
docker compose run --build --no-deps --entrypoint python backend -m pytest -q
docker compose run --build --no-deps --entrypoint npm frontend test
```
