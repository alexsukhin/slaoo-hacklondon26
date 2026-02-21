# Proptech Analysis Frontend

Simple, clean frontend for the Proptech ROI Analysis API.

## Features

- 🏠 Property analysis form with UPRN input
- 💰 Budget and improvement type selection
- 📊 Visual display of ROI, costs, and value increases
- ✅ Feasibility ratings based on local approvals
- 📋 Real planning application examples
- 📱 Responsive design

## Getting Started

### 1. Start the Backend

Make sure the backend is running first:

```bash
cd ../backend
python main.py
```

The API should be running at `http://localhost:8000`

### 2. Serve the Frontend

You can use any simple HTTP server. Here are a few options:

**Option A: Python**
```bash
cd frontend
python -m http.server 8080
```

**Option B: Node.js (http-server)**
```bash
cd frontend
npx http-server -p 8080
```

**Option C: PHP**
```bash
cd frontend
php -S localhost:8080
```

**Option D: VS Code Live Server**
- Install the "Live Server" extension
- Right-click on `index.html`
- Select "Open with Live Server"

### 3. Open in Browser

Navigate to `http://localhost:8080` (or whatever port you chose)

## Usage

1. Enter a property reference (UPRN)
2. Optionally add latitude/longitude coordinates
3. Set your budget
4. Select desired improvements (solar, insulation, windows, heat pump)
5. Click "Analyze Property"
6. View detailed ROI analysis and local examples

## Example Values

- **UPRN**: Any valid property reference
- **Latitude**: 51.5074 (London)
- **Longitude**: -0.1278 (London)
- **Budget**: 15000

## Architecture

- **index.html** - Main page structure
- **styles.css** - Modern, responsive styling with gradient theme
- **script.js** - API integration and dynamic UI updates

## API Integration

The frontend connects to the backend at `http://localhost:8000/api/analyze`

CORS is already enabled in the FastAPI backend, so no additional configuration is needed.
