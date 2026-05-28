"""Punto de entrada del servidor web NutriCosto.

Ejecuta:
    python server.py
    # o, equivalente:
    uvicorn nutricosto.web:app --reload --port 8000
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "nutricosto.web:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
