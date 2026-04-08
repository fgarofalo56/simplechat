# metadata_service.py
# Document metadata extraction and analysis — keywords, abstract, vision analysis.

from config import *
from functions_settings import get_settings
from functions_debug import debug_print
from functions_logging import *

def detect_doc_type(document_id, user_id=None):
    """
    Check Cosmos to see if this doc belongs to the user's docs (has user_id),
    the group's docs (has group_id), or public workspace docs (has public_workspace_id).
    Returns one of: "personal", "group", "public", or None if not found.
    Optionally checks if user_id matches (for user docs).
    """

    try:
        doc_item = cosmos_user_documents_container.read_item(
            document_id,
            partition_key=document_id
        )
        if user_id and doc_item.get('user_id') != user_id:
            pass
        else:
            return "personal", doc_item['user_id']
    except:
        pass

    try:
        group_doc_item = cosmos_group_documents_container.read_item(
            document_id,
            partition_key=document_id
        )
        return "group", group_doc_item['group_id']
    except:
        pass

    try:
        public_doc_item = cosmos_public_documents_container.read_item(
            document_id,
            partition_key=document_id
        )
        return "public", public_doc_item['public_workspace_id']
    except:
        pass

    return None

def process_metadata_extraction_background(document_id, user_id, group_id=None, public_workspace_id=None):
    """
    Background function that calls extract_document_metadata(...)
    and updates Cosmos DB accordingly.
    """
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    try:
        # Log status: starting
        args = {
            "document_id": document_id,
            "user_id": user_id,
            "percentage_complete": 5,
            "status": "Metadata extraction started..."
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        update_document(**args)

        # Call your existing extraction function
        args = {
            "document_id": document_id,
            "user_id": user_id
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        metadata = extract_document_metadata(**args)


        if not metadata:
            # If it fails or returns nothing, log an error status and quit
            args = {
                "document_id": document_id,
                "user_id": user_id,
                "status": "Metadata extraction returned empty or failed"
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            update_document(**args)

            return

        # Persist the returned metadata fields back into Cosmos
        args_metadata = {
            "document_id": document_id,
            "user_id": user_id,
            "title": metadata.get('title'),
            "authors": metadata.get('authors'),
            "abstract": metadata.get('abstract'),
            "keywords": metadata.get('keywords'),
            "publication_date": metadata.get('publication_date'),
            "organization": metadata.get('organization')
        }

        if is_public_workspace:
            args_metadata["public_workspace_id"] = public_workspace_id
        elif is_group:
            args_metadata["group_id"] = group_id

        update_document(**args_metadata)

        args_status = {
            "document_id": document_id,
            "user_id": user_id,
            "status": "Metadata extraction complete",
            "percentage_complete": 100
        }

        if is_public_workspace:
            args_status["public_workspace_id"] = public_workspace_id
        elif is_group:
            args_status["group_id"] = group_id

        update_document(**args_status)

    except Exception as e:
        # Log any exceptions
        args = {
            "document_id": document_id,
            "user_id": user_id,
            "status": f"Metadata extraction failed: {str(e)}"
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        update_document(**args)

def extract_document_metadata(document_id, user_id, group_id=None, public_workspace_id=None):
    """
    Extract metadata from a document stored in Cosmos DB.
    This function is called in the background after the document is uploaded.
    It retrieves the document from Cosmos DB, extracts metadata, and performs
    content safety checks.
    """

    settings = get_settings()
    enable_gpt_apim = settings.get('enable_gpt_apim', False)
    enable_user_workspace = settings.get('enable_user_workspace', False)
    enable_group_workspaces = settings.get('enable_group_workspaces', False)

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
        id_key = "public_workspace_id"
        id_value = public_workspace_id
    elif is_group:
        cosmos_container = cosmos_group_documents_container
        id_key = "group_id"
        id_value = group_id
    else:
        cosmos_container = cosmos_user_documents_container
        id_key = "user_id"
        id_value = user_id

    add_file_task_to_file_processing_log(
        document_id=document_id,
        user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
        content=f"Querying metadata for document {document_id} and user {user_id}"
    )

    # Example structure for reference
    meta_data_example = {
        "title": "Title here",
        "authors": ["Author 1", "Author 2"],
        "organization": "Organization or Unknown",
        "publication_date": "MM/YYYY or N/A",
        "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
        "abstract": "two sentence abstract"
    }

    # Pre-initialize metadata dictionary
    meta_data = {
        "title": "",
        "authors": [],
        "organization": "",
        "publication_date": "",
        "keywords": [],
        "abstract": ""
    }

    if is_public_workspace:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.public_workspace_id = @public_workspace_id
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.group_id = @group_id
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.user_id = @user_id
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]

    # --- Step 1: Retrieve document from Cosmos ---
    try:
        document_items = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        args = {
            "document_id": document_id,
            "user_id": user_id,
            "status": f"Retrieved document items for document {document_id}"
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        update_document(**args)


        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Retrieved document items for document {document_id}: {document_items}"
        )
    except Exception as e:
        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Error querying document items for document {document_id}: {e}"
        )
        debug_print(f"Error querying document items for document {document_id}: {e}")

    if not document_items:
        return None

    document_metadata = document_items[0]

    # --- Step 2: Populate meta_data from DB ---
    # Convert the DB fields to the correct structure
    if "title" in document_metadata:
        meta_data["title"] = document_metadata["title"]
    if "authors" in document_metadata:
        meta_data["authors"] = ensure_list(document_metadata["authors"])
    if "organization" in document_metadata:
        meta_data["organization"] = document_metadata["organization"]
    if "publication_date" in document_metadata:
        meta_data["publication_date"] = document_metadata["publication_date"]
    if "keywords" in document_metadata:
        meta_data["keywords"] = ensure_list(document_metadata["keywords"])
    if "abstract" in document_metadata:
        meta_data["abstract"] = document_metadata["abstract"]

    add_file_task_to_file_processing_log(
        document_id=document_id,
        user_id=group_id if is_group else user_id,
        content=f"Extracted metadata for document {document_id}, metadata: {meta_data}"
    )

    args = {
        "document_id": document_id,
        "user_id": user_id,
        "status": f"Extracted metadata for document {document_id}"
    }

    if is_public_workspace:
        args["public_workspace_id"] = public_workspace_id
    elif is_group:
        args["group_id"] = group_id

    update_document(**args)


    # --- Step 3: Content Safety Check (if enabled) ---
    if settings.get('enable_content_safety') and "content_safety_client" in CLIENTS:
        content_safety_client = CLIENTS["content_safety_client"]
        blocked = False
        block_reasons = []
        triggered_categories = []
        blocklist_matches = []

        try:
            request_obj = AnalyzeTextOptions(text=json.dumps(meta_data))
            cs_response = content_safety_client.analyze_text(request_obj)

            max_severity = 0
            for cat_result in cs_response.categories_analysis:
                triggered_categories.append({
                    "category": cat_result.category,
                    "severity": cat_result.severity
                })
                if cat_result.severity > max_severity:
                    max_severity = cat_result.severity

            if cs_response.blocklists_match:
                for match in cs_response.blocklists_match:
                    blocklist_matches.append({
                        "blocklistName": match.blocklist_name,
                        "blocklistItemId": match.blocklist_item_id,
                        "blocklistItemText": match.blocklist_item_text
                    })

            if max_severity >= 4:
                blocked = True
                block_reasons.append("Max severity >= 4")
            if blocklist_matches:
                blocked = True
                block_reasons.append("Blocklist match")

            if blocked:
                add_file_task_to_file_processing_log(
                    document_id=document_id,
                    user_id=group_id if is_group else user_id,
                    content=f"Blocked document metadata: {document_metadata}, reasons: {block_reasons}"
                )
                debug_print(f"Blocked document metadata: {document_metadata}\nReasons: {block_reasons}")
                return None

        except Exception as e:
            add_file_task_to_file_processing_log(
                document_id=document_id,
                user_id=group_id if is_group else user_id,
                content=f"Error checking content safety for document metadata: {e}"
            )
            debug_print(f"Error checking content safety for document metadata: {e}")

    # --- Step 4: Hybrid Search ---
    try:
        if enable_user_workspace or enable_group_workspaces:
            add_file_task_to_file_processing_log(
                document_id=document_id,
                user_id=group_id if is_group else user_id,
                content=f"Processing Hybrid search for document {document_id} using json dump of metadata {json.dumps(meta_data)}"
            )

            args = {
                "document_id": document_id,
                "user_id": user_id,
                "status": f"Collecting document data to generate metadata from document: {document_id}"
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            update_document(**args)


            document_scope, scope_id = detect_doc_type(
                document_id,
                user_id
            )

            if document_scope == "personal":
                search_results = hybrid_search(
                    json.dumps(meta_data),
                    user_id,
                    document_id=document_id,
                    top_n=12,
                    doc_scope=document_scope
                )
            elif document_scope == "group":
                search_results = hybrid_search(
                    json.dumps(meta_data),
                    user_id,
                    document_id=document_id,
                    top_n=12,
                    doc_scope=document_scope,
                    active_group_id=scope_id
                )
            elif document_scope == "public":
                search_results = hybrid_search(
                    json.dumps(meta_data),
                    user_id,
                    document_id=document_id,
                    top_n=12,
                    doc_scope=document_scope,
                    active_public_workspace_id=scope_id
                )
            else:
                # If document scope is not detected, but we know it's a public workspace document
                # (since we're in this function with public_workspace_id), use public scope
                if is_public_workspace:
                    search_results = hybrid_search(
                        json.dumps(meta_data),
                        user_id,
                        document_id=document_id,
                        top_n=12,
                        doc_scope="public",
                        active_public_workspace_id=public_workspace_id
                    )
                else:
                    search_results = "No Hybrid results"

        else:
            search_results = "No Hybrid results"
    except Exception as e:
        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Error processing Hybrid search for document {document_id}: {e}"
        )
        debug_print(f"Error processing Hybrid search for document {document_id}: {e}")
        search_results = "No Hybrid results"

    gpt_model = settings.get('metadata_extraction_model')

    # --- Step 5: Prepare GPT Client ---
    if enable_gpt_apim:
        # APIM-based GPT client
        gpt_client = AzureOpenAI(
            api_version=settings.get('azure_apim_gpt_api_version'),
            azure_endpoint=settings.get('azure_apim_gpt_endpoint'),
            api_key=settings.get('azure_apim_gpt_subscription_key')
        )
    else:
        # Standard Azure OpenAI approach
        if settings.get('azure_openai_gpt_authentication_type') == 'managed_identity':
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                cognitive_services_scope
            )
            gpt_client = AzureOpenAI(
                api_version=settings.get('azure_openai_gpt_api_version'),
                azure_endpoint=settings.get('azure_openai_gpt_endpoint'),
                azure_ad_token_provider=token_provider
            )
        else:
            gpt_client = AzureOpenAI(
                api_version=settings.get('azure_openai_gpt_api_version'),
                azure_endpoint=settings.get('azure_openai_gpt_endpoint'),
                api_key=settings.get('azure_openai_gpt_key')
            )

    # --- Step 6: GPT Prompt and JSON Parsing ---
    try:
        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Sending search results to AI to generate metadata {document_id}"
        )
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant that extracts metadata. Return valid JSON."
            },
            {
                "role": "user",
                "content": (
                    f"Search results from AI search index:\n{search_results}\n\n"
                    f"Current known metadata:\n{json.dumps(meta_data, indent=2)}\n\n"
                    f"Desired metadata structure:\n{json.dumps(meta_data_example, indent=2)}\n\n"
                    f"Please attempt to fill in any missing, or empty values."
                    f"If generating keywords, please create 5-10 keywords."
                    f"Return only JSON."
                )
            }
        ]

        response = gpt_client.chat.completions.create(
            model=gpt_model,
            messages=messages
        )

    except Exception as e:
        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Error processing GPT request for document {document_id}: {e}"
        )
        debug_print(f"Error processing GPT request for document {document_id}: {e}")
        return meta_data  # Return what we have so far

    if not response:
        return meta_data  # or None, depending on your logic

    response_content = response.choices[0].message.content
    add_file_task_to_file_processing_log(
        document_id=document_id,
        user_id=group_id if is_group else user_id,
        content=f"GPT response for document {document_id}: {response_content}"
    )

    # --- Step 7: Clean and parse the GPT JSON output ---
    try:
        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Decoding JSON from GPT response for document {document_id}"
        )

        cleaned_str = clean_json_codeFence(response_content)

        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Cleaned JSON from GPT response for document {document_id}: {cleaned_str}"
        )

        gpt_output = json.loads(cleaned_str)

        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Decoded JSON from GPT response for document {document_id}: {gpt_output}"
        )

        # Ensure authors and keywords are always lists
        gpt_output["authors"] = ensure_list(gpt_output.get("authors", []))
        gpt_output["keywords"] = ensure_list(gpt_output.get("keywords", []))

    except (json.JSONDecodeError, TypeError) as e:
        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=group_id if is_group else user_id,
            content=f"Error decoding JSON from GPT response for document {document_id}: {e}"
        )
        debug_print(f"Error decoding JSON from response: {e}")
        return meta_data  # or None

    # --- Step 8: Merge GPT Output with Existing Metadata ---
    #
    # If the DB's version is effectively empty/worthless, then overwrite
    # with the GPT's version if GPT has something non-empty.
    # Otherwise keep the DB's version.
    #

    # Title
    if is_effectively_empty(meta_data["title"]):
        meta_data["title"] = gpt_output.get("title", meta_data["title"])

    # Authors
    if is_effectively_empty(meta_data["authors"]):
        # If GPT has no authors either, fallback to ["Unknown"]
        meta_data["authors"] = gpt_output["authors"] or ["Unknown"]

    # Organization
    if is_effectively_empty(meta_data["organization"]):
        meta_data["organization"] = gpt_output.get("organization", meta_data["organization"])

    # Publication Date
    if is_effectively_empty(meta_data["publication_date"]):
        meta_data["publication_date"] = gpt_output.get("publication_date", meta_data["publication_date"])

    # Keywords
    if is_effectively_empty(meta_data["keywords"]):
        meta_data["keywords"] = gpt_output["keywords"]

    # Abstract
    if is_effectively_empty(meta_data["abstract"]):
        meta_data["abstract"] = gpt_output.get("abstract", meta_data["abstract"])

    add_file_task_to_file_processing_log(
        document_id=document_id,
        user_id=group_id if is_group else user_id,
        content=f"Final metadata for document {document_id}: {meta_data}"
    )

    args = {
        "document_id": document_id,
        "user_id": user_id,
        "status": f"Metadata generated for document {document_id}"
    }

    if is_public_workspace:
        args["public_workspace_id"] = public_workspace_id
    elif is_group:
        args["group_id"] = group_id

    update_document(**args)


    return meta_data

