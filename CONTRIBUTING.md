# 🛠️ Contributing to Smithy

Thanks for considering contributing to **Smithy** - the project management forge for developers.

Whether you're here to fix a typo or forge a new feature, you're in the right place.

---

## 🔧 Local Setup

Make sure you have:

- Python 3.13+
- Docker & Docker Compose
- Virtualenv (optional but recommended)

```bash
# Clone the repo
git clone https://github.com/Anvoria/smithy-backend.git
cd smithy-backend

# Set up virtual environment
python -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt
```

To spin up full stack:
```bash
docker-compose up --build
```

---

## 📦 Project Structure

Key folders:
- `app/` - core logic
- `alembic/` - DB migrations
- `tests/` - coming soon

---

## 🧪 Linting & Formatting

We use **Ruff** for linting and formatting.

```bash
# Run Ruff checks
ruff check .
# Auto-fix lint issues
ruff check . --fix
```

---

## 🧱 Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
feat: add project creation API
fix: fix user auth flow bug
chore: update dependencies
refactor: clean up token generation logic
```

---

## 🧪 Tests (soon)

---

## 🤝 Pull Request Process

1. Fork and clone the repo
2. Create a new branch (`feature/my-change`)
3. Commit your changes with a meaningful message
4. Push to your fork
5. Open a Pull Request against `main`

---

## 📜 License

By contributing, you agree that your code will be licensed under the [MIT License](LICENSE)
