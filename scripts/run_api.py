from __future__ import annotations

import uvicorn

from app.core.config import get_settings
from app.main import app

__all__ = ["app"]


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "scripts.run_api:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
        factory=False,
    )


if __name__ == "__main__":
    main()
