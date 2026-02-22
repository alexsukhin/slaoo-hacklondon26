# Proptech ROI Analysis

Full-stack application for analyzing cost-benefit of property energy efficiency upgrades.

- **Backend**: FastAPI server for property retrofit analysis
- **Frontend**: Simple, clean web interface

# Documentation
https://docs.google.com/document/d/1H52GHHYp-OG4oMswCknATX_GKw4Fb3UlC-6oFadPjUg/edit?tab=t.0

## Quick Start

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create and activate virtual environment:
```bash
# Create venv
python3 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r ../requirements.txt
```

4. Run the server:
```bash
python main.py
```

Backend will be running at `http://localhost:8000`

### Frontend Setup

1. Open a new terminal and navigate to frontend:
```bash
cd frontend
```

2. Start a simple HTTP server:
```bash
# Using Python
python -m http.server 8080

# OR using Node.js
npx http-server -p 8080
```

3. Open your browser to `http://localhost:8080`

## Project Structure

```
.
├── backend/
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models
│   ├── ibex_client.py    # Planning data API client
│   └── geocoding.py      # UPRN geocoding
├── frontend/
│   ├── index.html        # Main page
│   ├── styles.css        # Styling
│   ├── script.js         # API integration
│   └── README.md         # Frontend docs
├── requirements.txt      # Python dependencies
└── README.md            # This file
```
