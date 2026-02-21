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
## Features

### Analysis Capabilities
- 🏠 Property retrofit ROI analysis
- 💰 Cost-benefit calculations
- 📊 Green premium valuation
- ✅ Planning approval feasibility
- ⏱️ Average approval timelines
- 📍 Location-based historical data

### Supported Improvements
- ☀️ Solar Panels (~£7,000, 3.5% ROI)
- 🏠 Insulation (~£4,500, 2.8% ROI)
- 🪟 Windows (~£5,500, 2.2% ROI)
- 🔥 Heat Pump (~£12,000, 4.2% ROI)

## API Endpoints

### GET /health
Health check endpoint

### POST /api/analyze
Analyze property retrofit feasibility, ROI, and timeline
```json
{
  "property_reference": "100021000001",
  "latitude": 51.5074,
  "longitude": -0.1278,
  "budget": 15000,
  "desired_improvements": ["solar", "insulation"]
}
```

## Usage

### Web Interface
1. Open `http://localhost:8080` in your browser
2. Enter property details (UPRN, coordinates, budget)
3. Select desired improvements
4. Click "Analyze Property"
5. View detailed ROI analysis with local examples

### API Documentation
Access the interactive API docs at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Example Test Data

**Property Coordinates:**
- London: 51.5074, -0.1278
- Manchester: 53.4808, -2.2426
- Birmingham: 52.4862, -1.8904

**Sample Request:**
- UPRN: 100021000001
- Budget: £15,000
- Improvements: Solar, Insulation

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