def clean_json_codeFence(response_content: str) -> str:
    """
    Removes leading and trailing triple-backticks (```) or ```json
    from a string so that it can be parsed as JSON.
    """
    # Remove any ```json or ``` (with optional whitespace/newlines) at the start
    cleaned = re.sub(r"(?s)^```(?:json)?\s*", "", response_content.strip())
    # Remove trailing ``` on its own line or at the end
    cleaned = re.sub(r"```$", "", cleaned.strip())
    return cleaned.strip()

def ensure_list(value, delimiters=r"[;,]"):
    """
    Ensures the provided value is returned as a list of strings.
    - If `value` is already a list, it is returned as-is.
    - If `value` is a string, it is split on the given delimiters
      (default: commas and semicolons).
    - Otherwise, return an empty list.
    """
    if isinstance(value, list):
        return value
    elif isinstance(value, str):
        # Split on the given delimiters (commas, semicolons, etc.)
        items = re.split(delimiters, value)
        # Strip whitespace and remove empty strings
        items = [item.strip() for item in items if item.strip()]
        return items
    else:
        return []

def is_effectively_empty(value):
    """
    Returns True if the value is 'worthless' or empty.
    - For a string: empty or just whitespace
    - For a list: empty OR all empty strings
    - For None: obviously empty
    - For other types: not considered here, but you can extend as needed
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()  # '' or whitespace is empty
    if isinstance(value, list):
        # Example: [] or [''] or [' ', ''] is empty
        # If *every* item is effectively empty as a string, treat as empty
        if len(value) == 0:
            return True
        return all(not item.strip() for item in value if isinstance(item, str))
    return False

def estimate_word_count(text):
    """Estimates the number of words in a string."""
    if not text:
        return 0
    return len(text.split())

def analyze_image_with_vision_model(image_path, user_id, document_id, settings):
    """
    Analyze image using GPT-4 Vision or similar multimodal model.

    Args:
        image_path: Path to image file
        user_id: User ID for logging
        document_id: Document ID for tracking
        settings: Application settings

    Returns:
        dict: {
            'description': 'AI-generated image description',
            'objects': ['list', 'of', 'detected', 'objects'],
            'text': 'any text visible in image',
            'analysis': 'detailed analysis'
        } or None if vision analysis is disabled or fails
    """
    debug_print(f"[VISION_ANALYSIS_V2] Function entry - document_id: {document_id}, user_id: {user_id}")


    try:
        # Convert image to base64
        with open(image_path, 'rb') as img_file:
            image_bytes = img_file.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')

        image_size = len(image_bytes)
        base64_size = len(base64_image)
        debug_print(f"[VISION_ANALYSIS] Image conversion for {document_id}:")
        debug_print(f"  Image path: {image_path}")
        debug_print(f"  Original size: {image_size:,} bytes ({image_size / 1024 / 1024:.2f} MB)")
        debug_print(f"  Base64 size: {base64_size:,} characters")

        # Determine image mime type
        mime_type = mimetypes.guess_type(image_path)[0] or 'image/jpeg'
        debug_print(f"  MIME type: {mime_type}")

        # Get vision model settings
        vision_model = settings.get('multimodal_vision_model', 'gpt-4o')
        debug_print(f"[VISION_ANALYSIS] Vision model selected: {vision_model}")

        if not vision_model:
            debug_print(f"Warning: Multi-modal vision enabled but no model selected")
            return None

        # Initialize client (reuse GPT configuration)
        enable_gpt_apim = settings.get('enable_gpt_apim', False)
        debug_print(f"[VISION_ANALYSIS] Using APIM: {enable_gpt_apim}")

        if enable_gpt_apim:
            api_version = settings.get('azure_apim_gpt_api_version')
            endpoint = settings.get('azure_apim_gpt_endpoint')
            debug_print(f"[VISION_ANALYSIS] APIM Configuration:")
            debug_print(f"  Endpoint: {endpoint}")
            debug_print(f"  API Version: {api_version}")

            gpt_client = AzureOpenAI(
                api_version=api_version,
                azure_endpoint=endpoint,
                api_key=settings.get('azure_apim_gpt_subscription_key')
            )
        else:
            # Use managed identity or key
            auth_type = settings.get('azure_openai_gpt_authentication_type', 'key')
            api_version = settings.get('azure_openai_gpt_api_version')
            endpoint = settings.get('azure_openai_gpt_endpoint')

            debug_print(f"[VISION_ANALYSIS] Direct Azure OpenAI Configuration:")
            debug_print(f"  Endpoint: {endpoint}")
            debug_print(f"  API Version: {api_version}")
            debug_print(f"  Auth Type: {auth_type}")

            if auth_type == 'managed_identity':
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(),
                    cognitive_services_scope
                )
                gpt_client = AzureOpenAI(
                    api_version=api_version,
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider
                )
            else:
                gpt_client = AzureOpenAI(
                    api_version=api_version,
                    azure_endpoint=endpoint,
                    api_key=settings.get('azure_openai_gpt_key')
                )

        # Create vision prompt
        debug_print(f"Analyzing image with vision model: {vision_model}")

        # Determine which token parameter to use based on model type
        # o-series and gpt-5 models require max_completion_tokens instead of max_tokens
        vision_model_lower = vision_model.lower()

        debug_print(f"[VISION_ANALYSIS] Building API request parameters:")
        debug_print(f"  Model (lowercase): {vision_model_lower}")

        # Check which parameter will be used
        uses_completion_tokens = ('o1' in vision_model_lower or 'o3' in vision_model_lower or 'gpt-5' in vision_model_lower)
        debug_print(f"  Uses max_completion_tokens: {uses_completion_tokens}")
        debug_print(f"  Detection: o1={('o1' in vision_model_lower)}, o3={('o3' in vision_model_lower)}, gpt-5={('gpt-5' in vision_model_lower)}")

        # Build prompt - GPT-5/reasoning models need explicit JSON instruction when using response_format
        if uses_completion_tokens:
            prompt_text = """Analyze this image and respond in JSON format with the following structure:
{
  "description": "A detailed description of what you see in the image",
  "objects": ["list", "of", "objects", "people", "or", "notable", "elements"],
  "text": "Any visible text extracted from the image (OCR)",
  "analysis": "Contextual analysis, insights, or interpretation"
}

