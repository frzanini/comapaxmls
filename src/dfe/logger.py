from __future__ import annotations
import logging, os

def get_logger(name: str) -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log
    level = os.getenv("DFE_LOG_LEVEL", "INFO").upper()
    log.setLevel(level)
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    log.addHandler(h)
    return log
