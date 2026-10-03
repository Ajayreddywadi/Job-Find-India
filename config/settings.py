import os

DEFAULT_TIMEOUT: int = int(os.getenv("DEFAULT_TIMEOUT", "20"))
MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "6"))
MAX_RESULTS_PER_SOURCE: int = int(os.getenv("MAX_RESULTS_PER_SOURCE", "50"))
FUZZY_THRESHOLD: float = float(os.getenv("FUZZY_THRESHOLD", "0.82"))

DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/app.db")
SECRET_KEY: str = os.getenv("SECRET_KEY", "job-find-india-secure-secret-key-2026")

