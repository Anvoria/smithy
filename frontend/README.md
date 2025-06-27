# Smithy Frontend

Built with **Next.js 15**, **React 19**, and **TypeScript** for a fast, responsive user experience.

---

## 🚀 Getting Started

### Prerequisites

- **Node.js 20+**
- **pnpm** (you have to install it via npm using `npm install -g pnpm`)

### Development Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pnpm install

# Start development server with Turbopack
pnpm run dev

# The application will be available at:
# http://localhost:3000
```

### Available Scripts

```bash
# Development
pnpm run dev          # Start development server with Turbopack
pnpm run build        # Build for production
pnpm run start        # Start production server

# Code Quality
pnpm run lint         # Run ESLint
pnpm run lint:fix     # Fix ESLint issues automatically
pnpm run format       # Format code with Prettier
```

---

## 🔐 Authentication System

The frontend implements a comprehensive authentication system:

### Components

- **AuthGuard** - Protects routes requiring authentication
- **GuestGuard** - Redirects authenticated users away from auth pages
- ~~**RoleGuard** - Protects routes based on user roles~~ (soon™️)
- **LoginForm** - Multi-step login with email/password and MFA support

### Features

- JWT token management (access + refresh tokens)
- Multi-factor authentication (TOTP)
- Remember me functionality
- Automatic token refresh
- Route protection and redirection

### Usage Example

```tsx
import { AuthGuard } from '@/components/auth/AuthGuard';

export default function ProtectedPage() {
    return (
        <AuthGuard>
            <div>This content requires authentication</div>
        </AuthGuard>
    );
}
```

---

## 🎨 Styling

The project uses a custom design system built with:

- **Tailwind CSS 4** - Utility-first CSS framework
- **Custom CSS Variables** - Theme colors and spacing
- **Component-based Design** - Reusable UI components

### Theme Colors

- **Charcoal Black** (`--charcoal-black`) - Primary background
- **Coal Shadow** (`--coal-shadow`) - Secondary background
- **Forge Orange** (`--forge-orange`) - Brand accent
- **Ash Gray** (`--ash-gray`) - Text color

---

## 🧪 Development Guidelines

### Code Style

We use automated tools for consistent code quality:

```bash
# ESLint for code quality
pnpm run lint

# Prettier for formatting
pnpm run format

# Pre-commit hooks via Husky
pnpm run prepare
```

### TypeScript

- Strict mode enabled
- Full type safety for API responses
- Component prop validation

## 🔗 Integration with Backend

The frontend connects to the FastAPI backend running on port 8000.

See the main [project README](../README.md) for full-stack setup instructions.

---

## 📝 Contributing

Please see the main [Contributing Guide](../CONTRIBUTING.md) for:

- Development environment setup
- Code style guidelines
- Submitting pull requests
- Reporting issues

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
