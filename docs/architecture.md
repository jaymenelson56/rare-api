# Rare — System Architecture

## Overview

Rare is a two-tier blogging platform consisting of a React single-page application (SPA) frontend and a Django REST API backend backed by PostgreSQL. All client-server communication happens over HTTP/REST with token-based authentication.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Browser (User)                             │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    rare-client  (React SPA)                   │  │
│  │                    localhost:3000                             │  │
│  │                                                               │  │
│  │   ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐  │  │
│  │   │  React Router│   │  Components  │   │  Manager Layer  │  │  │
│  │   │  (Navigation)│──▶│  (UI/Views)  │──▶│  (API Clients)  │  │  │
│  │   └──────────────┘   └──────────────┘   └────────┬────────┘  │  │
│  │                                                   │           │  │
│  │   Auth token stored in localStorage               │ fetch()   │  │
│  └───────────────────────────────────────────────────┼───────────┘  │
└─────────────────────────────────────────────────────-┼──────────────┘
                                                        │
                          HTTP/REST   │  Authorization: Token <token>
                          JSON bodies │  localhost:8000
                                      │
┌─────────────────────────────────────┼──────────────────────────────┐
│                    rare-api  (Django + DRF)          │             │
│                    localhost:8000                                   │
│                                                                     │
│  ┌──────────────────────────────────▼──────────────────────────┐   │
│  │                      URL Router  (urls.py)                  │   │
│  └──────────────┬──────────────────────────────────────────────┘   │
│                 │ dispatches to                                     │
│    ┌────────────▼──────────────────────────────────────────────┐   │
│    │                      View Layer  (DRF ViewSets)           │   │
│    │                                                           │   │
│    │  PostView  CategoryView  TagView  CommentView             │   │
│    │  ProfileView  ReactionView  AuthView  DemotionView        │   │
│    └────────────┬──────────────────────────────────────────────┘   │
│                 │ reads / writes via ORM                           │
│    ┌────────────▼──────────────────────────────────────────────┐   │
│    │                      Model Layer  (Django ORM)            │   │
│    │                                                           │   │
│    │  RareUser  Post  Category  Tag  PostTag                   │   │
│    │  Comment  Subscription  Reaction  PostReaction            │   │
│    │  DemotionQueue                                            │   │
│    └────────────┬──────────────────────────────────────────────┘   │
│                 │ SQL (psycopg2)                                   │
└─────────────────┼───────────────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────────────┐
│                  PostgreSQL 16  (Docker)                            │
│                  localhost:5432  •  database: rare                  │
│                  volume: rare_db_data                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Major Components

### 1. rare-client — React SPA

**Tech:** React 18, React Router v6, Bulma CSS, native `fetch`

The frontend is a single-page application served by the Create React App dev server on `localhost:3000`. It has no server-side rendering; all data is fetched from the API at runtime.

| Sub-component | Responsibility |
|---|---|
| `Rare.js` | Root component; manages auth state, guards routes |
| `ApplicationViews.js` | Declares all client-side routes via React Router |
| `NavBar.js` | Top navigation; shows admin vs. regular user links |
| Manager modules (`PostManager`, `AuthManager`, …) | Thin wrappers around `fetch` that attach the auth token and target `http://localhost:8000` |
| `localStorage` | Persists the auth token between page loads |

**Authorization levels enforced client-side:**
- Public: `/login`, `/register`
- Authenticated: all content routes
- Admin-only: tag/category management, post approval, user demotion queue

---

### 2. rare-api — Django REST API

**Tech:** Python 3, Django 4.2, Django REST Framework 3.15, django-cors-headers

The backend is a monolithic Django application that exposes a REST API on `localhost:8000`. All endpoints return JSON. CORS is configured to allow requests from `localhost:3000` only.

**Authentication:** DRF Token Authentication — the client sends `Authorization: Token <token>` on every request. Tokens are issued at login/register and stored in the `authtoken_token` table.

#### Key endpoint groups

