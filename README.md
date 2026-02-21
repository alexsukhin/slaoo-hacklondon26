# Proptech Analysis Backend

FastAPI backend for property energy efficiency and planning analysis.

# Documentation
https://docs.google.com/document/d/1H52GHHYp-OG4oMswCknATX_GKw4Fb3UlC-6oFadPjUg/edit?tab=t.0

## Setup

1. Create and activate virtual environment:
```bash
# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate

```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python main.py
```
## API Endpoints

### GET /health
Health check endpoint

### POST /api/property/analyze
Analyze a property with planning data
```json
{
  "latitude": 51.5074,
  "longitude": -0.1278,
  "radius": 300
}
```

### POST /api/area/retrofits
Find retrofit projects (solar, insulation, etc.) in an area
```json
{
  "latitude": 51.5074,
  "longitude": -0.1278,
  "radius": 500,
  "improvement_type": "solar"
}
```

### GET/POST /api/planning/search
Search planning applications
- GET: Use query parameters
- POST: Same parameters in request body

### GET /api/council/{council_id}/stats
Get council planning statistics

### POST /api/area/analysis
Detailed area analysis with statistics

## Testing

Access the interactive API docs at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Example Coordinates

- London: 51.5074, -0.1278
- Manchester: 53.4808, -2.2426
- Birmingham: 52.4862, -1.8904
