# chunk_service.py
# Search index chunk operations — save, retrieve, update, and delete document chunks.

import traceback
from config import *
from functions_logging import *
from functions_debug import debug_print


def save_video_chunk(
    page_text_content,
    ocr_chunk_text,
    start_time,
    file_name,
    user_id,
    document_id,
    group_id
):
    """
    Saves one 30-second video chunk to the search index, with separate fields for transcript and OCR.
    Video Indexer insights (keywords, labels, topics, audio effects, emotions, sentiments) are
    already appended to page_text_content for searchability.
    The chunk_id is built from document_id and the integer second offset to ensure a valid key.
    """
    from functions_debug import debug_print

    debug_print(f"[VIDEO CHUNK] Saving video chunk for document: {document_id}, start_time: {start_time}")
    debug_print(f"[VIDEO CHUNK] Transcript length: {len(page_text_content)}, OCR length: {len(ocr_chunk_text)}")

    try:
        current_time = datetime.now(timezone.utc).isoformat()
        is_group = group_id is not None

        # Convert start_time "HH:MM:SS.mmm" to integer seconds
        h, m, s = start_time.split(':')
        seconds = int(h) * 3600 + int(m) * 60 + int(float(s))

        debug_print(f"[VIDEO CHUNK] Converted start_time {start_time} to {seconds} seconds")

        # 1) generate embedding on the transcript text
        try:
            debug_print(f"[VIDEO CHUNK] Generating embedding for transcript text")
            result = generate_embedding(page_text_content)

            # Handle both tuple (new) and single value (backward compatibility)
            if isinstance(result, tuple):
                embedding, _ = result  # Ignore token_usage for now
            else:
                embedding = result

            debug_print(f"[VIDEO CHUNK] Embedding generated successfully")
            debug_print(f"[VideoChunk] EMBEDDING OK for {document_id}@{start_time}", flush=True)
        except Exception as e:
            debug_print(f"[VIDEO CHUNK] Embedding generation failed: {str(e)}")
            debug_print(f"[VideoChunk] EMBEDDING ERROR for {document_id}@{start_time}: {e}", flush=True)
            return

        # 2) build chunk document
        try:
            debug_print(f"[VIDEO CHUNK] Retrieving document metadata")
            from services.document_service import get_document_metadata
            meta = get_document_metadata(document_id, user_id, group_id)
            version = meta.get("version", 1) if meta else 1
            debug_print(f"[VIDEO CHUNK] Document version: {version}")

            # Use integer seconds to build a safe document key
            chunk_id = f"{document_id}_{seconds}"
            debug_print(f"[VIDEO CHUNK] Generated chunk ID: {chunk_id}")

            chunk = {
                "id":                   chunk_id,
                "document_id":          document_id,
                "chunk_text":           page_text_content,
                "video_ocr_chunk_text": ocr_chunk_text,
                "embedding":            embedding,
                "file_name":            file_name,
                "start_time":           start_time,
                "chunk_sequence":       seconds,
                "upload_date":          current_time,
                "version":              version,
                "document_tags":        meta.get('tags', []) if meta else []
            }

            if is_group:
                chunk["group_id"] = group_id
                client = CLIENTS["search_client_group"]
                debug_print(f"[VIDEO CHUNK] Using group search client for group_id: {group_id}")
            else:
                # Get shared_user_ids from document metadata for personal documents
                shared_user_ids = meta.get('shared_user_ids', []) if meta else []
                chunk["user_id"] = user_id
                chunk["shared_user_ids"] = shared_user_ids
                client = CLIENTS["search_client_user"]
                debug_print(f"[VIDEO CHUNK] Using user search client for user_id: {user_id}, shared_user_ids: {shared_user_ids}")

            debug_print(f"[VIDEO CHUNK] Built chunk document with ID: {chunk_id}")
            debug_print(f"[VideoChunk] CHUNK BUILT {chunk_id}", flush=True)

        except Exception as e:
            debug_print(f"[VIDEO CHUNK] Error building chunk document: {str(e)}")
            debug_print(f"[VideoChunk] CHUNK BUILD ERROR for {document_id}@{start_time}: {e}", flush=True)
            return

        # 3) upload to search index
        try:
            debug_print(f"[VIDEO CHUNK] Uploading chunk to search index")
            client.upload_documents(documents=[chunk])
            debug_print(f"[VIDEO CHUNK] Upload successful for chunk: {chunk_id}")
            debug_print(f"[VideoChunk] UPLOAD OK for {chunk_id}", flush=True)
        except Exception as e:
            debug_print(f"[VIDEO CHUNK] Upload to search index failed: {str(e)}")
            debug_print(f"[VideoChunk] UPLOAD ERROR for {chunk_id}: {e}", flush=True)

    except Exception as e:
        debug_print(f"[VIDEO CHUNK] Unexpected error processing chunk: {str(e)}")
        debug_print(f"[VideoChunk] UNEXPECTED ERROR for {document_id}@{start_time}: {e}", flush=True)


