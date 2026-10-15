"""E31 shim: E29-era scripts and tests import guard29; they get the E31 guard (writes confined to E31)."""
from guard31 import *  # noqa: F401,F403
from guard31 import _under, check, install, AccessDenied  # noqa: F401
