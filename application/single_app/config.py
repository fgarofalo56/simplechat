# config.py
# Facade module for backward compatibility.
# All symbols are re-exported so existing `from config import *` continues to work.
#
# This file was refactored from a ~800-line monolith into 3 focused modules:
#   - config_constants.py: App constants, environment config, security headers, extensions
#   - config_database.py: Cosmos DB client initialization and container definitions
#   - config_clients.py: Azure service client initialization and custom asset management
#
# To import specific symbols directly from the new modules:
#   from config_constants import VERSION, ALLOWED_EXTENSIONS
#   from config_database import cosmos_user_documents_container
#   from config_clients import initialize_clients

# Re-export standard library and lightweight imports that many modules expect from config
import logging
import os
import requests
import uuid
import tempfile
import json
import time
import threading
import random
import base64
import markdown2
import re
import math
import traceback
import subprocess
import glob
import jwt

# Heavy libraries (docx, fitz, openpyxl, xlrd, pandas, ffmpeg, PIL) are now
# lazy-imported inside the functions that actually need them.
# This reduces startup time and memory usage for requests that don't need
# document processing, PDF operations, or media conversion.

from config_constants import *
from config_database import *
from config_clients import *
