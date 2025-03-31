#! /usr/bin/env python3

import os
import sys

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
print(project_root)
sys.path.append(project_root)

from scripts.migrations import run_migrations
from db import get_default_db_path

config = {'DATABASE': get_default_db_path()}
run_migrations(config)