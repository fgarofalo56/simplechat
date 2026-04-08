# config_constants.py
# Application constants, environment configuration, and security settings.
# Extracted from config.py for modularity.

import logging
import os
import threading
import mimetypes

# Register font MIME types so Flask serves them correctly (required for
# X-Content-Type-Options: nosniff to not block Bootstrap Icons)
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('font/ttf', '.ttf')
mimetypes.add_type('font/otf', '.otf')

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    request,
    jsonify,
    render_template,
    redirect,
    url_for,
    session,
    send_from_directory,
    send_file,
    current_app
)
from markupsafe import Markup
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
from functools import wraps
from msal import ConfidentialClientApplication, SerializableTokenCache
from flask_session import Session
from uuid import uuid4
from threading import Thread
from openai import AzureOpenAI, RateLimitError
from cryptography.fernet import Fernet, InvalidToken
from urllib.parse import quote
from flask_executor import Executor
from bs4 import BeautifulSoup
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
    RecursiveJsonSplitter
)
from io import BytesIO
from typing import List

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.search.documents import SearchClient, IndexDocumentsBatch
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SearchField, SearchFieldDataType
from azure.core.exceptions import AzureError, ResourceNotFoundError, HttpResponseError, ServiceRequestError
from azure.core.polling import LROPoller
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.identity import ClientSecretCredential, DefaultAzureCredential, get_bearer_token_provider, AzureAuthorityHosts
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

# Load environment variables from .env file
load_dotenv()

# Flask app configuration constants
EXECUTOR_TYPE = 'thread'
EXECUTOR_MAX_WORKERS = 30
SESSION_TYPE = 'filesystem'
VERSION = "0.239.013"

# Session security configuration
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True  # Always true — no JS access to session cookies
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv('SESSION_LIFETIME_HOURS', '8')))

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "FATAL: SECRET_KEY environment variable is not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\" "
        "and set it in your .env or app service configuration."
    )

# Security Headers Configuration
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(self), geolocation=(), payment=()',
}

def build_csp_header(nonce=None):
    """
    Build the Content-Security-Policy header value.
    Delegates to utils.security for the actual implementation.

    Args:
        nonce: The per-request CSP nonce string (base64url-encoded).

    Returns:
        str: The complete CSP header value.
    """
    from utils.security import build_csp_header as _build_csp
    return _build_csp(nonce)

# Security Configuration
ENABLE_STRICT_TRANSPORT_SECURITY = os.getenv('ENABLE_HSTS', 'false').lower() == 'true'
HSTS_MAX_AGE = int(os.getenv('HSTS_MAX_AGE', '31536000'))  # 1 year default

CLIENTS = {}
CLIENTS_LOCK = threading.Lock()

# Base allowed extensions (always available)
BASE_ALLOWED_EXTENSIONS = {'txt', 'doc', 'docm', 'html', 'md', 'json', 'xml', 'yaml', 'yml', 'log'}
DOCUMENT_EXTENSIONS = {'pdf', 'docx', 'pptx', 'ppt'}
TABULAR_EXTENSIONS = {'csv', 'xlsx', 'xls', 'xlsm'}

# Updates to image, video, or audio extensions should also be made in static/js/chat/chat-enhanced-citations.js if the new file types can be natively rendered in the browser.
IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'heif', 'heic'}

# Optional extensions by feature
VIDEO_EXTENSIONS = {
    'mp4', 'mov', 'avi', 'mkv', 'flv', 'mxf', 'gxf', 'ts', 'ps', '3gp', '3gpp',
    'mpg', 'wmv', 'asf', 'm4v', 'isma', 'ismv', 'dvr-ms', 'webm', 'mpeg'
}

AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a'}

def get_allowed_extensions(enable_video=False, enable_audio=False):
    """
    Get allowed file extensions based on feature flags.

    Args:
        enable_video: Whether video file support is enabled
        enable_audio: Whether audio file support is enabled

    Returns:
        set: Allowed file extensions
    """
    extensions = BASE_ALLOWED_EXTENSIONS.copy()
    extensions.update(DOCUMENT_EXTENSIONS)
    extensions.update(IMAGE_EXTENSIONS)
    extensions.update(TABULAR_EXTENSIONS)

    if enable_video:
        extensions.update(VIDEO_EXTENSIONS)

    if enable_audio:
        extensions.update(AUDIO_EXTENSIONS)

    return extensions

ALLOWED_EXTENSIONS = get_allowed_extensions(enable_video=True, enable_audio=True)

# Admin UI specific extensions (for logo/favicon uploads)
ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH_MB', '200')) * 1024 * 1024  # Default 200 MB, configurable via env

