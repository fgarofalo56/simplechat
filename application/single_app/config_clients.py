# config_clients.py
# Azure service client initialization and custom asset management.
# Extracted from config.py for modularity.

import os
import base64

from config_constants import (
    CLIENTS, CLIENTS_LOCK, AZURE_ENVIRONMENT,
    storage_account_user_documents_container_name,
    storage_account_group_documents_container_name,
    storage_account_public_documents_container_name,
)

# These are conditionally defined in config_constants based on AZURE_ENVIRONMENT
# Import them safely with fallbacks
try:
    from config_constants import cognitive_services_scope
except ImportError:
    cognitive_services_scope = None

try:
    from config_constants import search_resource_manager
except ImportError:
    search_resource_manager = None

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.search.documents import SearchClient
from azure.identity import DefaultAzureCredential
from azure.ai.contentsafety import ContentSafetyClient
from azure.storage.blob import BlobServiceClient


def ensure_custom_logo_file_exists(app, settings):
    """
    If custom_logo_base64 or custom_logo_dark_base64 is present in settings, ensure the appropriate
    static files exist and reflect the current base64 data. Overwrites if necessary.
    If base64 is empty/missing, removes the corresponding file.
    """
    # Handle light mode logo
    custom_logo_b64 = settings.get('custom_logo_base64', '')
    logo_filename = 'custom_logo.png'
    logo_path = os.path.join(app.root_path, 'static', 'images', logo_filename)
    images_dir = os.path.dirname(logo_path)

    # Ensure the directory exists
    os.makedirs(images_dir, exist_ok=True)

    if not custom_logo_b64:
        # No custom logo in DB; remove the static file if it exists
        if os.path.exists(logo_path):
            try:
                os.remove(logo_path)
                print(f"Removed existing {logo_filename} as custom logo is disabled/empty.")
            except OSError as ex:
                print(f"Error removing {logo_filename}: {ex}")
    else:
        # Custom logo exists in settings, write/overwrite the file
        try:
            # Decode the current base64 string
            decoded = base64.b64decode(custom_logo_b64)

            # Write the decoded data to the file, overwriting if it exists
            with open(logo_path, 'wb') as f:
                f.write(decoded)
            print(f"Ensured {logo_filename} exists and matches current settings.")

        except (base64.binascii.Error, TypeError, OSError) as ex:
            print(f"Failed to write/overwrite {logo_filename}: {ex}")
        except Exception as ex:
            print(f"Unexpected error writing {logo_filename}: {ex}")

    # Handle dark mode logo
    custom_logo_dark_b64 = settings.get('custom_logo_dark_base64', '')
    logo_dark_filename = 'custom_logo_dark.png'
    logo_dark_path = os.path.join(app.root_path, 'static', 'images', logo_dark_filename)

    if not custom_logo_dark_b64:
        # No custom dark logo in DB; remove the static file if it exists
        if os.path.exists(logo_dark_path):
            try:
                os.remove(logo_dark_path)
                print(f"Removed existing {logo_dark_filename} as custom dark logo is disabled/empty.")
            except OSError as ex:
                print(f"Error removing {logo_dark_filename}: {ex}")
    else:
        # Custom dark logo exists in settings, write/overwrite the file
        try:
            # Decode the current base64 string
            decoded = base64.b64decode(custom_logo_dark_b64)

            # Write the decoded data to the file, overwriting if it exists
            with open(logo_dark_path, 'wb') as f:
                f.write(decoded)
            print(f"Ensured {logo_dark_filename} exists and matches current settings.")

        except (base64.binascii.Error, TypeError, OSError) as ex:
            print(f"Failed to write/overwrite {logo_dark_filename}: {ex}")
        except Exception as ex:
            print(f"Unexpected error writing {logo_dark_filename}: {ex}")

def ensure_custom_favicon_file_exists(app, settings):
    """
    If custom_favicon_base64 is present in settings, ensure static/images/favicon.ico
    exists and reflects the current base64 data. Overwrites if necessary.
    If base64 is empty/missing, uses the default favicon.
    """
    custom_favicon_b64 = settings.get('custom_favicon_base64', '')
    # Ensure the filename is consistent
    favicon_filename = 'favicon.ico'
    favicon_path = os.path.join(app.root_path, 'static', 'images', favicon_filename)
    images_dir = os.path.dirname(favicon_path)

    # Ensure the directory exists
    os.makedirs(images_dir, exist_ok=True)

    if not custom_favicon_b64:
        # No custom favicon in DB; no need to remove the static file as we want to keep the default
        return

    # Custom favicon exists in settings, write/overwrite the file
    try:
        # Decode the current base64 string
        decoded = base64.b64decode(custom_favicon_b64)

        # Write the decoded data to the file, overwriting if it exists
        with open(favicon_path, 'wb') as f:
            f.write(decoded)
        print(f"Ensured {favicon_filename} exists and matches current settings.")

    except (base64.binascii.Error, TypeError, OSError) as ex: # Catch specific errors
        print(f"Failed to write/overwrite {favicon_filename}: {ex}")
    except Exception as ex: # Catch any other unexpected errors
         print(f"Unexpected error during favicon file write for {favicon_filename}: {ex}")

