from __future__ import annotations

import logging

from .config import app_dir


def configure_logging() -> None:
    path = app_dir() / "talk-dat-shi.log"
    logging.basicConfig(
        filename=str(path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