def save_chunks(page_text_content, page_number, file_name, user_id, document_id, group_id=None, public_workspace_id=None):
    """
    Save a single chunk (one page) at a time:
      - Generate embedding
      - Build chunk metadata
      - Upload to Search index
    """
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Choose the correct cosmos_container and query parameters
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    try:
        # Update document status
        #num_chunks = 1  # because we only have one chunk (page) here
        #status = f"Processing 1 chunk (page {page_number})"
        #update_document(document_id=document_id, user_id=user_id, status=status)

        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
            content=f"Saving chunk, cosmos_container:{cosmos_container}, page_text_content:{page_text_content}, page_number:{page_number}, file_name:{file_name}, user_id:{user_id}, document_id:{document_id}, group_id:{group_id}, public_workspace_id:{public_workspace_id}"
        )

        from services.document_service import get_document_metadata

        if is_public_workspace:
            metadata = get_document_metadata(
                document_id=document_id,
                user_id=user_id,
                public_workspace_id=public_workspace_id
            )
        elif is_group:
            metadata = get_document_metadata(
                document_id=document_id,
                user_id=user_id,
                group_id=group_id
            )
        else:
            metadata = get_document_metadata(
                document_id=document_id,
                user_id=user_id
            )

        if not metadata:
            raise ValueError(f"No metadata found for document {document_id} (group: {is_group})")

        version = metadata.get("version") if metadata.get("version") else 1
        if version is None:
            raise ValueError(f"Metadata for document {document_id} missing 'version' field")

    except Exception as e:
        debug_print(f"Error updating document status or retrieving metadata for document {document_id}: {repr(e)}\nTraceback:\n{traceback.format_exc()}")
        raise

    # Generate embedding
    try:
        #status = f"Generating embedding for page {page_number}"
        #update_document(document_id=document_id, user_id=user_id, status=status)
        embedding, token_usage = generate_embedding(page_text_content)
    except Exception as e:
        debug_print(f"Error generating embedding for page {page_number} of document {document_id}: {e}")
        raise

    # Build chunk document
    try:
        chunk_id = f"{document_id}_{page_number}"
        chunk_keywords = []
        chunk_summary = ""
        author = []
        title = ""

        # Check if this document has vision analysis and append it to chunk_text
        vision_analysis = metadata.get('vision_analysis')
        enhanced_chunk_text = page_text_content

        if vision_analysis:
            debug_print(f"[SAVE_CHUNKS] Document {document_id} has vision analysis, appending to chunk_text")
            # Format vision analysis as structured text for better searchability
            vision_text_parts = []
            vision_text_parts.append("\n\n=== AI Vision Analysis ===")
            vision_text_parts.append(f"Model: {vision_analysis.get('model', 'unknown')}")

            if vision_analysis.get('description'):
                vision_text_parts.append(f"\nDescription: {vision_analysis['description']}")

            if vision_analysis.get('objects'):
                objects_list = vision_analysis['objects']
                if isinstance(objects_list, list):
                    vision_text_parts.append(f"\nObjects Detected: {', '.join(objects_list)}")
                else:
                    vision_text_parts.append(f"\nObjects Detected: {objects_list}")

            if vision_analysis.get('text'):
                vision_text_parts.append(f"\nVisible Text: {vision_analysis['text']}")

            if vision_analysis.get('analysis'):
                vision_text_parts.append(f"\nContextual Analysis: {vision_analysis['analysis']}")

            vision_text = "\n".join(vision_text_parts)
            enhanced_chunk_text = page_text_content + vision_text

            debug_print(f"[SAVE_CHUNKS] Enhanced chunk_text length: {len(enhanced_chunk_text)} (original: {len(page_text_content)}, vision: {len(vision_text)})")
        else:
            debug_print(f"[SAVE_CHUNKS] No vision analysis found for document {document_id}")

        # Web ingestion metadata (Phase 2: Advanced RAG)
        source_url = metadata.get('source_url', '') if metadata else ''
        source_type = metadata.get('source_type', 'file') if metadata else 'file'
        content_hash = metadata.get('content_hash', '') if metadata else ''

        if is_public_workspace:
            chunk_document = {
                "id": chunk_id,
                "document_id": document_id,
                "chunk_id": str(page_number),
                "chunk_text": enhanced_chunk_text,
                "embedding": embedding,
                "file_name": file_name,
                "chunk_keywords": chunk_keywords,
                "chunk_summary": chunk_summary,
                "page_number": page_number,
                "author": author,
                "title": title,
                "document_classification": "None",
                "document_tags": metadata.get('tags', []),
                "chunk_sequence": page_number,  # or you can keep an incremental idx
                "upload_date": current_time,
                "version": version,
                "public_workspace_id": public_workspace_id,
                "source_url": source_url,
                "source_type": source_type,
                "content_hash": content_hash,
            }
        elif is_group:
            # Get shared_group_ids from document metadata for group documents
            shared_group_ids = metadata.get('shared_group_ids', []) if metadata else []
            chunk_document = {
                "id": chunk_id,
                "document_id": document_id,
                "chunk_id": str(page_number),
                "chunk_text": enhanced_chunk_text,
                "embedding": embedding,
                "file_name": file_name,
                "chunk_keywords": chunk_keywords,
                "chunk_summary": chunk_summary,
                "page_number": page_number,
                "author": author,
                "title": title,
                "document_classification": "None",
                "document_tags": metadata.get('tags', []),
                "chunk_sequence": page_number,  # or you can keep an incremental idx
                "upload_date": current_time,
                "version": version,
                "group_id": group_id,
                "shared_group_ids": shared_group_ids,
                "source_url": source_url,
                "source_type": source_type,
                "content_hash": content_hash,
            }
        else:
            # Get shared_user_ids from document metadata for personal documents
            shared_user_ids = metadata.get('shared_user_ids', []) if metadata else []

            chunk_document = {
                "id": chunk_id,
                "document_id": document_id,
                "chunk_id": str(page_number),
                "chunk_text": enhanced_chunk_text,
                "embedding": embedding,
                "file_name": file_name,
                "chunk_keywords": chunk_keywords,
                "chunk_summary": chunk_summary,
                "page_number": page_number,
                "author": author,
                "title": title,
                "document_classification": "None",
                "document_tags": metadata.get('tags', []),
                "chunk_sequence": page_number,  # or you can keep an incremental idx
                "upload_date": current_time,
                "version": version,
                "user_id": user_id,
                "shared_user_ids": shared_user_ids,
                "source_url": source_url,
                "source_type": source_type,
                "content_hash": content_hash,
            }
    except Exception as e:
        debug_print(f"Error creating chunk document for page {page_number} of document {document_id}: {e}")
        raise

    # Upload chunk document to Search
    try:
        #status = f"Uploading page {page_number} of document {document_id} to index."
        #update_document(document_id=document_id, user_id=user_id, status=status)

        if is_public_workspace:
            search_client = CLIENTS["search_client_public"]
        elif is_group:
            search_client = CLIENTS["search_client_group"]
        else:
            search_client = CLIENTS["search_client_user"]
        # Upload as a single-document list
        search_client.upload_documents(documents=[chunk_document])

    except Exception as e:
        debug_print(f"Error uploading chunk document for document {document_id}: {e}")
        raise

    # Return token usage information for accumulation
    return token_usage


