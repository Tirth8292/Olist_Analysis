# This is the Vercel entry point
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from olist_platform.api.dashboard_api import app
