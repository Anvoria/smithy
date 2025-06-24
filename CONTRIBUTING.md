# 🛠️ Contributing to Smithy

Thanks for considering contributing to **Smithy** - the project management forge for developers.

Whether you're here to fix a typo or forge a new feature, you're in the right place.

---

## 🔧 Local Setup

Make sure you have:

- Python 3.13+ (for backend)
- Node.js 20+ (for frontend)
- Docker & Docker Compose
- Git

```bash
# Clone the repo
git clone https://github.com/Anvoria/smithy.git
cd smithy

# Quick start with Docker (recommended)
docker-compose up --build

# Or set up development environment
```

### Backend Development Setup

```bash
cd backend

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 📦 Project Structure

```
smithy/
├── backend/                    # FastAPI backend
│   ├── app/                    # Core application logic
│   │   ├── api/                # API endpoints
│   │   ├── core/               # Auth, config, middleware
│   │   ├── db/                 # Database config
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   └── services/           # Business logic
│   ├── alembic/                # Database migrations
│   └── scripts/                # Utility scripts
├── frontend/                   # Next.js frontend
│   ├── src/app/                # App router pages
│   └── public/                 # Static assets
├── docker-compose.yml          # Production compose
├── docker-compose.dev.yml      # Development compose
└── scripts/                    # Project-wide scripts
```

---

## 🧪 Development Guidelines

### Backend (Python)

We use **Ruff** for linting and formatting and **pre-commit** for automated checks:

```bash
cd backend

# Manual linting (optional)
ruff check app/
ruff check app/ --fix
ruff format app/
```

**Note:** Pre-commit hooks will automatically run Ruff checks before each commit. If you haven't installed pre-commit hooks yet, run `pre-commit install` in the project root.

### Frontend (TypeScript)

We use **ESLint** and **Prettier**:

```bash
cd frontend

# Run linting
npm run lint
# Fix linting issues
npm run lint:fix
# Format code
npm run format
```

---

## 🧱 Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
feat: add project creation API
fix: resolve user auth flow bug
chore: update dependencies
refactor: clean up token generation logic
docs: update API documentation
test: add user service tests
```

**Scope examples:**
- `feat(backend): add MFA support`
- `fix(frontend): resolve login form validation`
- `docs(api): update authentication endpoints`

---

## 🤝 Pull Request Process

### Before You Start
1. **Open an issue** to discuss your proposed changes
2. Wait for maintainer approval/feedback
3. Check if someone else is already working on it

### Development Workflow
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes in small, logical commits
4. Test your changes locally
5. Run linting and formatting tools
6. Push to your fork: `git push origin feature/new-feature`
7. Open a Pull Request against `develop` branch

### PR Requirements
- [ ] Clear description of what the PR does
- [ ] Reference any related issues (#123)
- [ ] Tests pass (when we have them)
- [ ] Code is properly formatted
- [ ] No merge conflicts

---

## 🧪 Testing (Coming Soon)

We're working on comprehensive test suites.

---

## 📋 Issue Labels

- `good first issue` - Good for newcomers to the project
- `help wanted` - Extra attention is needed
- `bug` - Something isn't working correctly
- `feature` - New feature or functionality
- `docs` - Documentation improvements
- `frontend` - Frontend issues
- `backend` - Backend issues

---

## 🎯 Areas We Need Help

1. **Testing** - Writing comprehensive test suites
2. **Documentation** - API docs, user guides, tutorials
3. **Performance** - Database optimization, caching
4. **Security** - Security audits, best practices
5. **DevOps** - CI/CD, deployment automation

---

## 💬 Getting Help

- **Questions?** Open a discussion or issue
- **Bug reports?** Use the bug report template
- **Feature requests?** Use the feature request template

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).