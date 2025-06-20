# Smithy

![Smithy Banner](.github/assets/banner.png)

A minimalist, backend-focused project and task management platform built for developers.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.114+-00a393.svg)](https://fastapi.tiangolo.com)
[![Linted with Ruff](https://img.shields.io/badge/linting-ruff-blue)](https://docs.astral.sh/ruff/)
[![CI](https://github.com/Anvoria/smithy-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/Anvoria/smithy-backend/actions/workflows/ci.yml)


---

## ✨ Features

- **Fast and lightweight** - Built with FastAPI and async SQLAlchemy for high performance.
- **Developer-first** - Focused on providing a solid API for building custom tools.
- **Secure** - JWT authentication for secure access.
- **Modular architecture** - Easily extendable with plugins and custom endpoints.
- **Scalable** - PostgreSQL backend with Alembic migrations for schema management.

### Core Functionality

- User management (registration, login, profile)
- Project organization (create, update, delete projects)
- Task tracking (full CRUD with status, priority, due dates)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.13+
- Docker & Docker Compose
- PostgreSQL 15+ (if not using Docker)

### Quick Start

```bash
# Clone the repo
git clone https://github.com/Anvoria/smithy-backend.git
cd smithy-backend

# Copy environment variables
cp .env.example .env

# Start using Docker
docker-compose up --build

# Alembic migrations
docker-compose exec smithy_backend alembic upgrade head
```

---

## 🧪 Testing

---

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) for details on how to get started.

---

## 📋 Roadmap

### 🧱 Foundation

- [x] Project scaffold (folder structure, FastAPI app)
- [x] Environment setup (.env, config loader)
- [x] Base Dockerfile + docker-compose
- [ ] SQLAlchemy models (User, Project, Task)
- [x] Alembic migrations
- [x] JWT authentication (access and refresh)
- [ ] Initial tests (pytest + coverage)
- [x] Basic logging + error handling

### 📡 API Layer

- [x] Auth endpoints (register, login, refresh)
- [x] User CRUD
- [ ] Project CRUD
- [ ] Task CRUD
- [ ] Filtering & pagination
- [x] Basic OpenAPI docs

### 📦 Later / Feature Plans

- [ ] Web dashboard (Next.js frontend)
- [ ] Team collaboration (invites, roles)
- [ ] Time tracking
- [ ] Webhooks
- [ ] Notifications

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.