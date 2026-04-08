# functions_documents.py
# Backward-compatible facade — re-exports all document functions from focused service modules.
#
# This file was decomposed into 8 service modules under services/:
#   - document_service.py    — CRUD operations (create, get, update, delete, versions)
#   - chunk_service.py       — chunk save/get/delete, PDF page splitting
#   - blob_service.py        — Azure Blob Storage upload/delete
#   - document_processing.py — format-specific processors, upload dispatcher
#   - media_service.py       — video (Azure Video Indexer) and audio (Azure Speech) processing
#   - metadata_service.py    — metadata extraction, vision analysis
#   - sharing_service.py     — document sharing between users/groups
#   - tag_service.py         — tag CRUD, normalization, propagation
#
# All existing imports like `from functions_documents import *` continue to work unchanged.

# Original imports — kept for backward compatibility with callers that depend on
# these being available via `from functions_documents import *`.
from config import *
from functions_content import *
from functions_settings import *
from functions_search import *
from functions_logging import *
from functions_authentication import *
from functions_debug import *
import azure.cognitiveservices.speech as speechsdk

# Re-export all functions from service modules.
from services.document_service import *
from services.chunk_service import *
from services.blob_service import *
from services.document_processing import *
from services.media_service import *
from services.metadata_service import *
from services.sharing_service import *
from services.tag_service import *
