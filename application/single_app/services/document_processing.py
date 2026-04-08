# document_processing.py
# Document format processors and main upload dispatcher.

from config import *
from functions_settings import get_settings
from functions_debug import debug_print


def process_txt(document_id, user_id, temp_file_path, original_filename, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes plain text files."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status="Processing TXT file...")
    total_chunks_saved = 0
    total_embedding_tokens = 0
    embedding_model_name = None
    target_words_per_chunk = 400

    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        upload_to_blob(**args)

    try:
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        words = content.split()
        num_words = len(words)
        num_chunks_estimated = math.ceil(num_words / target_words_per_chunk)
        update_callback(number_of_pages=num_chunks_estimated) # Use number_of_pages for chunk count

        for i in range(0, num_words, target_words_per_chunk):
            chunk_words = words[i : i + target_words_per_chunk]
            chunk_content = " ".join(chunk_words)
            chunk_index = (i // target_words_per_chunk) + 1

            if chunk_content.strip():
                update_callback(
                    current_file_chunk=chunk_index,
                    status=f"Saving chunk {chunk_index}/{num_chunks_estimated}..."
                )
                args = {
                    "page_text_content": chunk_content,
                    "page_number": chunk_index,
                    "file_name": original_filename,
                    "user_id": user_id,
                    "document_id": document_id
                }

                if is_public_workspace:
                    args["public_workspace_id"] = public_workspace_id
                elif is_group:
                    args["group_id"] = group_id

                token_usage = save_chunks(**args)
                total_chunks_saved += 1

                # Accumulate embedding tokens
                if token_usage:
                    total_embedding_tokens += token_usage.get('total_tokens', 0)
                    if not embedding_model_name:
                        embedding_model_name = token_usage.get('model_deployment_name')

    except Exception as e:
        raise Exception(f"Failed processing TXT file {original_filename}: {e}")

    return total_chunks_saved, total_embedding_tokens, embedding_model_name


def process_xml(document_id, user_id, temp_file_path, original_filename, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes XML files using RecursiveCharacterTextSplitter for structured content."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status="Processing XML file...")
    total_chunks_saved = 0
    # Character-based chunking for XML structure preservation
    max_chunk_size_chars = 4000

    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }

        if is_group:
            args["group_id"] = group_id
        elif is_public_workspace:
            args["public_workspace_id"] = public_workspace_id

        upload_to_blob(**args)

    try:
        # Read XML content
        try:
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
        except Exception as e:
            raise Exception(f"Error reading XML file {original_filename}: {e}")

        # Use RecursiveCharacterTextSplitter with XML-aware separators
        # This preserves XML structure better than simple word splitting
        xml_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size_chars,
            chunk_overlap=0,
            length_function=len,
            separators=["\n\n", "\n", ">", " ", ""],  # XML-friendly separators
            is_separator_regex=False
        )

        # Split the XML content
        final_chunks = xml_splitter.split_text(xml_content)

        initial_chunk_count = len(final_chunks)
        update_callback(number_of_pages=initial_chunk_count)

        for idx, chunk_content in enumerate(final_chunks, start=1):
            # Skip empty chunks
            if not chunk_content or not chunk_content.strip():
                debug_print(f"Skipping empty XML chunk {idx}/{initial_chunk_count}")
                continue

            update_callback(
                current_file_chunk=idx,
                status=f"Saving chunk {idx}/{initial_chunk_count}..."
            )
            args = {
                "page_text_content": chunk_content,
                "page_number": total_chunks_saved + 1,
                "file_name": original_filename,
                "user_id": user_id,
                "document_id": document_id
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            save_chunks(**args)
            total_chunks_saved += 1

        # Final update with actual chunks saved
        if total_chunks_saved != initial_chunk_count:
            update_callback(number_of_pages=total_chunks_saved)
            debug_print(f"Adjusted final chunk count from {initial_chunk_count} to {total_chunks_saved} after skipping empty chunks.")

    except Exception as e:
        debug_print(f"Error during XML processing for {original_filename}: {type(e).__name__}: {e}")
        raise Exception(f"Failed processing XML file {original_filename}: {e}")

    return total_chunks_saved


def process_yaml(document_id, user_id, temp_file_path, original_filename, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes YAML files using RecursiveCharacterTextSplitter for structured content."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status="Processing YAML file...")
    total_chunks_saved = 0
    # Character-based chunking for YAML structure preservation
    max_chunk_size_chars = 4000

    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        upload_to_blob(**args)

    try:
        # Read YAML content
        try:
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()
        except Exception as e:
            raise Exception(f"Error reading YAML file {original_filename}: {e}")

        # Use RecursiveCharacterTextSplitter with YAML-aware separators
        # This preserves YAML structure better than simple word splitting
        yaml_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size_chars,
            chunk_overlap=0,
            length_function=len,
            separators=["\n\n", "\n", "- ", " ", ""],  # YAML-friendly separators
            is_separator_regex=False
        )

        # Split the YAML content
        final_chunks = yaml_splitter.split_text(yaml_content)

        initial_chunk_count = len(final_chunks)
        update_callback(number_of_pages=initial_chunk_count)

        for idx, chunk_content in enumerate(final_chunks, start=1):
            # Skip empty chunks
            if not chunk_content or not chunk_content.strip():
                debug_print(f"Skipping empty YAML chunk {idx}/{initial_chunk_count}")
                continue

            update_callback(
                current_file_chunk=idx,
                status=f"Saving chunk {idx}/{initial_chunk_count}..."
            )
            args = {
                "page_text_content": chunk_content,
                "page_number": total_chunks_saved + 1,
                "file_name": original_filename,
                "user_id": user_id,
                "document_id": document_id
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            save_chunks(**args)
            total_chunks_saved += 1

        # Final update with actual chunks saved
        if total_chunks_saved != initial_chunk_count:
            update_callback(number_of_pages=total_chunks_saved)
            debug_print(f"Adjusted final chunk count from {initial_chunk_count} to {total_chunks_saved} after skipping empty chunks.")

    except Exception as e:
        debug_print(f"Error during YAML processing for {original_filename}: {type(e).__name__}: {e}")
        raise Exception(f"Failed processing YAML file {original_filename}: {e}")

    return total_chunks_saved


def process_log(document_id, user_id, temp_file_path, original_filename, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes LOG files using line-based chunking to maintain log record integrity."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status="Processing LOG file...")
    total_chunks_saved = 0
    target_words_per_chunk = 1000  # Word-based chunking for better semantic grouping

    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        upload_to_blob(**args)

    try:
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split by lines to maintain log record integrity
        lines = content.splitlines(keepends=True)  # Keep line endings

        if not lines:
            raise Exception(f"LOG file {original_filename} is empty")

        # Chunk by accumulating lines until reaching target word count
        final_chunks = []
        current_chunk_lines = []
        current_chunk_word_count = 0

        for line in lines:
            line_word_count = len(line.split())

            # If adding this line exceeds target AND we already have content
            if current_chunk_word_count + line_word_count > target_words_per_chunk and current_chunk_lines:
                # Finalize current chunk
                final_chunks.append("".join(current_chunk_lines))
                # Start new chunk with current line
                current_chunk_lines = [line]
                current_chunk_word_count = line_word_count
            else:
                # Add line to current chunk
                current_chunk_lines.append(line)
                current_chunk_word_count += line_word_count

        # Add the last remaining chunk if it has content
        if current_chunk_lines:
            final_chunks.append("".join(current_chunk_lines))

        num_chunks = len(final_chunks)
        update_callback(number_of_pages=num_chunks)

        for idx, chunk_content in enumerate(final_chunks, start=1):
            if chunk_content.strip():
                update_callback(
                    current_file_chunk=idx,
                    status=f"Saving chunk {idx}/{num_chunks}..."
                )
                args = {
                    "page_text_content": chunk_content,
                    "page_number": idx,
                    "file_name": original_filename,
                    "user_id": user_id,
                    "document_id": document_id
                }

                if is_public_workspace:
                    args["public_workspace_id"] = public_workspace_id
                elif is_group:
                    args["group_id"] = group_id

                save_chunks(**args)
                total_chunks_saved += 1

    except Exception as e:
        raise Exception(f"Failed processing LOG file {original_filename}: {e}")

    return total_chunks_saved


def process_doc(document_id, user_id, temp_file_path, original_filename, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """
    Processes .doc and .docm files using docx2txt library.
    Note: .docx files still use Document Intelligence for better formatting preservation.
    """
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status=f"Processing {original_filename.split('.')[-1].upper()} file...")
    total_chunks_saved = 0
    target_words_per_chunk = 400  # Consistent with other text-based chunking

    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        upload_to_blob(**args)

    try:
        # Import docx2txt here to avoid dependency issues if not installed
        try:
            import docx2txt
        except ImportError:
            raise Exception("docx2txt library is required for .doc and .docm file processing. Install with: pip install docx2txt")

        # Extract text from .doc or .docm file
        try:
            text_content = docx2txt.process(temp_file_path)
        except Exception as e:
            raise Exception(f"Error extracting text from {original_filename}: {e}")

        if not text_content or not text_content.strip():
            raise Exception(f"No text content extracted from {original_filename}")

        # Split into words for chunking
        words = text_content.split()
        if not words:
            raise Exception(f"No text content found in {original_filename}")

        # Create chunks of target_words_per_chunk words
        final_chunks = []
        for i in range(0, len(words), target_words_per_chunk):
            chunk_words = words[i:i + target_words_per_chunk]
            chunk_text = " ".join(chunk_words)
            final_chunks.append(chunk_text)

        num_chunks = len(final_chunks)
        update_callback(number_of_pages=num_chunks)

        for idx, chunk_content in enumerate(final_chunks, start=1):
            if chunk_content.strip():
                update_callback(
                    current_file_chunk=idx,
                    status=f"Saving chunk {idx}/{num_chunks}..."
                )
                args = {
                    "page_text_content": chunk_content,
                    "page_number": idx,
                    "file_name": original_filename,
                    "user_id": user_id,
                    "document_id": document_id
                }

                if is_public_workspace:
                    args["public_workspace_id"] = public_workspace_id
                elif is_group:
                    args["group_id"] = group_id

                save_chunks(**args)
                total_chunks_saved += 1

    except Exception as e:
        raise Exception(f"Failed processing {original_filename}: {e}")

    return total_chunks_saved


def process_html(document_id, user_id, temp_file_path, original_filename, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes HTML files."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks
    from services.metadata_service import extract_document_metadata, estimate_word_count
    from bs4 import BeautifulSoup
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status="Processing HTML file...")
    total_chunks_saved = 0
    total_embedding_tokens = 0
    embedding_model_name = None
    target_chunk_words = 1200 # Target size based on requirement
    min_chunk_words = 600 # Minimum size based on requirement

    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }
        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        upload_to_blob(**args)

    try:
        # --- CHANGE HERE: Open in binary mode ('rb') ---
        # Let BeautifulSoup handle the decoding based on meta tags or detection
        with open(temp_file_path, 'rb') as f:
            # --- CHANGE HERE: Pass the file object directly to BeautifulSoup ---
            soup = BeautifulSoup(f, 'lxml') # or 'html.parser' if lxml not installed

        # TODO: Advanced Table Handling - (Comment remains valid)
        # ...

        # Now process the soup object as before
        text_content = soup.get_text(separator=" ", strip=True)

        # Remainder of the chunking logic stays the same...
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=target_chunk_words * 6, # Approximation
            chunk_overlap=target_chunk_words * 0.1 * 6, # 10% overlap approx
            length_function=len,
            is_separator_regex=False,
        )

        initial_chunks = text_splitter.split_text(text_content)

        # Post-processing: Merge small chunks
        final_chunks = []
        buffer_chunk = ""
        for i, chunk in enumerate(initial_chunks):
            current_chunk_text = buffer_chunk + chunk
            current_word_count = estimate_word_count(current_chunk_text)

            if current_word_count >= min_chunk_words or i == len(initial_chunks) - 1:
                if current_chunk_text.strip():
                    final_chunks.append(current_chunk_text)
                buffer_chunk = "" # Reset buffer
            else:
                # Chunk is too small, add to buffer and continue to next chunk
                buffer_chunk = current_chunk_text + " " # Add space between merged chunks

        num_chunks_final = len(final_chunks)
        update_callback(number_of_pages=num_chunks_final) # Use number_of_pages for chunk count

        for idx, chunk_content in enumerate(final_chunks, start=1):
            update_callback(
                current_file_chunk=idx,
                status=f"Saving chunk {idx}/{num_chunks_final}..."
            )
            args = {
                "page_text_content": chunk_content,
                "page_number": idx,
                "file_name": original_filename,
                "user_id": user_id,
                "document_id": document_id
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            token_usage = save_chunks(**args)
            total_chunks_saved += 1

            # Accumulate embedding tokens
            if token_usage:
                total_embedding_tokens += token_usage.get('total_tokens', 0)
                if not embedding_model_name:
                    embedding_model_name = token_usage.get('model_deployment_name')

    except Exception as e:
        # Catch potential BeautifulSoup errors too
        raise Exception(f"Failed processing HTML file {original_filename}: {e}")

    # Extract metadata if enabled and chunks were processed
    settings = get_settings()
    enable_extract_meta_data = settings.get('enable_extract_meta_data', False)
    if enable_extract_meta_data and total_chunks_saved > 0:
        try:
            update_callback(status="Extracting final metadata...")
            args = {
                "document_id": document_id,
                "user_id": user_id
            }

            if public_workspace_id:
                args["public_workspace_id"] = public_workspace_id
            elif group_id:
                args["group_id"] = group_id

            document_metadata = extract_document_metadata(**args)

            if document_metadata:
                update_fields = {k: v for k, v in document_metadata.items() if v is not None and v != ""}
                if update_fields:
                    update_fields['status'] = "Final metadata extracted"
                    update_callback(**update_fields)
                else:
                    update_callback(status="Final metadata extraction yielded no new info")
        except Exception as e:
            debug_print(f"Warning: Error extracting final metadata for HTML document {document_id}: {str(e)}")
            update_callback(status=f"Processing complete (metadata extraction warning)")

    return total_chunks_saved, total_embedding_tokens, embedding_model_name


def process_md(document_id, user_id, temp_file_path, original_filename, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes Markdown files."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks
    from services.metadata_service import extract_document_metadata, estimate_word_count
    from langchain_text_splitters import MarkdownHeaderTextSplitter

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status="Processing Markdown file...")
    total_chunks_saved = 0
    total_embedding_tokens = 0
    embedding_model_name = None
    target_chunk_words = 1200 # Target size based on requirement
    min_chunk_words = 600 # Minimum size based on requirement

    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }

        if is_group:
            args["group_id"] = group_id
        elif is_public_workspace:
            args["public_workspace_id"] = public_workspace_id

        upload_to_blob(**args)

    try:
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
            ("#####", "Header 5"),
        ]

        # Use MarkdownHeaderTextSplitter first
        md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, return_each_line=False)
        md_header_splits = md_splitter.split_text(md_content)

        initial_chunks_content = [doc.page_content for doc in md_header_splits]

        # TODO: Advanced Table/Code Block Handling:
        # - Table header replication requires identifying markdown tables (`|---|`),
        #   detecting splits, and injecting headers.
        # - Code block wrapping requires detecting ``` blocks split across chunks and
        #   adding start/end fences.
        # This requires complex regex or stateful parsing during/after splitting.
        # For now, we focus on the text splitting and minimum size merging.

        # Post-processing: Merge small chunks based on word count
        final_chunks = []
        buffer_chunk = ""
        for i, chunk_text in enumerate(initial_chunks_content):
            current_chunk_text = buffer_chunk + chunk_text # Combine with buffer first
            current_word_count = estimate_word_count(current_chunk_text)

            # Merge if current chunk alone (without buffer) is too small, UNLESS it's the last one
            # Or, more simply, accumulate until the buffer meets the minimum size
            if current_word_count >= min_chunk_words or i == len(initial_chunks_content) - 1:
                 # If the combined chunk meets min size OR it's the last chunk, save it
                if current_chunk_text.strip():
                     final_chunks.append(current_chunk_text)
                buffer_chunk = "" # Reset buffer
            else:
                # Accumulate in buffer if below min size and not the last chunk
                buffer_chunk = current_chunk_text + "\n\n" # Add separator when buffering

        num_chunks_final = len(final_chunks)
        update_callback(number_of_pages=num_chunks_final)

        for idx, chunk_content in enumerate(final_chunks, start=1):
            update_callback(
                current_file_chunk=idx,
                status=f"Saving chunk {idx}/{num_chunks_final}..."
            )
            args = {
                "page_text_content": chunk_content,
                "page_number": idx,
                "file_name": original_filename,
                "user_id": user_id,
                "document_id": document_id
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            token_usage = save_chunks(**args)
            total_chunks_saved += 1

            # Accumulate embedding tokens
            if token_usage:
                total_embedding_tokens += token_usage.get('total_tokens', 0)
                if not embedding_model_name:
                    embedding_model_name = token_usage.get('model_deployment_name')

    except Exception as e:
        raise Exception(f"Failed processing Markdown file {original_filename}: {e}")

    # Extract metadata if enabled and chunks were processed
    settings = get_settings()
    enable_extract_meta_data = settings.get('enable_extract_meta_data', False)
    if enable_extract_meta_data and total_chunks_saved > 0:
        try:
            update_callback(status="Extracting final metadata...")
            args = {
                "document_id": document_id,
                "user_id": user_id
            }

            if public_workspace_id:
                args["public_workspace_id"] = public_workspace_id
            elif group_id:
                args["group_id"] = group_id

            document_metadata = extract_document_metadata(**args)

            if document_metadata:
                update_fields = {k: v for k, v in document_metadata.items() if v is not None and v != ""}
                if update_fields:
                    update_fields['status'] = "Final metadata extracted"
                    update_callback(**update_fields)
                else:
                    update_callback(status="Final metadata extraction yielded no new info")
        except Exception as e:
            debug_print(f"Warning: Error extracting final metadata for Markdown document {document_id}: {str(e)}")
            update_callback(status=f"Processing complete (metadata extraction warning)")

    return total_chunks_saved, total_embedding_tokens, embedding_model_name


def process_json(document_id, user_id, temp_file_path, original_filename, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes JSON files using RecursiveJsonSplitter."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks
    from services.metadata_service import extract_document_metadata
    from langchain_text_splitters import RecursiveJsonSplitter

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status="Processing JSON file...")
    total_chunks_saved = 0
    total_embedding_tokens = 0
    embedding_model_name = None
    # Reflects character count limit for the splitter
    max_chunk_size_chars = 4000 # As per original requirement

    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }

        if is_group:
            args["group_id"] = group_id
        elif is_public_workspace:
            args["public_workspace_id"] = public_workspace_id

        upload_to_blob(**args)


    try:
        # Load the JSON data first to ensure it's valid
        try:
            with open(temp_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except json.JSONDecodeError as e:
             raise Exception(f"Invalid JSON structure in {original_filename}: {e}")
        except Exception as e: # Catch other file reading errors
             raise Exception(f"Error reading JSON file {original_filename}: {e}")

        # Initialize the splitter - convert_lists does NOT go here
        json_splitter = RecursiveJsonSplitter(max_chunk_size=max_chunk_size_chars)

        # Perform the splitting using split_json
        # --- CHANGE HERE: Add convert_lists=True to the splitting method call ---
        # This tells the splitter to handle lists by converting them internally during splitting
        final_json_chunks_structured = json_splitter.split_json(
            json_data=json_data,
            convert_lists=True # Use the feature here as per documentation
        )

        # Convert each structured chunk (which are dicts/lists) back into a JSON string for saving
        # Using ensure_ascii=False is safer for preserving original characters if any non-ASCII exist
        final_chunks_text = [json.dumps(chunk, ensure_ascii=False) for chunk in final_json_chunks_structured]

        initial_chunk_count = len(final_chunks_text)
        update_callback(number_of_pages=initial_chunk_count) # Initial estimate

        for idx, chunk_content in enumerate(final_chunks_text, start=1):
            # Skip potentially empty or trivial chunks (e.g., "{}" or "[]" or just "")
            # Stripping allows checking for empty strings potentially generated
            if not chunk_content or chunk_content == '""' or chunk_content == '{}' or chunk_content == '[]' or not chunk_content.strip('{}[]" '):
                debug_print(f"Skipping empty or trivial JSON chunk {idx}/{initial_chunk_count}")
                continue # Skip saving this chunk

            update_callback(
                current_file_chunk=idx, # Use original index for progress display
                # Keep number_of_pages as initial estimate during saving loop
                status=f"Saving chunk {idx}/{initial_chunk_count}..."
            )
            args = {
                "page_text_content": chunk_content,
                "page_number": total_chunks_saved + 1,
                "file_name": original_filename,
                "user_id": user_id,
                "document_id": document_id
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            token_usage = save_chunks(**args)
            total_chunks_saved += 1 # Increment only when a chunk is actually saved

            # Accumulate embedding tokens
            if token_usage:
                total_embedding_tokens += token_usage.get('total_tokens', 0)
                if not embedding_model_name:
                    embedding_model_name = token_usage.get('model_deployment_name')

        # Final update with the actual number of chunks saved
        if total_chunks_saved != initial_chunk_count:
            update_callback(number_of_pages=total_chunks_saved)
            debug_print(f"Adjusted final chunk count from {initial_chunk_count} to {total_chunks_saved} after skipping empty chunks.")


    except Exception as e:
        # Catch errors during loading, splitting, or saving
        # Avoid catching the specific JSONDecodeError again if already handled
        if not isinstance(e, json.JSONDecodeError):
             debug_print(f"Error during JSON processing for {original_filename}: {type(e).__name__}: {e}")
        # Re-raise wrapped exception for the main handler
        raise Exception(f"Failed processing JSON file {original_filename}: {e}")

    # Extract metadata if enabled and chunks were processed
    settings = get_settings()
    enable_extract_meta_data = settings.get('enable_extract_meta_data', False)
    if enable_extract_meta_data and total_chunks_saved > 0:
        try:
            update_callback(status="Extracting final metadata...")
            args = {
                "document_id": document_id,
                "user_id": user_id
            }

            if public_workspace_id:
                args["public_workspace_id"] = public_workspace_id
            elif group_id:
                args["group_id"] = group_id

            document_metadata = extract_document_metadata(**args)

            if document_metadata:
                update_fields = {k: v for k, v in document_metadata.items() if v is not None and v != ""}
                if update_fields:
                    update_fields['status'] = "Final metadata extracted"
                    update_callback(**update_fields)
                else:
                    update_callback(status="Final metadata extraction yielded no new info")
        except Exception as e:
            debug_print(f"Warning: Error extracting final metadata for JSON document {document_id}: {str(e)}")
            update_callback(status=f"Processing complete (metadata extraction warning)")

    # Return the count of chunks actually saved
    return total_chunks_saved, total_embedding_tokens, embedding_model_name


def process_single_tabular_sheet(df, document_id, user_id, file_name, update_callback, group_id=None, public_workspace_id=None):
    """Chunks a pandas DataFrame from a CSV or Excel sheet."""
    from services.chunk_service import save_chunks
    import pandas

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    total_chunks_saved = 0
    total_embedding_tokens = 0
    embedding_model_name = None
    target_chunk_size_chars = 800 # Requirement: "800 size chunk" (assuming characters)

    if df.empty:
        debug_print(f"Skipping empty sheet/file: {file_name}")
        return 0

    # Get header
    header = df.columns.tolist()
    header_string = ",".join(map(str, header)) + "\n" # CSV representation of header

    # Prepare rows as strings (e.g., CSV format)
    rows_as_strings = []
    for _, row in df.iterrows():
        # Convert row to string, handling potential NaNs and types
        row_string = ",".join(map(lambda x: str(x) if pandas.notna(x) else "", row.tolist())) + "\n"
        rows_as_strings.append(row_string)

    # Chunk rows based on character count
    final_chunks_content = []
    current_chunk_rows = []
    current_chunk_char_count = 0

    for row_str in rows_as_strings:
        row_len = len(row_str)
        # If adding the current row exceeds the limit AND the chunk already has content
        if current_chunk_char_count + row_len > target_chunk_size_chars and current_chunk_rows:
            # Finalize the current chunk
            final_chunks_content.append("".join(current_chunk_rows))
            # Start a new chunk with the current row
            current_chunk_rows = [row_str]
            current_chunk_char_count = row_len
        else:
            # Add row to the current chunk
            current_chunk_rows.append(row_str)
            current_chunk_char_count += row_len

    # Add the last remaining chunk if it has content
    if current_chunk_rows:
        final_chunks_content.append("".join(current_chunk_rows))

    num_chunks_final = len(final_chunks_content)
    # Update total pages estimate once at the start of processing this sheet
    # Note: This might overwrite previous updates if called multiple times for excel sheets.
    # Consider accumulating page count in the caller if needed.
    update_callback(number_of_pages=num_chunks_final)

    # Save chunks, prepending the header to each
    for idx, chunk_rows_content in enumerate(final_chunks_content, start=1):
        # Prepend header - header length does not count towards chunk size limit
        chunk_with_header = header_string + chunk_rows_content

        update_callback(
            current_file_chunk=idx,
            status=f"Saving chunk {idx}/{num_chunks_final} from {file_name}..."
        )

        args = {
            "page_text_content": chunk_with_header,
            "page_number": idx,
            "file_name": file_name,
            "user_id": user_id,
            "document_id": document_id
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        token_usage = save_chunks(**args)
        total_chunks_saved += 1

        # Accumulate embedding tokens
        if token_usage:
            total_embedding_tokens += token_usage.get('total_tokens', 0)
            if not embedding_model_name:
                embedding_model_name = token_usage.get('model_deployment_name')

    return total_chunks_saved, total_embedding_tokens, embedding_model_name


def process_tabular(document_id, user_id, temp_file_path, original_filename, file_ext, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes CSV, XLSX, or XLS files using pandas."""
    from services.blob_service import upload_to_blob
    from services.metadata_service import extract_document_metadata
    import pandas

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    update_callback(status=f"Processing Tabular file ({file_ext})...")
    total_chunks_saved = 0
    total_embedding_tokens = 0
    embedding_model_name = None

    # Upload the original file once if enhanced citations are enabled
    if enable_enhanced_citations:
        args = {
            "temp_file_path": temp_file_path,
            "user_id": user_id,
            "document_id": document_id,
            "blob_filename": original_filename,
            "update_callback": update_callback
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        upload_to_blob(**args)

    try:
        if file_ext == '.csv':
            # Process CSV
             # Read CSV, attempt to infer header, keep data as string initially
            df = pandas.read_csv(
                temp_file_path,
                keep_default_na=False,
                dtype=str
            )
            args = {
                "df": df,
                "document_id": document_id,
                "user_id": user_id,
                "file_name": original_filename,
                "update_callback": update_callback
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            result = process_single_tabular_sheet(**args)
            if isinstance(result, tuple) and len(result) == 3:
                chunks, tokens, model = result
                total_chunks_saved = chunks
                total_embedding_tokens += tokens
                if not embedding_model_name:
                    embedding_model_name = model
            else:
                total_chunks_saved = result

        elif file_ext in ('.xlsx', '.xls', '.xlsm'):
            # Process Excel (potentially multiple sheets)
            excel_file = pandas.ExcelFile(
                temp_file_path,
                engine='openpyxl' if file_ext in ('.xlsx', '.xlsm') else 'xlrd'
            )
            sheet_names = excel_file.sheet_names
            base_name, ext = os.path.splitext(original_filename)

            accumulated_total_chunks = 0
            for sheet_name in sheet_names:
                update_callback(status=f"Processing sheet '{sheet_name}'...")
                # Read specific sheet, get values (not formulas), keep data as string
                # Note: pandas typically reads values, not formulas by default.
                df = excel_file.parse(sheet_name, keep_default_na=False, dtype=str)

                # Create effective filename for this sheet
                effective_filename = f"{base_name}-{sheet_name}{ext}" if len(sheet_names) > 1 else original_filename

                args = {
                    "df": df,
                    "document_id": document_id,
                    "user_id": user_id,
                    "file_name": effective_filename,
                    "update_callback": update_callback
                }

                if is_public_workspace:
                    args["public_workspace_id"] = public_workspace_id
                elif is_group:
                    args["group_id"] = group_id

                result = process_single_tabular_sheet(**args)
                if isinstance(result, tuple) and len(result) == 3:
                    chunks, tokens, model = result
                    accumulated_total_chunks += chunks
                    total_embedding_tokens += tokens
                    if not embedding_model_name:
                        embedding_model_name = model
                else:
                    accumulated_total_chunks += result

            total_chunks_saved = accumulated_total_chunks # Total across all sheets


    except pandas.errors.EmptyDataError:
        debug_print(f"Warning: Tabular file or sheet is empty: {original_filename}")
        update_callback(status=f"Warning: File/sheet is empty - {original_filename}", number_of_pages=0)
    except Exception as e:
        raise Exception(f"Failed processing Tabular file {original_filename}: {e}")

    # Extract metadata if enabled and chunks were processed
    settings = get_settings()
    enable_extract_meta_data = settings.get('enable_extract_meta_data', False)
    if enable_extract_meta_data and total_chunks_saved > 0:
        try:
            update_callback(status="Extracting final metadata...")
            args = {
                "document_id": document_id,
                "user_id": user_id
            }

            if public_workspace_id:
                args["public_workspace_id"] = public_workspace_id
            elif group_id:
                args["group_id"] = group_id

            document_metadata = extract_document_metadata(**args)

            if document_metadata:
                update_fields = {k: v for k, v in document_metadata.items() if v is not None and v != ""}
                if update_fields:
                    update_fields['status'] = "Final metadata extracted"
                    update_callback(**update_fields)
                else:
                    update_callback(status="Final metadata extraction yielded no new info")
        except Exception as e:
            debug_print(f"Warning: Error extracting final metadata for Tabular document {document_id}: {str(e)}")
            update_callback(status=f"Processing complete (metadata extraction warning)")

    return total_chunks_saved, total_embedding_tokens, embedding_model_name


def process_di_document(document_id, user_id, temp_file_path, original_filename, file_ext, enable_enhanced_citations, update_callback, group_id=None, public_workspace_id=None):
    """Processes documents supported by Azure Document Intelligence (PDF, Word, PPT, Image)."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_chunks, get_pdf_page_count, chunk_pdf
    from services.document_service import get_document_metadata
    from services.metadata_service import extract_document_metadata, analyze_image_with_vision_model
    from functions_content import extract_content_with_azure_di, extract_pdf_metadata, extract_docx_metadata, parse_authors, chunk_word_file_into_pages

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # --- Token tracking initialization ---
    total_embedding_tokens = 0
    embedding_model_name = None

    # --- Extracted Metadata logic ---
    doc_title, doc_author, doc_subject, doc_keywords = '', '', None, None
    doc_authors_list = []
    page_count = 0 # For PDF pre-check

    is_pdf = file_ext == '.pdf'
    is_word = file_ext in ('.docx', '.doc')
    is_ppt = file_ext in ('.pptx', '.ppt')
    is_image = file_ext in tuple('.' + ext for ext in IMAGE_EXTENSIONS)

    try:
        if is_pdf:
            doc_title, doc_author, doc_subject, doc_keywords = extract_pdf_metadata(temp_file_path)
            doc_authors_list = parse_authors(doc_author)
            page_count = get_pdf_page_count(temp_file_path)
        elif is_word:
            doc_title, doc_author = extract_docx_metadata(temp_file_path)
            doc_authors_list = parse_authors(doc_author)
        # PPT and Image metadata extraction might be added here if needed/possible

        update_fields = {'status': "Extracted initial metadata"}
        if doc_title: update_fields['title'] = doc_title
        if doc_authors_list: update_fields['authors'] = doc_authors_list
        elif doc_author: update_fields['authors'] = [doc_author]
        if doc_subject: update_fields['abstract'] = doc_subject
        if doc_keywords: update_fields['keywords'] = doc_keywords
        update_callback(**update_fields)

    except Exception as e:
        debug_print(f"Warning: Failed to extract initial metadata for {original_filename}: {e}")
        # Continue processing even if metadata fails

    # --- DI Processing Logic ---
    settings = get_settings() # Assuming get_settings is accessible
    di_limit_bytes = 500 * 1024 * 1024
    di_page_limit = 2000
    file_size = os.path.getsize(temp_file_path)

    file_paths_to_process = [temp_file_path]
    needs_pdf_file_chunking = False
    use_enhanced_citations_di = False # Specific flag for DI types

    if enable_enhanced_citations:
        # Enhanced citations involve blob link for PDF, PPT, Word, Image in this flow
        use_enhanced_citations_di = True
        update_callback(enhanced_citations=True, status=f"Enhanced citations enabled for {file_ext}")
        # Check if PDF needs *file-level* chunking before DI/Upload
        if is_pdf and (file_size > di_limit_bytes or (page_count > 0 and page_count > di_page_limit)):
            needs_pdf_file_chunking = True
    else:
        update_callback(enhanced_citations=False, status="Enhanced citations disabled")

    if needs_pdf_file_chunking:
        try:
            update_callback(status="Chunking large PDF file...")
            pdf_chunk_max_pages = di_page_limit // 4 if di_page_limit > 4 else 500
            file_paths_to_process = chunk_pdf(temp_file_path, max_pages=pdf_chunk_max_pages)
            if not file_paths_to_process:
                raise Exception("PDF chunking failed to produce output files.")
            if os.path.exists(temp_file_path): os.remove(temp_file_path) # Remove original large PDF
            debug_print(f"Successfully chunked large PDF into {len(file_paths_to_process)} files.")
        except Exception as e:
            raise Exception(f"Failed to chunk PDF file: {str(e)}")

    num_file_chunks = len(file_paths_to_process)
    update_callback(num_file_chunks=num_file_chunks, status=f"Processing {original_filename} in {num_file_chunks} file chunk(s)")

    total_final_chunks_processed = 0
    for idx, chunk_path in enumerate(file_paths_to_process, start=1):
        chunk_base_name, chunk_ext_loop = os.path.splitext(original_filename)
        chunk_effective_filename = original_filename
        if num_file_chunks > 1:
            chunk_effective_filename = f"{chunk_base_name}_chunk_{idx}{chunk_ext_loop}"
        debug_print(f"Processing DI file chunk {idx}/{num_file_chunks}: {chunk_effective_filename}")

        update_callback(status=f"Processing file chunk {idx}/{num_file_chunks}: {chunk_effective_filename}")

        # Upload to Blob (if enhanced citations enabled for these types)
        if use_enhanced_citations_di:
            args = {
                "temp_file_path": temp_file_path,
                "user_id": user_id,
                "document_id": document_id,
                "blob_filename": chunk_effective_filename,
                "update_callback": update_callback
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            upload_to_blob(**args)

        # Send chunk to Azure DI
        update_callback(status=f"Sending {chunk_effective_filename} to Azure Document Intelligence...")
        di_extracted_pages = []
        try:
            di_extracted_pages = extract_content_with_azure_di(chunk_path)
            num_di_pages = len(di_extracted_pages)
            conceptual_pages = num_di_pages if not is_image else 1 # Image is one conceptual item

            if not di_extracted_pages and not is_image:
                debug_print(f"Warning: Azure DI returned no content pages for {chunk_effective_filename}.")
                status_msg = f"Azure DI found no content in {chunk_effective_filename}."
                # Update page count to 0 if nothing found, otherwise keep previous estimate or conceptual count
                update_callback(number_of_pages=0 if idx == num_file_chunks else conceptual_pages, status=status_msg)
            elif not di_extracted_pages and is_image:
                debug_print(f"Info: Azure DI processed image {chunk_effective_filename}, but extracted no text.")
                update_callback(number_of_pages=conceptual_pages, status=f"Processed image {chunk_effective_filename} (no text found).")
            else:
                 update_callback(number_of_pages=conceptual_pages, status=f"Received {num_di_pages} content page(s)/slide(s) from Azure DI for {chunk_effective_filename}.")

        except Exception as e:
            raise Exception(f"Error extracting content from {chunk_effective_filename} with Azure DI: {str(e)}")

        # --- Multi-Modal Vision Analysis (for images only) - Must happen BEFORE save_chunks ---
        if is_image and enable_enhanced_citations and idx == 1:  # Only run once for first chunk
            enable_multimodal_vision = settings.get('enable_multimodal_vision', False)
            if enable_multimodal_vision:
                try:
                    update_callback(status="Performing AI vision analysis...")

                    vision_analysis = analyze_image_with_vision_model(
                        chunk_path,
                        user_id,
                        document_id,
                        settings
                    )

                    if vision_analysis:
                        debug_print(f"Vision analysis completed for image: {chunk_effective_filename}")

                        # Update document with vision analysis results BEFORE saving chunks
                        # This allows save_chunks() to append vision data to chunk_text for AI Search
                        update_fields = {
                            'vision_analysis': vision_analysis,
                            'vision_description': vision_analysis.get('description', ''),
                            'vision_objects': vision_analysis.get('objects', []),
                            'vision_extracted_text': vision_analysis.get('text', ''),
                            'status': "AI vision analysis completed"
                        }
                        update_callback(**update_fields)
                        debug_print(f"Vision analysis saved to document metadata and will be appended to chunk_text for AI Search indexing")
                    else:
                        debug_print(f"Vision analysis returned no results for: {chunk_effective_filename}")
                        update_callback(status="Vision analysis completed (no results)")

                except Exception as e:
                    debug_print(f"Warning: Error in vision analysis for {document_id}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Don't fail the whole process, just update status
                    update_callback(status=f"Processing continues (vision analysis warning)")

        # Content Chunking Strategy (Word needs specific handling)
        final_chunks_to_save = []
        if is_word:
            update_callback(status=f"Chunking Word content from {chunk_effective_filename}...")
            try:
                final_chunks_to_save = chunk_word_file_into_pages(di_pages=di_extracted_pages)
                num_final_chunks = len(final_chunks_to_save)
                # Update number_of_pages again for Word to reflect final chunk count
                update_callback(number_of_pages=num_final_chunks, status=f"Created {num_final_chunks} content chunks for {chunk_effective_filename}.")
            except Exception as e:
                 raise Exception(f"Error chunking Word content for {chunk_effective_filename}: {str(e)}")
        elif is_pdf or is_ppt:
            final_chunks_to_save = di_extracted_pages # Use DI pages/slides directly
        elif is_image:
            if di_extracted_pages:
                 if 'page_number' not in di_extracted_pages[0]: di_extracted_pages[0]['page_number'] = 1
                 final_chunks_to_save = di_extracted_pages
            else: final_chunks_to_save = [] # No text extracted

        # Save Final Chunks to Search Index
        num_final_chunks = len(final_chunks_to_save)
        if not final_chunks_to_save:
            debug_print(f"Info: No final content chunks to save for {chunk_effective_filename}.")
        else:
            update_callback(status=f"Saving {num_final_chunks} content chunk(s) for {chunk_effective_filename}...")
            args = {
                "document_id": document_id,
                "user_id": user_id
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            doc_metadata_temp = get_document_metadata(**args)

            estimated_total_items = doc_metadata_temp.get('number_of_pages', num_final_chunks) if doc_metadata_temp else num_final_chunks

            try:
                for i, chunk_data in enumerate(final_chunks_to_save):
                    chunk_index = chunk_data.get("page_number", i + 1) # Ensure page number exists
                    chunk_content = chunk_data.get("content", "")

                    if not chunk_content.strip():
                        debug_print(f"Skipping empty chunk index {chunk_index} for {chunk_effective_filename}.")
                        continue

                    update_callback(
                        current_file_chunk=int(chunk_index),
                        number_of_pages=estimated_total_items,
                        status=f"Saving page/chunk {chunk_index}/{estimated_total_items} of {chunk_effective_filename}..."
                    )

                    args = {
                        "page_text_content": chunk_content,
                        "page_number": chunk_index,
                        "file_name": chunk_effective_filename,
                        "user_id": user_id,
                        "document_id": document_id
                    }

                    if is_public_workspace:
                        args["public_workspace_id"] = public_workspace_id
                    elif is_group:
                        args["group_id"] = group_id

                    token_usage = save_chunks(**args)

                    # Accumulate embedding tokens
                    if token_usage:
                        total_embedding_tokens += token_usage.get('total_tokens', 0)
                        if not embedding_model_name:
                            embedding_model_name = token_usage.get('model_deployment_name')

                    total_final_chunks_processed += 1
                debug_print(f"Saved {num_final_chunks} content chunk(s) from {chunk_effective_filename}.")
            except Exception as e:
                raise Exception(f"Error saving extracted content chunk index {chunk_index} for {chunk_effective_filename}: {repr(e)}\nTraceback:\n{traceback.format_exc()}")

        # Clean up local file chunk (if it's not the original temp file)
        if chunk_path != temp_file_path and os.path.exists(chunk_path):
            try:
                os.remove(chunk_path)
                debug_print(f"Cleaned up temporary chunk file: {chunk_path}")
            except Exception as cleanup_e:
                debug_print(f"Warning: Failed to clean up temp chunk file {chunk_path}: {cleanup_e}")

    # --- Final Metadata Extraction (Optional, moved outside loop) ---
    settings = get_settings() # Re-get in case it changed? Or pass it down.
    enable_extract_meta_data = settings.get('enable_extract_meta_data')
    if enable_extract_meta_data and total_final_chunks_processed > 0:
        try:
            update_callback(status="Extracting final metadata...")
            args = {
                "document_id": document_id,
                "user_id": user_id
            }

            if is_public_workspace:
                args["public_workspace_id"] = public_workspace_id
            elif is_group:
                args["group_id"] = group_id

            document_metadata = extract_document_metadata(**args)

            update_fields = {k: v for k, v in document_metadata.items() if v is not None and v != ""}
            if update_fields:
                 update_fields['status'] = "Final metadata extracted"
                 update_callback(**update_fields)
            else:
                 update_callback(status="Final metadata extraction yielded no new info")
        except Exception as e:
            debug_print(f"Warning: Error extracting final metadata for {document_id}: {str(e)}")
            # Don't fail the whole proc, total_embedding_tokens, embedding_model_nameess, just update status
            update_callback(status=f"Processing complete (metadata extraction warning)")

    # Note: Vision analysis now happens BEFORE save_chunks (moved earlier in the flow)
    # This ensures vision_analysis is available in metadata when chunks are being saved

    return total_final_chunks_processed, total_embedding_tokens, embedding_model_name


def process_document_upload_background(document_id, user_id, temp_file_path, original_filename, group_id=None, public_workspace_id=None):
    """
    Main background task dispatcher for document processing.
    Handles various file types with specific chunking and processing logic.
    Integrates enhanced citations (blob upload) for all supported types.
    """
    from services.document_service import allowed_file, update_document, get_document_metadata
    from services.media_service import process_video_document, process_audio_document

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None
    settings = get_settings()
    enable_enhanced_citations = settings.get('enable_enhanced_citations', False) # Default to False if missing
    enable_extract_meta_data = settings.get('enable_extract_meta_data', False) # Used by DI flow
    max_file_size_bytes = settings.get('max_file_size_mb', 16) * 1024 * 1024

    # Get allowed extensions from config.py to determine which processing function to call
    tabular_extensions = tuple('.' + ext for ext in TABULAR_EXTENSIONS)
    image_extensions = tuple('.' + ext for ext in IMAGE_EXTENSIONS)
    di_supported_extensions = tuple('.' + ext for ext in DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS)
    video_extensions = tuple('.' + ext for ext in VIDEO_EXTENSIONS)
    audio_extensions = tuple('.' + ext for ext in AUDIO_EXTENSIONS)

    # --- Define update_document callback wrapper ---
    # This makes it easier to pass the update function to helpers without repeating args
    def update_doc_callback(**kwargs):
        args = {
            "document_id": document_id,
            "user_id": user_id,
            **kwargs  # includes any dynamic update fields
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        update_document(**args)


    total_chunks_saved = 0
    total_embedding_tokens = 0
    embedding_model_name = None
    file_ext = '' # Initialize

    try:
        # --- 0. Initial Setup & Validation ---
        if not temp_file_path or not os.path.exists(temp_file_path):
             raise FileNotFoundError(f"Temporary file path not found or invalid: {temp_file_path}")

        file_ext = os.path.splitext(original_filename)[-1].lower()
        if not file_ext:
            raise ValueError("Could not determine file extension from original filename.")

        if not allowed_file(original_filename): # Assuming allowed_file checks the extension
             raise ValueError(f"File type {file_ext} is not allowed.")

        file_size = os.path.getsize(temp_file_path)
        if file_size > max_file_size_bytes:
            raise ValueError(f"File exceeds maximum allowed size ({max_file_size_bytes / (1024*1024):.1f} MB).")

        update_doc_callback(status=f"Processing file {original_filename}, type: {file_ext}")

        # --- 1. Dispatch to appropriate handler based on file type ---
        # Note: .doc and .docm are handled separately by process_doc() using docx2txt

        is_group = group_id is not None

        args = {
            "document_id": document_id,
            "user_id": user_id,
            "temp_file_path": temp_file_path,
            "original_filename": original_filename,
            "file_ext": file_ext if file_ext in tabular_extensions or file_ext in di_supported_extensions else None,
            "enable_enhanced_citations": enable_enhanced_citations,
            "update_callback": update_doc_callback
        }

        if is_public_workspace:
            args["public_workspace_id"] = public_workspace_id
        elif is_group:
            args["group_id"] = group_id

        if file_ext == '.txt':
            result = process_txt(**{k: v for k, v in args.items() if k != "file_ext"})
            # Handle tuple return (chunks, tokens, model_name)
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext == '.xml':
            result = process_xml(**{k: v for k, v in args.items() if k != "file_ext"})
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext in ('.yaml', '.yml'):
            result = process_yaml(**{k: v for k, v in args.items() if k != "file_ext"})
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext == '.log':
            result = process_log(**{k: v for k, v in args.items() if k != "file_ext"})
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext in ('.doc', '.docm'):
            result = process_doc(**{k: v for k, v in args.items() if k != "file_ext"})
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext == '.html':
            result = process_html(**{k: v for k, v in args.items() if k != "file_ext"})
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext == '.md':
            result = process_md(**{k: v for k, v in args.items() if k != "file_ext"})
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext == '.json':
            result = process_json(**{k: v for k, v in args.items() if k != "file_ext"})
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext in tabular_extensions:
            result = process_tabular(**args)
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        elif file_ext in video_extensions:
            total_chunks_saved = process_video_document(
                document_id=document_id,
                user_id=user_id,
                temp_file_path=temp_file_path,
                original_filename=original_filename,
                update_callback=update_doc_callback,
                group_id=group_id,
                public_workspace_id=public_workspace_id
            )
        elif file_ext in audio_extensions:
            total_chunks_saved = process_audio_document(
                document_id=document_id,
                user_id=user_id,
                temp_file_path=temp_file_path,
                original_filename=original_filename,
                update_callback=update_doc_callback,
                group_id=group_id,
                public_workspace_id=public_workspace_id
            )
        elif file_ext in di_supported_extensions:
            result = process_di_document(**args)
            # Handle tuple return (chunks, tokens, model_name)
            if isinstance(result, tuple) and len(result) == 3:
                total_chunks_saved, total_embedding_tokens, embedding_model_name = result
            else:
                total_chunks_saved = result
        else:
            raise ValueError(f"Unsupported file type for processing: {file_ext}")


        # --- 2. Final Status Update ---
        final_status = "Processing complete"
        if total_chunks_saved == 0:
             # Provide more specific status if no chunks were saved
             if file_ext in image_extensions:
                 final_status = "Processing complete - no text found in image"
             elif file_ext in tabular_extensions:
                 final_status = "Processing complete - no data rows found or file empty"
             else:
                 final_status = "Processing complete - no content indexed"

        # Final update uses the total chunks saved across all steps/sheets
        # For DI types, number_of_pages might have been updated during DI processing,
        # but let's ensure the final update reflects the *saved* chunk count accurately.
        # Also update embedding token tracking data
        final_update_args = {
             "number_of_pages": total_chunks_saved, # Final count of SAVED chunks
             "status": final_status,
             "percentage_complete": 100,
             "current_file_chunk": None # Clear current chunk tracking
        }

        # Add embedding token data if available
        if total_embedding_tokens > 0:
            final_update_args["embedding_tokens"] = total_embedding_tokens
        if embedding_model_name:
            final_update_args["embedding_model_deployment_name"] = embedding_model_name

        update_doc_callback(**final_update_args)

        debug_print(f"Document {document_id} ({original_filename}) processed successfully with {total_chunks_saved} chunks saved and {total_embedding_tokens} embedding tokens used.")

        # Graph RAG: extract entities as async background task (Phase 4)
        try:
            from functions_settings import get_settings as _get_settings
            _settings = _get_settings()
            if _settings and _settings.get("enable_graph_rag", False) and total_chunks_saved > 0:
                from functions_graph_entities import extract_and_store_entities
                executor = current_app.extensions.get("executor") if current_app else None
                if executor:
                    executor.submit(
                        extract_and_store_entities,
                        document_id=document_id,
                        user_id=user_id,
                        group_id=group_id,
                        public_workspace_id=public_workspace_id,
                        settings=_settings,
                    )
                    debug_print(f"Graph RAG entity extraction queued for document {document_id}")
        except Exception as graph_err:
            debug_print(f"Graph RAG extraction failed to queue (non-blocking): {graph_err}")

        # Log document creation transaction to activity_logs container
        try:
            from functions_activity_logging import log_document_creation_transaction, log_token_usage

            # Retrieve final document metadata to capture all extracted fields
            doc_metadata = get_document_metadata(
                document_id=document_id,
                user_id=user_id,
                group_id=group_id,
                public_workspace_id=public_workspace_id
            )

            # Determine workspace type
            if public_workspace_id:
                workspace_type = 'public'
            elif group_id:
                workspace_type = 'group'
            else:
                workspace_type = 'personal'

            # Log the transaction with all available metadata
            log_document_creation_transaction(
                user_id=user_id,
                document_id=document_id,
                workspace_type=workspace_type,
                file_name=original_filename,
                file_type=file_ext,
                file_size=file_size,
                page_count=total_chunks_saved,
                embedding_tokens=total_embedding_tokens,
                embedding_model=embedding_model_name,
                version=doc_metadata.get('version') if doc_metadata else None,
                author=doc_metadata.get('author') if doc_metadata else None,
                title=doc_metadata.get('title') if doc_metadata else None,
                subject=doc_metadata.get('subject') if doc_metadata else None,
                publication_date=doc_metadata.get('publication_date') if doc_metadata else None,
                keywords=doc_metadata.get('keywords') if doc_metadata else None,
                abstract=doc_metadata.get('abstract') if doc_metadata else None,
                group_id=group_id,
                public_workspace_id=public_workspace_id,
                additional_metadata={
                    'status': final_status,
                    'upload_date': doc_metadata.get('upload_date') if doc_metadata else None,
                    'document_classification': doc_metadata.get('document_classification') if doc_metadata else None
                }
            )

            # Log embedding token usage separately for easy reporting
            if total_embedding_tokens > 0 and embedding_model_name:
                log_token_usage(
                    user_id=user_id,
                    token_type='embedding',
                    total_tokens=total_embedding_tokens,
                    model=embedding_model_name,
                    workspace_type=workspace_type,
                    document_id=document_id,
                    file_name=original_filename,
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                    additional_context={
                        'file_type': file_ext,
                        'page_count': total_chunks_saved
                    }
                )

            # Mark document as logged to activity logs to prevent duplicate migration
            try:
                # All document containers use /id as partition key
                if public_workspace_id:
                    doc_container = cosmos_public_documents_container
                elif group_id:
                    doc_container = cosmos_group_documents_container
                else:
                    doc_container = cosmos_user_documents_container

                # All document containers use document_id (/id) as partition key
                partition_key = document_id

                # Read, update, and upsert the document with the flag
                doc_record = doc_container.read_item(item=document_id, partition_key=partition_key)
                doc_record['added_to_activity_log'] = True
                doc_container.upsert_item(doc_record)
                debug_print(f"✅ Set added_to_activity_log flag for document {document_id}")

            except Exception as flag_error:
                debug_print(f"⚠️  Warning: Failed to set added_to_activity_log flag: {flag_error}")
                # Don't fail if flag setting fails

        except Exception as log_error:
            debug_print(f"Error logging document creation transaction: {log_error}")
            # Don't fail the entire process if logging fails

        # Create notification for document processing completion
        try:
            from functions_notifications import create_notification, create_group_notification, create_public_workspace_notification

            notification_title = f"Document ready: {original_filename}"
            notification_message = f"Your document has been processed successfully with {total_chunks_saved} chunks."

            # Determine workspace type and create appropriate notification
            if public_workspace_id:
                # Notification for all public workspace members
                create_public_workspace_notification(
                    public_workspace_id=public_workspace_id,
                    notification_type='document_processing_complete',
                    title=notification_title,
                    message=notification_message,
                    link_url='/public_directory',
                    link_context={
                        'workspace_type': 'public',
                        'public_workspace_id': public_workspace_id,
                        'document_id': document_id
                    },
                    metadata={
                        'document_id': document_id,
                        'file_name': original_filename,
                        'chunks': total_chunks_saved
                    }
                )
                debug_print(f"📢 Created notification for public workspace {public_workspace_id}")

            elif group_id:
                # Notification for all group members - get group name
                from functions_group import find_group_by_id
                group = find_group_by_id(group_id)
                group_name = group.get('name', 'Unknown Group') if group else 'Unknown Group'

                create_group_notification(
                    group_id=group_id,
                    notification_type='document_processing_complete',
                    title=notification_title,
                    message=f"Document uploaded to {group_name} has been processed successfully with {total_chunks_saved} chunks.",
                    link_url='/group_workspaces',
                    link_context={
                        'workspace_type': 'group',
                        'group_id': group_id,
                        'document_id': document_id
                    },
                    metadata={
                        'document_id': document_id,
                        'file_name': original_filename,
                        'chunks': total_chunks_saved,
                        'group_name': group_name,
                        'group_id': group_id
                    }
                )
                debug_print(f"📢 Created notification for group {group_id} ({group_name})")

            else:
                # Personal notification for the uploader
                create_notification(
                    user_id=user_id,
                    notification_type='document_processing_complete',
                    title=notification_title,
                    message=notification_message,
                    link_url='/workspace',
                    link_context={
                        'workspace_type': 'personal',
                        'document_id': document_id
                    },
                    metadata={
                        'document_id': document_id,
                        'file_name': original_filename,
                        'chunks': total_chunks_saved
                    }
                )
                debug_print(f"📢 Created notification for user {user_id}")

        except Exception as notif_error:
            debug_print(f"⚠️  Warning: Failed to create notification: {notif_error}")
            # Don't fail the entire process if notification creation fails
            debug_print(f"⚠️  Warning: Failed to log document creation transaction: {log_error}")
            # Don't fail the document processing if logging fails

    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        debug_print(f"Error processing {document_id} ({original_filename}): {error_msg}")
        # Attempt to update status to Error
        try:
            update_doc_callback(
                status=f"Error: {error_msg[:250]}", # Limit error message length
                percentage_complete=0 # Indicate failure
            )
        except Exception as update_e:
            debug_print(f"Critical Error: Failed to update document status to error for {document_id}: {update_e}")

    finally:
        # --- 3. Cleanup ---
        # Clean up the original temporary file path regardless of success or failure
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                debug_print(f"Cleaned up original temporary file: {temp_file_path}")
            except Exception as cleanup_e:
                 debug_print(f"Warning: Failed to clean up original temp file {temp_file_path}: {cleanup_e}")