def get_document_metadata_for_citations(document_id, user_id=None, group_id=None, public_workspace_id=None):
    """
    Retrieve keywords and abstract from a document for creating metadata citations.
    Used to enhance search results with additional context from document metadata.

    Args:
        document_id: The document's unique identifier
        user_id: User ID (for personal documents)
        group_id: Group ID (for group documents)
        public_workspace_id: Public workspace ID (for public documents)

    Returns:
        dict: Dictionary with 'keywords' and 'abstract' fields, or None if document not found
    """
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Determine the correct container
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    try:
        # Read the document directly by ID
        document_item = cosmos_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Extract keywords and abstract
        keywords = document_item.get('keywords', [])
        abstract = document_item.get('abstract', '')

        # Return only if we have actual content
        if keywords or abstract:
            return {
                'keywords': keywords if keywords else [],
                'abstract': abstract if abstract else '',
                'file_name': document_item.get('file_name', 'Unknown')
            }

        return None

    except Exception as e:
        # Document not found or error reading - return None silently
        # This is expected for documents without metadata
        return None


def get_batch_document_metadata_for_citations(doc_requests):
    """
    Batch retrieve keywords and abstract for multiple documents.
    Groups requests by container type to minimize cross-partition queries.

    Args:
        doc_requests: list of dicts with keys:
            - document_id (str)
            - user_id (str, optional)
            - group_id (str, optional)
            - public_workspace_id (str, optional)

    Returns:
        dict: Mapping of document_id -> metadata dict (or None if not found).
    """
    results = {}
    if not doc_requests:
        return results

    # Group by container type for efficient batch reads
    by_container = {
        'user': [],
        'group': [],
        'public': [],
    }
    for req in doc_requests:
        doc_id = req.get('document_id')
        if not doc_id:
            continue
        if req.get('public_workspace_id'):
            by_container['public'].append(doc_id)
        elif req.get('group_id'):
            by_container['group'].append(doc_id)
        else:
            by_container['user'].append(doc_id)

    container_map = {
        'user': cosmos_user_documents_container,
        'group': cosmos_group_documents_container,
        'public': cosmos_public_documents_container,
    }

    for container_type, doc_ids in by_container.items():
        if not doc_ids:
            continue
        cosmos_container = container_map[container_type]
        for doc_id in doc_ids:
            try:
                document_item = cosmos_container.read_item(
                    item=doc_id,
                    partition_key=doc_id
                )
                keywords = document_item.get('keywords', [])
                abstract = document_item.get('abstract', '')
                if keywords or abstract:
                    results[doc_id] = {
                        'keywords': keywords if keywords else [],
                        'abstract': abstract if abstract else '',
                        'file_name': document_item.get('file_name', 'Unknown')
                    }
                else:
                    results[doc_id] = None
            except Exception:
                results[doc_id] = None

    return results


