import logging
import sys
from .config import settings

_LOG_FORMAT = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"

def setup_logging() -> None:
    """
    Idempotent logging setup that plays nicely with uvicorn. 
    We call this once process startes, before creating FastAPI app.
    """
    root = logging.getLogger()
    if root.handlers:
        # already configured by something (uvicorn or something else) -> just tune it to desired levels/format
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler):
                h.setFormatter(logging.Formatter(_LOG_FORMAT))
            h.setLevel(settings.LOG_LEVEL)
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(handler)
        root.setLevel(settings.LOG_LEVEL)
    
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).setLevel(settings.LOG_LEVEL)
    
    # set up SQLAlchemy and Arq logging + more if we need to? 
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("arq").setLevel(logging.INFO)