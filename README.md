# time-tracker

## Architecture

- api and backend via django and postgres
- Frontend via VUE.js
- Both running in Docker Containers (don't need root priviliges)
- docker compose for local development
- Later deployed as kubernetes cluster and helm chart
- Prometheus and Grafana as monitoring stack

## Backend apps

The Django project lives in `services/api`. Domain logic is split into five apps under `apps/`. Dependencies point in one direction only:

`reports` → `tracking` → `customers` → `workspaces` → `accounts`

### `accounts`

Handles identity and authentication: who a person is and how they log in.

- **Custom user model** (`accounts.User`), set as `AUTH_USER_MODEL` from the start so it can be extended without migration issues
- **Authentication** for the Vue frontend via Django session auth with CSRF protection (login, logout, current user)
- **Profile data** that belongs to the person regardless of workspace, such as name, email and personal settings

Not part of this app: what a user is allowed to do and what they cost. Roles (owner, admin, member) and hourly rates depend on the workspace and live in `workspaces.Membership`.

### `workspaces`

The top-level container. Everything else (customers, streams, tags, time entries) belongs to exactly one workspace.

- **Workspace** with name, currency and a default hourly rate
- **Membership** connecting users to workspaces, including their role (owner, admin, member) and an optional workspace-wide hourly rate
- **Scoping**: every API request operates within one workspace, and data from other workspaces is never visible

Not part of this app: the user account itself (`accounts`) and project-specific membership (`tracking`).

### `customers`

The clients that work is done for.

- **Customer** with name and an active flag, scoped to a workspace
- Customers are archived rather than deleted, so booked time and reports stay intact

Not part of this app: the work itself. Streams reference customers, not the other way around.

### `tracking`

The core of the application: what is being worked on and how much time is spent on it.

- **Stream**: a group of work for a customer (comparable to a project), with an optional hourly rate and its own member list
- **StreamMembership**: which users can book on a stream, with an optional stream-specific hourly rate
- **Item**: an optional subdivision of a stream (comparable to a task)
- **Tag**: workspace-wide labels for a second, cross-cutting grouping
- **TimeEntry**: a booking by a user on a stream (and optionally an item), either as a running timer or with start, end and duration. The resolved hourly rate is stored on the entry when it is saved, so later rate changes don't alter past amounts.

Hourly rates are resolved from most to least specific: stream membership → stream → workspace membership → workspace default.

### `reports`

Read-only evaluation of tracked time. This app has no models of its own.

- **Summary**: totals grouped by customer, stream, user or tag over a date range
- **Detailed**: a filterable list of individual time entries, exportable as CSV
- **Weekly**: a user × day overview

All reports share the same filters (date range, users, customers, streams, tags, billable) and are calculated from `tracking` data on request.

Do from the start

Code quality and delivery

Tests with pytest-django, linting with ruff, and a CI pipeline that runs both on every push
One Docker image used everywhere, served by gunicorn in production
manage.py check --deploy passing in CI against production settings
Never edit migrations that have already been applied anywhere

Data correctness, the heart of a time tracker

USE_TZ = True, store everything in UTC, and convert to each user’s time zone only for display and for “which day does this entry belong to.” Today is a good reminder: clocks went back at 3:00 this morning, so a naive implementation would have an entry from 2:30 to 3:30 last either one hour or two.
Decimal for all money and rates, never float
created_at, updated_at and created_by on core models, and archiving instead of deleting
Workspace scoping enforced in one central place, with tests proving one workspace can’t see another’s data

API contract

Generate an OpenAPI schema with drf-spectacular and a TypeScript client for Vue from it. That keeps frontend and backend in sync without manual work.

Operations

Automated Postgres backups, plus a restore you’ve actually tested once. This data drives customer billing, so it matters more than anything else in this list.
Error tracking (Sentry, or self-hosted GlitchTip), structured logs and a /health endpoint
Dependency updates via Dependabot or Renovate

Security and privacy

HTTPS, secure cookies, rate-limited login. Later, SSO with your company’s identity provider, for example via django-allauth.
Time entries are personal data, so decide early who may see whose entries (own entries, stream members, admins)
Defer on purpose

Kubernetes, Celery and background jobs, caching, invoicing, approvals, mobile apps, and anything for the hosted version, such as signup or billing. None of these block internal use, and your architecture leaves room for all of them.

Getting to the Clockify switch
Define the MVP from real usage. Ask your colleagues what they do in Clockify daily. It’s usually timer, manual entries, clients and projects, a summary report and a CSV export.
Build a Clockify importer early. Clockify has an API, and importing customers, projects and historical entries means nobody loses their data and you can compare reports directly.
Run both in parallel for two weeks. Matching totals in both tools are your proof that it’s ready.
Then switch. Keep the Clockify export as an archive.

For the cost argument, it’s worth writing down once what Clockify actually costs you per year and comparing it against hosting plus a realistic estimate of your own maintenance time. Even if the savings turn out modest, the learning and the option for later are a perfectly good reason on their own.

## Helpful commands
### Check Database
```bash
docker exec -it time-tracker-db-1 psql -U timetracker -d timetracker
```
Inside the Database, see all tables:
```bash
\dt
```