| Prefix | Description |
|---|---|
| `POST /login`, `POST /register`, `GET /me` | Auth — issue and validate tokens |
| `GET/POST /posts`, `/posts/<id>` | Post CRUD; includes approve/unapprove for admins |
| `GET /myposts`, `GET /subscribedposts`, `GET /unapprovedposts` | Filtered post lists |
| `GET/POST /categories`, `/categories/<id>` | Category management (write: admin only) |
| `GET/POST /tags`, `/tags/<id>` | Tag management (write: admin only) |
| `GET/POST /posts/<id>/comments`, `/comments/<id>` | Comments on a post |
| `GET /profiles/<id>`, `PUT /profiles/<id>/image` | User profiles |
| `POST /profiles/<id>/subscribe`, `/unsubscribe` | Follow/unfollow an author |
| `GET/POST /posts/<id>/reactions` | Emoji reactions |
| `GET /demotionqueue`, `DELETE /demotionqueue/<id>` | Two-admin approval workflow |

---

### 3. PostgreSQL 16

**Tech:** PostgreSQL 16 in Docker Compose; data persisted in named volume `rare_db_data`

The single database for the entire platform. Django's ORM (via `psycopg2`) manages schema migrations.

#### Core tables / models

| Model | Purpose |
|---|---|
| `RareUser` | Extends Django's `AbstractUser`; adds `bio`, `profile_image_url` |
| `Post` | Blog post; FK to `RareUser` (author) and `Category`; `approved` flag for moderation |
| `Category` | Flat list of post categories |
| `Tag` | Flat list of tags; linked to posts via `PostTag` join table |
| `Comment` | Comment on a post; FK to `Post` and `RareUser` |
| `Subscription` | Follow relationship between two `RareUser` records; soft-deleted via `ended_on` |
| `Reaction` | Emoji reaction type (label + image) |
| `PostReaction` | Records which user reacted to which post with which reaction |
| `DemotionQueue` | Stores pending two-admin votes for user demotion/deactivation |

---

## Communication Flow

### Typical authenticated request

```
Browser
  │
  │  1. User action triggers Manager.fetchSomething()
  │
  ├─── HTTP GET /posts  ──────────────────────────────────────────▶ Django URL Router
  │    Authorization: Token abc123                                        │
  │                                                                  PostView.list()
  │                                                                        │
  │                                                               ORM query → SQL
  │                                                                        │
  │                                                                  PostgreSQL
  │                                                                        │
  │◀── 200 OK  { posts: [...] } ──────────────────────────────────────────┘
  │
  │  2. React sets state → component re-renders
```

### Login / token issuance

```
Browser
  │
  ├─── POST /login  { username, password } ──────────────────────▶ AuthView
  │                                                                     │
  │                                                         Validate credentials
  │                                                                     │
  │◀── 200 OK  { token: "abc123", valid: true } ──────────────────────-┘
  │
  │  localStorage.setItem("auth_token", "abc123")
  │  All subsequent requests include: Authorization: Token abc123
```

### Post moderation workflow

```
Regular user creates post
  │
  ├─── POST /posts ──────────────────────────────────────────────▶ PostView
  │                                                                     │
  │                                                        Post saved, approved=False
  │
Admin reviews unapproved posts
  │
  ├─── GET /unapprovedposts ─────────────────────────────────────▶ PostView
  ├─── POST /posts/<id>/approve ─────────────────────────────────▶ PostView
  │                                                                     │
  │                                                         Post.approved set to True
  │                                                         Post is now publicly visible
```

---

## Infrastructure (Development)

```
docker-compose.yml (rare-api/)
  └── postgres:16
        ports:  5432:5432
        env:    POSTGRES_DB=rare
                POSTGRES_USER=rare_user
                POSTGRES_PASSWORD=rare_user
        volume: rare_db_data:/var/lib/postgresql/data

Django dev server:  python manage.py runserver  →  localhost:8000
React dev server:   npm start                   →  localhost:3000
Media files:        rare-api/media/             (profile images, post images)
```

---

## Key Architectural Decisions

| Decision | Rationale |
|---|---|
| Token auth over sessions | Stateless; works cleanly with a decoupled SPA |
| Monolithic Django app | Simple to reason about and deploy for this scale |
| Admin posts auto-approve | Admins are trusted; only regular-user content needs review |
| Two-admin DemotionQueue | Prevents a single admin from unilaterally deactivating users |
| Soft-delete on Subscriptions | Preserves subscription history via `ended_on` timestamp |
