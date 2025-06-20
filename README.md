# Smithy

![Smithy Banner](.github/assets/banner.png)

A minimalist, backend-focused project and task management platform built for developers.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.114+-00a393.svg)](https://fastapi.tiangolo.com)
[![Linted with Ruff](https://img.shields.io/badge/linting-ruff-blue)](https://docs.astral.sh/ruff/)

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

-

### Quick Start

---

## 🏗️ Architecture

---

## 🧪 Testing

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing-feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📋 Roadmap

### 🧱 Foundation

- [x] Project scaffold (folder structure, FastAPI app)
- [x] Environment setup (.env, config loader)
- [ ] Base Dockerfile + docker-compose
- [ ] SQLAlchemy models (User, Project, Task)
- [x] Alembic migrations
- [x] JWT authentication (access and refresh)
- [ ] Initial tests (pytest + coverage)
- [x] Basic logging + error handling

### 📡 API Layer

- [x] Auth endpoints (register, login, refresh)
- [ ] User CRUD
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