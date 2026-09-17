from __future__ import annotations

import logging
import sys
from typing import Any

FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: str = "INFO", stream: Any = sys.stdout) -> None:
    logging.basicConfig(
        level=level.upper(),
        format=FORMAT,
        stream=stream,
    )