Ensure your entire response is valid JSON. Include all four keys even if some are empty strings or empty arrays."""
        else:
            prompt_text = """Analyze this image and provide:
1. A detailed description of what you see
2. List any objects, people, or notable elements
3. Extract any visible text (OCR)
4. Provide contextual analysis or insights

Format your response as JSON with these keys:
{
  "description": "...",
  "objects": ["...", "..."],
  "text": "...",
  "analysis": "..."
}"""

        api_params = {
            "model": vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        }

        debug_print(f"[VISION_ANALYSIS_V2] ⚡ About to send request to Azure OpenAI with {vision_model}")
        debug_print(f"[VISION_ANALYSIS_V2] ⚡ Using parameter: {'max_completion_tokens' if uses_completion_tokens else 'max_tokens'} = 1000")
        debug_print(f"[VISION_ANALYSIS] Sending request to Azure OpenAI...")
        debug_print(f"  Message content types: text + image_url")
        debug_print(f"  Image data URL prefix: data:{mime_type};base64,... ({base64_size} chars)")

        response = gpt_client.chat.completions.create(**api_params)

        debug_print(f"[VISION_ANALYSIS_V2] ⚡ Response received successfully from {vision_model}")

        debug_print(f"[VISION_ANALYSIS] Response received from {vision_model}")
        debug_print(f"  Response ID: {response.id if hasattr(response, 'id') else 'N/A'}")
        debug_print(f"  Model used: {response.model if hasattr(response, 'model') else 'N/A'}")
        if hasattr(response, 'usage'):
            debug_print(f"  Token usage: prompt={response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 'N/A'}, completion={response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else 'N/A'}, total={response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 'N/A'}")

        # Debug the response structure to understand why content might be empty
        debug_print(f"[VISION_ANALYSIS] Response object inspection:")
        debug_print(f"  Response type: {type(response)}")
        debug_print(f"  Has choices: {hasattr(response, 'choices')}")
        if hasattr(response, 'choices') and len(response.choices) > 0:
            debug_print(f"  Number of choices: {len(response.choices)}")
            debug_print(f"  First choice type: {type(response.choices[0])}")
            debug_print(f"  Has message: {hasattr(response.choices[0], 'message')}")
            if hasattr(response.choices[0], 'message'):
                debug_print(f"  Message type: {type(response.choices[0].message)}")
                debug_print(f"  Message content type: {type(response.choices[0].message.content)}")
                debug_print(f"  Message content is None: {response.choices[0].message.content is None}")
                # Check for refusal
                if hasattr(response.choices[0].message, 'refusal'):
                    debug_print(f"  Message refusal: {response.choices[0].message.refusal}")
                # Check finish reason
                if hasattr(response.choices[0], 'finish_reason'):
                    debug_print(f"  Finish reason: {response.choices[0].finish_reason}")

        # Parse response
        content = response.choices[0].message.content

        # Handle None content
        if content is None:
            debug_print(f"[VISION_ANALYSIS_V2] ⚠️ Response content is None!")
            debug_print(f"[VISION_ANALYSIS] ⚠️ Content is None - checking for refusal or error")
            if hasattr(response.choices[0].message, 'refusal') and response.choices[0].message.refusal:
                error_msg = f"Model refused to respond: {response.choices[0].message.refusal}"
            else:
                error_msg = "Model returned empty content with no refusal message"

            return {
                'description': error_msg,
                'error': error_msg,
                'model': vision_model,
                'parse_failed': True
            }

        # Additional debugging for empty string case
        debug_print(f"[VISION_ANALYSIS_V2] ⚡ Content length: {len(content)}, repr: {repr(content[:200])}")
        debug_print(f"[VISION_ANALYSIS] Raw response received:")
        debug_print(f"  Length: {len(content)} characters")
        debug_print(f"  Content repr: {repr(content)}")
        debug_print(f"  First 500 chars: {content[:500]}...")
        debug_print(f"  Last 100 chars: ...{content[-100:] if len(content) > 100 else content}")

        # Check if response looks like JSON
        is_json_like = content.strip().startswith('{') or content.strip().startswith('[')
        has_code_fence = '```' in content
        debug_print(f"  Starts with JSON bracket: {is_json_like}")
        debug_print(f"  Contains code fence: {has_code_fence}")

        # Try to parse as JSON, fallback to raw text
        try:
            # Clean up potential markdown code fences
            debug_print(f"[VISION_ANALYSIS] Attempting to clean JSON code fences...")
            content_cleaned = clean_json_codeFence(content)
            debug_print(f"  Cleaned length: {len(content_cleaned)} characters")
            debug_print(f"  Cleaned first 200 chars: {content_cleaned[:200]}...")

            debug_print(f"[VISION_ANALYSIS] Attempting to parse as JSON...")
            vision_analysis = json.loads(content_cleaned)
            debug_print(f"[VISION_ANALYSIS] ✅ Successfully parsed JSON response!")
            debug_print(f"  JSON keys: {list(vision_analysis.keys())}")

        except Exception as parse_error:
            debug_print(f"[VISION_ANALYSIS] ❌ JSON parsing failed!")
            debug_print(f"  Error type: {type(parse_error).__name__}")
            debug_print(f"  Error message: {str(parse_error)}")
            debug_print(f"  Content that failed to parse (first 1000 chars): {content[:1000]}")
            debug_print(f"Vision response not valid JSON, using raw text")

            vision_analysis = {
                'description': content,
                'raw_response': content,
                'parse_error': str(parse_error),
                'parse_failed': True
            }
            debug_print(f"[VISION_ANALYSIS] Created fallback structure with raw response")

        # Add model info to analysis
        vision_analysis['model'] = vision_model

        debug_print(f"[VISION_ANALYSIS] Final analysis structure for {document_id}:")
        debug_print(f"  Model: {vision_model}")
        debug_print(f"  Has 'description': {'description' in vision_analysis}")
        debug_print(f"  Has 'objects': {'objects' in vision_analysis}")
        debug_print(f"  Has 'text': {'text' in vision_analysis}")
        debug_print(f"  Has 'analysis': {'analysis' in vision_analysis}")

        if 'description' in vision_analysis:
            desc = vision_analysis['description']
            debug_print(f"  Description length: {len(desc)} chars")
            debug_print(f"  Description preview: {desc[:200]}...")

        if 'objects' in vision_analysis:
            objs = vision_analysis['objects']
            debug_print(f"  Objects count: {len(objs) if isinstance(objs, list) else 'not a list'}")
            debug_print(f"  Objects: {objs}")

        if 'text' in vision_analysis:
            txt = vision_analysis['text']
            debug_print(f"  Text length: {len(txt) if txt else 0} chars")
            debug_print(f"  Text preview: {txt[:100] if txt else 'None'}...")

        debug_print(f"Vision analysis completed for document: {document_id}")
        return vision_analysis

    except Exception as e:
        debug_print(f"Error in vision analysis for {document_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
