import sys
import os

# Add the root directory to sys.path to import the backend package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app
