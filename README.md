# Proptech ROI Analysis - Green Brick

Full-stack application for analyzing cost-benefit of property energy efficiency upgrades.

- **Backend**: FastAPI server for property retrofit analysis
- **Frontend**: Clean web interface via HTML, CSS and JavaScript

## Devpost

https://devpost.com/software/slao

## About Green Brick

Green Brick helps homeowners plan energy efficiency upgrades by turning fragmented data (EPC ratings, property values, planning approvals) into actionable insights.

With Green Brick, users can:
- **See the potential ROI**
- **Check Feasibility**
- **Measure environmental feedback**
- **Explore Nearby Examples**

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

# Activate
source venv/bin/activate
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
python -m http.server 8080
```

3. Open your browser to `http://localhost:8080`
