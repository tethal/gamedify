# Gamedify

## Project setup

1. Clone the repository
2. Create venv: `python3 -m venv .venv`
3. Activate venv: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the server: `uvicorn app.main:app --reload`
6. Open the browser and go to `http://localhost:8000`

## Testing

1. Install playwright dependencies: `playwright install --with-deps chromium`
2. Make sure the server is running
3. Execute `pytest`
4. To open the browser and see the tests running, execute `pytest --headed --slowmo 1000`