def get_all_chunks(document_id, user_id, group_id=None, public_workspace_id=None):
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # For personal documents, first check if user has access (owner or shared)
    if not is_group and not is_public_workspace:
        # Check if user has access to this document
        from services.sharing_service import is_document_shared_with_user
        if not is_document_shared_with_user(document_id, user_id):
            debug_print(f"User {user_id} does not have access to document {document_id}")
            return []
    elif is_group:
        # For group documents, check if group has access (owner or shared)
        from services.sharing_service import is_document_shared_with_group
        if not is_document_shared_with_group(document_id, group_id):
            debug_print(f"Group {group_id} does not have access to document {document_id}")
            return []

    search_client = CLIENTS["search_client_public"] if is_public_workspace else CLIENTS["search_client_group"] if is_group else CLIENTS["search_client_user"]
    filter_expr = (
        f"document_id eq '{document_id}' and public_workspace_id eq '{public_workspace_id}'"
        if is_public_workspace else
        f"document_id eq '{document_id}' and (group_id eq '{group_id}' or shared_group_ids/any(g: g eq '{group_id}'))"
        if is_group else
        f"document_id eq '{document_id}'"  # For personal documents, just filter by document_id since access is already verified
    )

    select_fields = [
        "id",
        "chunk_text",
        "chunk_id",
        "file_name",
        "public_workspace_id" if is_public_workspace else ("group_id" if is_group else "user_id"),
        "version",
        "chunk_sequence",
        "upload_date"
    ]

    try:
        results = search_client.search(
            search_text="*",
            filter=filter_expr,
            select=",".join(select_fields)
        )
        return results

    except Exception as e:
        debug_print(f"Error retrieving chunks for document {document_id}: {e}")
        raise