def initialize_clients(settings):
    """
    Initialize/re-initialize all your clients based on the provided settings.
    Store them in a global dictionary so they're accessible throughout the app.
    """
    with CLIENTS_LOCK:
        form_recognizer_endpoint = settings.get("azure_document_intelligence_endpoint")
        form_recognizer_key = settings.get("azure_document_intelligence_key")
        enable_document_intelligence_apim = settings.get("enable_document_intelligence_apim")
        azure_apim_document_intelligence_endpoint = settings.get("azure_apim_document_intelligence_endpoint")
        azure_apim_document_intelligence_subscription_key = settings.get("azure_apim_document_intelligence_subscription_key")

        azure_ai_search_endpoint = settings.get("azure_ai_search_endpoint")
        azure_ai_search_key = settings.get("azure_ai_search_key")
        enable_ai_search_apim = settings.get("enable_ai_search_apim")
        azure_apim_ai_search_endpoint = settings.get("azure_apim_ai_search_endpoint")
        azure_apim_ai_search_subscription_key = settings.get("azure_apim_ai_search_subscription_key")

        enable_enhanced_citations = settings.get("enable_enhanced_citations")
        enable_video_file_support = settings.get("enable_video_file_support")
        enable_audio_file_support = settings.get("enable_audio_file_support")

        try:
            if enable_document_intelligence_apim:
                document_intelligence_client = DocumentIntelligenceClient(
                    endpoint=azure_apim_document_intelligence_endpoint,
                    credential=AzureKeyCredential(azure_apim_document_intelligence_subscription_key)
                )
            else:
                if settings.get("azure_document_intelligence_authentication_type") == "managed_identity":
                    if AZURE_ENVIRONMENT in ("usgovernment", "custom"):
                        document_intelligence_client = DocumentIntelligenceClient(
                            endpoint=form_recognizer_endpoint,
                            credential=DefaultAzureCredential(),
                            credential_scopes=[cognitive_services_scope],
                            api_version="2024-11-30"
                        )
                    else:
                        document_intelligence_client = DocumentIntelligenceClient(
                            endpoint=form_recognizer_endpoint,
                            credential=DefaultAzureCredential()
                        )
                else:
                    document_intelligence_client = DocumentIntelligenceClient(
                        endpoint=form_recognizer_endpoint,
                        credential=AzureKeyCredential(form_recognizer_key)
                    )
            CLIENTS["document_intelligence_client"] = document_intelligence_client
        except Exception as e:
            print(f"Failed to initialize Document Intelligence client: {e}")

        try:
            if enable_ai_search_apim:
                search_client_user = SearchClient(
                    endpoint=azure_apim_ai_search_endpoint,
                    index_name="simplechat-user-index",
                    credential=AzureKeyCredential(azure_apim_ai_search_subscription_key)
                )
                search_client_group = SearchClient(
                    endpoint=azure_apim_ai_search_endpoint,
                    index_name="simplechat-group-index",
                    credential=AzureKeyCredential(azure_apim_ai_search_subscription_key)
                )
                search_client_public = SearchClient(
                    endpoint=azure_apim_ai_search_endpoint,
                    index_name="simplechat-public-index",
                    credential=AzureKeyCredential(azure_apim_ai_search_subscription_key)
                )
            else:
                if settings.get("azure_ai_search_authentication_type") == "managed_identity":
                    if AZURE_ENVIRONMENT in ("usgovernment", "custom"):
                        search_client_user = SearchClient(
                            endpoint=azure_ai_search_endpoint,
                            index_name="simplechat-user-index",
                            credential=DefaultAzureCredential(),
                            audience=search_resource_manager
                        )
                        search_client_group = SearchClient(
                            endpoint=azure_ai_search_endpoint,
                            index_name="simplechat-group-index",
                            credential=DefaultAzureCredential(),
                            audience=search_resource_manager
                        )
                        search_client_public = SearchClient(
                            endpoint=azure_ai_search_endpoint,
                            index_name="simplechat-public-index",
                            credential=DefaultAzureCredential(),
                            audience=search_resource_manager
                        )
                    else:
                        search_client_user = SearchClient(
                            endpoint=azure_ai_search_endpoint,
                            index_name="simplechat-user-index",
                            credential=DefaultAzureCredential()
                        )
                        search_client_group = SearchClient(
                            endpoint=azure_ai_search_endpoint,
                            index_name="simplechat-group-index",
                            credential=DefaultAzureCredential()
                        )
                        search_client_public = SearchClient(
                            endpoint=azure_ai_search_endpoint,
                            index_name="simplechat-public-index",
                            credential=DefaultAzureCredential()
                        )
                else:
                    search_client_user = SearchClient(
                        endpoint=azure_ai_search_endpoint,
                        index_name="simplechat-user-index",
                        credential=AzureKeyCredential(azure_ai_search_key)
                    )
                    search_client_group = SearchClient(
                        endpoint=azure_ai_search_endpoint,
                        index_name="simplechat-group-index",
                        credential=AzureKeyCredential(azure_ai_search_key)
                    )
                    search_client_public = SearchClient(
                        endpoint=azure_ai_search_endpoint,
                        index_name="simplechat-public-index",
                        credential=AzureKeyCredential(azure_ai_search_key)
                    )
            CLIENTS["search_client_user"] = search_client_user
            CLIENTS["search_client_group"] = search_client_group
            CLIENTS["search_client_public"] = search_client_public
        except Exception as e:
            print(f"Failed to initialize Search clients: {e}")

        if settings.get("enable_content_safety"):
            safety_endpoint = settings.get("content_safety_endpoint", "")
            safety_key = settings.get("content_safety_key", "")
            enable_content_safety_apim = settings.get("enable_content_safety_apim")
            azure_apim_content_safety_endpoint = settings.get("azure_apim_content_safety_endpoint")
            azure_apim_content_safety_subscription_key = settings.get("azure_apim_content_safety_subscription_key")

            if safety_endpoint:
                try:
                    if enable_content_safety_apim:
                        content_safety_client = ContentSafetyClient(
                            endpoint=azure_apim_content_safety_endpoint,
                            credential=AzureKeyCredential(azure_apim_content_safety_subscription_key)
                        )
                    else:
                        if settings.get("content_safety_authentication_type") == "managed_identity":
                            if AZURE_ENVIRONMENT in ("usgovernment", "custom"):
                                content_safety_client = ContentSafetyClient(
                                    endpoint=safety_endpoint,
                                    credential=DefaultAzureCredential(),
                                    credential_scopes=[cognitive_services_scope]
                                )
                            else:
                                content_safety_client = ContentSafetyClient(
                                    endpoint=safety_endpoint,
                                    credential=DefaultAzureCredential()
                                )
                        else:
                            content_safety_client = ContentSafetyClient(
                                endpoint=safety_endpoint,
                                credential=AzureKeyCredential(safety_key)
                            )
                    CLIENTS["content_safety_client"] = content_safety_client
                except Exception as e:
                    print(f"Failed to initialize Content Safety client: {e}")
                    CLIENTS["content_safety_client"] = None
            else:
                print("Content Safety enabled, but endpoint/key not provided.")
        else:
            if "content_safety_client" in CLIENTS:
                del CLIENTS["content_safety_client"]


        try:
            if enable_enhanced_citations:
                blob_service_client = None
                if settings.get("office_docs_authentication_type") == "key":
                    blob_service_client = BlobServiceClient.from_connection_string(settings.get("office_docs_storage_account_url"))
                    CLIENTS["storage_account_office_docs_client"] = blob_service_client
                elif settings.get("office_docs_authentication_type") == "managed_identity":
                    blob_service_client = BlobServiceClient(account_url=settings.get("office_docs_storage_account_blob_endpoint"), credential=DefaultAzureCredential())
                    CLIENTS["storage_account_office_docs_client"] = blob_service_client

                # Create containers if they don't exist
                # This addresses the issue where the application assumes containers exist
                if blob_service_client:
                    for container_name in [
                        storage_account_user_documents_container_name,
                        storage_account_group_documents_container_name,
                        storage_account_public_documents_container_name
                        ]:
                        try:
                            container_client = blob_service_client.get_container_client(container_name)
                            if not container_client.exists():
                                print(f"Container '{container_name}' does not exist. Creating...")
                                container_client.create_container()
                                print(f"Container '{container_name}' created successfully.")
                            else:
                                print(f"Container '{container_name}' already exists.")
                        except Exception as container_error:
                            print(f"Error creating container {container_name}: {str(container_error)}")
        except Exception as e:
            print(f"Failed to initialize Blob Storage clients: {e}")
