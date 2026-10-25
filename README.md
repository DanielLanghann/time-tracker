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