def update_chunk_metadata(chunk_id, user_id, group_id=None, public_workspace_id=None, document_id=None, **kwargs):
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    try:
        search_client = CLIENTS["search_client_public"] if is_public_workspace else CLIENTS["search_client_group"] if is_group else CLIENTS["search_client_user"]
        chunk_item = search_client.get_document(key=chunk_id)

        if not chunk_item:
            raise Exception("Chunk not found")

        if is_public_workspace:
            if chunk_item.get('public_workspace_id') != public_workspace_id:
                raise Exception("Unauthorized access to chunk")
        elif is_group:
            if chunk_item.get('group_id') != group_id:
                raise Exception("Unauthorized access to chunk")
        else:
            if chunk_item.get('user_id') != user_id:
                raise Exception("Unauthorized access to chunk")

        if chunk_item.get('document_id') != document_id:
            raise Exception("Chunk does not belong to document")

        # Update only supported fields based on workspace type
        # Personal workspace documents don't have shared_group_ids in search index
        updatable_fields = [
            'chunk_keywords',
            'chunk_summary',
            'author',
            'title',
            'document_classification',
            'document_tags',
            'shared_user_ids'
        ]

        # Only include shared_group_ids for group workspaces where it exists in the schema
        if is_group:
            updatable_fields.append('shared_group_ids')

        for field in updatable_fields:
            if field in kwargs:
                chunk_item[field] = kwargs[field]

        search_client.upload_documents(documents=[chunk_item])

    except Exception as e:
        debug_print(f"Error updating chunk metadata for chunk {chunk_id}: {e}")
        raise


def get_pdf_page_count(pdf_path: str) -> int:
    """
    Returns the total number of pages in the given PDF using PyMuPDF.
    """
    import fitz  # Lazy import — heavy library only needed for PDF operations
    try:
        with fitz.open(pdf_path) as doc:
            return doc.page_count
    except Exception as e:
        debug_print(f"Error reading PDF page count: {e}")
        return 0


def chunk_pdf(input_pdf_path: str, max_pages: int = 500) -> list:
    """
    Splits a PDF into multiple PDFs, each with up to `max_pages` pages,
    using PyMuPDF. Returns a list of file paths for the newly created chunks.
    """
    import fitz  # Lazy import — heavy library only needed for PDF operations
    chunks = []
    try:
        with fitz.open(input_pdf_path) as doc:
            total_pages = doc.page_count
            current_page = 0
            chunk_index = 1

            base_name, ext = os.path.splitext(input_pdf_path)

            # Loop through the PDF in increments of `max_pages`
            while current_page < total_pages:
                end_page = min(current_page + max_pages, total_pages)

                # Create a new, empty document for this chunk
                chunk_doc = fitz.open()

                # Insert the range of pages in one go
                chunk_doc.insert_pdf(doc, from_page=current_page, to_page=end_page - 1)

                chunk_pdf_path = f"{base_name}_chunk_{chunk_index}{ext}"
                chunk_doc.save(chunk_pdf_path)
                chunk_doc.close()

                chunks.append(chunk_pdf_path)

                current_page = end_page
                chunk_index += 1

    except Exception as e:
        debug_print(f"Error chunking PDF: {e}")

    return chunks


def delete_document_chunks(document_id, group_id=None, public_workspace_id=None):
    """Delete document chunks from Azure Cognitive Search index."""

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    try:
        search_client = CLIENTS["search_client_public"] if is_public_workspace else CLIENTS["search_client_group"] if is_group else CLIENTS["search_client_user"]
        results = search_client.search(
            search_text="*",
            filter=f"document_id eq '{sanitize_odata_value(document_id)}'",
            select=["id"]
        )

        ids_to_delete = [doc['id'] for doc in results]

        if not ids_to_delete:
            return

        documents_to_delete = [{"id": doc_id} for doc_id in ids_to_delete]
        batch = IndexDocumentsBatch()
        batch.add_delete_actions(documents_to_delete)
        result = search_client.index_documents(batch)
    except Exception as e:
        raise


def delete_document_version_chunks(document_id, version, group_id=None, public_workspace_id=None):
    """Delete document chunks from Azure Cognitive Search index for a specific version."""
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    search_client = CLIENTS["search_client_public"] if is_public_workspace else CLIENTS["search_client_group"] if is_group else CLIENTS["search_client_user"]

    search_client.delete_documents(
        actions=[
            {"@search.action": "delete", "id": chunk['id']} for chunk in
            search_client.search(
                search_text="*",
                filter=f"document_id eq '{sanitize_odata_value(document_id)}' and version eq {int(version)}",
                select="id"
            )
        ]
    )