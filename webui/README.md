# Open Swarm MCP Web UI

This directory contains the React-based frontend for Open Swarm MCP, built with:

- **Vite** - Fast build tool
- **React** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **DaisyUI** - Component library for Tailwind
- **React Router** - Client-side routing

## Development

### Prerequisites

- Node.js v22+ (recommended)
- npm (comes with Node.js)

### Setup

```bash
# Install dependencies
cd webui/frontend
npm install

# Start development server
npm run dev
```

The development server runs on port 3000 and proxies API requests to the Django backend on port 8000.

### Building for Production

```bash
# Build optimized assets
npm run build

# Or use the convenience script
./scripts/build_frontend.sh
```

Built assets will be in `webui/frontend/dist/` and automatically served by Django.

## Project Structure

```
webui/
└── frontend/
    ├── public/          # Static assets
    ├── src/             # Source code
    │   ├── App.tsx       # Main application
    │   ├── main.tsx      # Entry point
    │   └── index.css     # Global styles
    ├── vite.config.ts   # Vite configuration
    ├── tailwind.config.js # Tailwind config
    └── package.json     # Dependencies
```

## Features

- **Responsive Design**: Works on mobile and desktop
- **Dark/Light Mode**: Toggle between themes
- **SPA Routing**: React Router for smooth navigation
- **Modern UI**: DaisyUI v5 components
- **API Integration**: Proxied to Django backend

## Integration with Django

The frontend is automatically detected and served by Django when built. The `index` view in `src/swarm/views/web_views.py` checks for built assets and serves them preferentially over Django templates.

## DaisyUI Components

This project uses DaisyUI v5 with the following themes configured:
- `light` (default)
- `dark`
- `cupcake`

All DaisyUI components are available for use in the React components.
