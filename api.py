"""ParseAnything Universal API Server Entrypoint.
Delegates to backend.api.
"""

from backend.api import app

if __name__ == "__main__":
    import uvicorn
    print("Starting ParseAnything Universal Engine on http://127.0.0.1:8000")
    uvicorn.run("backend.api:app", host="127.0.0.1", port=8000, reload=False)