# Add Support for Custom Azure Environments
CUSTOM_GRAPH_URL_VALUE = os.getenv("CUSTOM_GRAPH_URL_VALUE", "")
CUSTOM_IDENTITY_URL_VALUE = os.getenv("CUSTOM_IDENTITY_URL_VALUE", "")
CUSTOM_RESOURCE_MANAGER_URL_VALUE = os.getenv("CUSTOM_RESOURCE_MANAGER_URL_VALUE", "")
CUSTOM_BLOB_STORAGE_URL_VALUE = os.getenv("CUSTOM_BLOB_STORAGE_URL_VALUE", "")
CUSTOM_COGNITIVE_SERVICES_URL_VALUE = os.getenv("CUSTOM_COGNITIVE_SERVICES_URL_VALUE", "")
CUSTOM_SEARCH_RESOURCE_MANAGER_URL_VALUE = os.getenv("CUSTOM_SEARCH_RESOURCE_MANAGER_URL_VALUE", "")
CUSTOM_REDIS_CACHE_INFRASTRUCTURE_URL_VALUE = os.getenv("CUSTOM_REDIS_CACHE_INFRASTRUCTURE_URL_VALUE", "")


# Azure AD Configuration
CLIENT_ID = os.getenv("CLIENT_ID")
APP_URI = f"api://{CLIENT_ID}"
CLIENT_SECRET = os.getenv("MICROSOFT_PROVIDER_AUTHENTICATION_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
SCOPE = ["User.Read", "User.ReadBasic.All", "People.Read.All", "Group.Read.All"] # Adjust scope according to your needs
MICROSOFT_PROVIDER_AUTHENTICATION_SECRET = os.getenv("MICROSOFT_PROVIDER_AUTHENTICATION_SECRET")
LOGIN_REDIRECT_URL = os.getenv("LOGIN_REDIRECT_URL")
HOME_REDIRECT_URL = os.getenv("HOME_REDIRECT_URL")  # Front Door URL for home page

OIDC_METADATA_URL = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration"
AZURE_ENVIRONMENT = os.getenv("AZURE_ENVIRONMENT", "public") # public, usgovernment, custom

if AZURE_ENVIRONMENT == "custom":
    AUTHORITY = f"{CUSTOM_IDENTITY_URL_VALUE}/{TENANT_ID}"
elif AZURE_ENVIRONMENT == "usgovernment":
    AUTHORITY = f"https://login.microsoftonline.us/{TENANT_ID}"
else:
    AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

WORD_CHUNK_SIZE = 400

if AZURE_ENVIRONMENT == "usgovernment":
    OIDC_METADATA_URL = f"https://login.microsoftonline.us/{TENANT_ID}/v2.0/.well-known/openid-configuration"
    resource_manager = "https://management.usgovcloudapi.net"
    authority = AzureAuthorityHosts.AZURE_GOVERNMENT
    credential_scopes=[resource_manager + "/.default"]
    cognitive_services_scope = "https://cognitiveservices.azure.us/.default"
    video_indexer_endpoint = "https://api.videoindexer.ai.azure.us"
    search_resource_manager = "https://search.azure.us"
    KEY_VAULT_DOMAIN = ".vault.usgovcloudapi.net"

elif AZURE_ENVIRONMENT == "custom":
    resource_manager = CUSTOM_RESOURCE_MANAGER_URL_VALUE
    authority = CUSTOM_IDENTITY_URL_VALUE
    video_indexer_endpoint = os.getenv("CUSTOM_VIDEO_INDEXER_ENDPOINT", "https://api.videoindexer.ai")
    credential_scopes=[resource_manager + "/.default"]
    cognitive_services_scope = CUSTOM_COGNITIVE_SERVICES_URL_VALUE
    search_resource_manager = CUSTOM_SEARCH_RESOURCE_MANAGER_URL_VALUE
    KEY_VAULT_DOMAIN = os.getenv("KEY_VAULT_DOMAIN", ".vault.azure.net")
else:
    OIDC_METADATA_URL = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration"
    resource_manager = "https://management.azure.com"
    authority = AzureAuthorityHosts.AZURE_PUBLIC_CLOUD
    credential_scopes=[resource_manager + "/.default"]
    cognitive_services_scope = "https://cognitiveservices.azure.com/.default"
    video_indexer_endpoint = "https://api.videoindexer.ai"
    KEY_VAULT_DOMAIN = ".vault.azure.net"

def get_redis_cache_infrastructure_endpoint(redis_hostname: str) -> str:
    """
    Get the appropriate Redis cache infrastructure endpoint based on Azure environment.

    Args:
        redis_hostname (str): The hostname of the Redis cache instance

    Returns:
        str: The complete endpoint URL for Redis cache infrastructure token acquisition
    """
    if AZURE_ENVIRONMENT == "usgovernment":
        return f"https://{redis_hostname}.cacheinfra.azure.us:10225/appid"
    elif AZURE_ENVIRONMENT == "custom" and CUSTOM_REDIS_CACHE_INFRASTRUCTURE_URL_VALUE:
        # For custom environments, allow override via environment variable
        # Format: https://{hostname}.custom-cache-domain.com:10225/appid
        return CUSTOM_REDIS_CACHE_INFRASTRUCTURE_URL_VALUE.format(hostname=redis_hostname)
    else:
        # Default to Azure Public Cloud
        return f"https://{redis_hostname}.cacheinfra.windows.net:10225/appid"

storage_account_user_documents_container_name = "user-documents"
storage_account_group_documents_container_name = "group-documents"
storage_account_public_documents_container_name = "public-documents"
