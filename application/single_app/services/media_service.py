# media_service.py
# Video and audio document processing — Azure Video Indexer and Azure Speech transcription.

from config import *
from functions_settings import get_settings
from functions_debug import debug_print
import azure.cognitiveservices.speech as speechsdk


def process_video_document(
    document_id,
    user_id,
    temp_file_path,
    original_filename,
    update_callback,
    group_id,
    public_workspace_id=None
):
    """
    Processes a video by dividing transcript into 30-second chunks,
    extracting OCR separately, and saving each as a chunk with safe IDs.
    """
    from functions_debug import debug_print
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_video_chunk, save_chunks
    from services.document_service import update_document, get_document_metadata
    from services.metadata_service import extract_document_metadata
    from functions_content import get_video_indexer_account_token

    debug_print(f"[VIDEO INDEXER] Starting video processing for file: {original_filename}")
    debug_print(f"[VIDEO INDEXER] Document ID: {document_id}, User ID: {user_id}, Group ID: {group_id}, Public Workspace ID: {public_workspace_id}")
    debug_print(f"[VIDEO INDEXER] Temp file path: {temp_file_path}")

    def to_seconds(ts: str) -> float:
        parts = ts.split(':')
        parts = [float(p) for p in parts]
        if len(parts) == 3:
            h, m, s = parts
        else:
            h = 0.0
            m, s = parts
        return h * 3600 + m * 60 + s

    settings = get_settings()
    if not settings.get("enable_video_file_support", False):
        debug_print("[VIDEO INDEXER] Video file support is disabled in settings")
        debug_print("[VIDEO] indexing disabled in settings", flush=True)
        update_callback(status="VIDEO: indexing disabled")
        return 0
    
    debug_print("[VIDEO INDEXER] Video file support is enabled, proceeding with indexing")
    
    if settings.get("enable_enhanced_citations", False):
        debug_print("[VIDEO INDEXER] Enhanced citations enabled, uploading to blob storage")
        update_callback(status="Uploading video for enhanced citations...")
        try:
            # this helper is already in your file below
            blob_path = upload_to_blob(
                temp_file_path,
                user_id,
                document_id,
                original_filename,
                update_callback,
                group_id,
                public_workspace_id
            )
            debug_print(f"[VIDEO INDEXER] Blob upload successful: {blob_path}")
            update_callback(status=f"Enhanced citations: video at {blob_path}")
        except Exception as e:
            debug_print(f"[VIDEO INDEXER] Blob upload failed: {str(e)}")
            debug_print(f"[VIDEO] BLOB UPLOAD ERROR: {e}", flush=True)
            update_callback(status=f"VIDEO: blob upload failed → {e}")

    vi_ep, vi_loc, vi_acc = (
        settings["video_indexer_endpoint"],
        settings["video_indexer_location"],
        settings["video_indexer_account_id"]
    )
    
    debug_print(f"[VIDEO INDEXER] Configuration - Endpoint: {vi_ep}, Location: {vi_loc}, Account ID: {vi_acc}")

    # Validate required settings for managed identity authentication
    required_settings = {
        "video_indexer_endpoint": vi_ep,
        "video_indexer_location": vi_loc,
        "video_indexer_account_id": vi_acc,
        "video_indexer_resource_group": settings.get("video_indexer_resource_group"),
        "video_indexer_subscription_id": settings.get("video_indexer_subscription_id"),
        "video_indexer_account_name": settings.get("video_indexer_account_name")
    }
    
    debug_print(f"[VIDEO INDEXER] Managed identity authentication requires: endpoint, location, account_id, resource_group, subscription_id, account_name")
    
    missing_settings = [key for key, value in required_settings.items() if not value]
    if missing_settings:
        debug_print(f"[VIDEO INDEXER] ERROR: Missing required settings: {missing_settings}")
        update_callback(status=f"VIDEO: missing settings - {', '.join(missing_settings)}")
        return 0

    debug_print("[VIDEO INDEXER] All required settings are present")

    # 1) Auth
    try:
        debug_print("[VIDEO INDEXER] Attempting to acquire authentication token")
        token = get_video_indexer_account_token(settings)
        debug_print(f"[VIDEO INDEXER] Authentication successful, token length: {len(token) if token else 0}")
    except Exception as e:
        debug_print(f"[VIDEO INDEXER] Authentication failed: {str(e)}")
        debug_print(f"[VIDEO] AUTH ERROR: {e}", flush=True)
        update_callback(status=f"VIDEO: auth failed → {e}")
        return 0

    # 2) Upload video to Indexer
    try:
        url = f"{vi_ep}/{vi_loc}/Accounts/{vi_acc}/Videos"
        
        # Use the access token in the URL parameters
        headers = {}
        # Request comprehensive indexing including audio transcript
        params = {
            "accessToken": token, 
            "name": original_filename,
            "indexingPreset": "Default",  # Includes video + audio insights
            "streamingPreset": "NoStreaming"
        }
        debug_print(f"[VIDEO INDEXER] Using managed identity access token authentication")
        
        debug_print(f"[VIDEO INDEXER] Upload URL: {url}")
        debug_print(f"[VIDEO INDEXER] Upload params: {params}")
        debug_print(f"[VIDEO INDEXER] Starting file upload for: {original_filename}")
        
        with open(temp_file_path, "rb") as f:
            resp = requests.post(url, params=params, headers=headers, files={"file": f})
        
        debug_print(f"[VIDEO INDEXER] Upload response status: {resp.status_code}")
        
        if resp.status_code != 200:
            debug_print(f"[VIDEO INDEXER] Upload response text: {resp.text}")
            
        resp.raise_for_status()
        response_data = resp.json()
        debug_print(f"[VIDEO INDEXER] Upload response keys: {list(response_data.keys())}")
        
        vid = response_data.get("id")
        if not vid:
            debug_print(f"[VIDEO INDEXER] ERROR: No video ID in response: {response_data}")
            raise ValueError("no video ID returned")
            
        debug_print(f"[VIDEO INDEXER] Upload successful, video ID: {vid}")
        debug_print(f"[VIDEO] UPLOAD OK, videoId={vid}", flush=True)
        update_callback(status=f"VIDEO: uploaded id={vid}")
        
        try:
            # Update the document's metadata with the video indexer ID
            debug_print(f"[VIDEO INDEXER] Updating document metadata with video_indexer_id: {vid}")
            update_document(
                document_id=document_id,
                user_id=user_id,
                group_id=group_id,
                video_indexer_id=vid
            )
            debug_print(f"[VIDEO INDEXER] Document metadata updated successfully")
        except Exception as e:
            debug_print(f"[VIDEO INDEXER] Failed to update document metadata: {str(e)}")
            debug_print(f"[VIDEO] Failed to update document metadata with video_indexer_id: {e}", flush=True)

    except requests.exceptions.RequestException as e:
        debug_print(f"[VIDEO INDEXER] Upload request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            debug_print(f"[VIDEO INDEXER] Upload error response status: {e.response.status_code}")
            debug_print(f"[VIDEO INDEXER] Upload error response text: {e.response.text}")
        debug_print(f"[VIDEO] UPLOAD ERROR: {e}", flush=True)
        update_callback(status=f"VIDEO: upload failed → {e}")
        return 0
    except Exception as e:
        debug_print(f"[VIDEO INDEXER] Upload unexpected error: {str(e)}")
        debug_print(f"[VIDEO] UPLOAD ERROR: {e}", flush=True)
        update_callback(status=f"VIDEO: upload failed → {e}")
        return 0

    # 3) Poll until ready
    # Don't use includeInsights parameter - it filters what's returned. We want everything.
    index_url = (
        f"{vi_ep}/{vi_loc}/Accounts/{vi_acc}/Videos/{vid}/Index"
        f"?accessToken={token}"
    )
    poll_headers = {}
    debug_print(f"[VIDEO INDEXER] Using managed identity access token for polling")
    debug_print(f"[VIDEO INDEXER] Requesting full insights (no filtering)")
    
    debug_print(f"[VIDEO INDEXER] Index polling URL: {index_url}")
    debug_print(f"[VIDEO INDEXER] Starting processing polling for video ID: {vid}")
    
    poll_count = 0
    max_polls = 180  # 90 minutes maximum (30 second intervals)
    
    while True:
        poll_count += 1
        debug_print(f"[VIDEO INDEXER] Polling attempt {poll_count}/{max_polls}")
        
        try:
            r = requests.get(index_url, headers=poll_headers)
            debug_print(f"[VIDEO INDEXER] Poll response status: {r.status_code}")
            
            if r.status_code in (401, 404):
                debug_print(f"[VIDEO INDEXER] Poll returned {r.status_code}, waiting 30s and retrying")
                time.sleep(30)
                continue
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 30))
                debug_print(f"[VIDEO INDEXER] Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue
            if r.status_code == 504:
                debug_print(f"[VIDEO INDEXER] Timeout received, waiting 30s and retrying")
                time.sleep(30)
                continue
                
            r.raise_for_status()
            data = r.json()
            debug_print(f"[VIDEO INDEXER] Poll response keys: {list(data.keys())}")
            
        except requests.exceptions.RequestException as e:
            debug_print(f"[VIDEO INDEXER] Poll request failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                debug_print(f"[VIDEO INDEXER] Poll error response status: {e.response.status_code}")
                debug_print(f"[VIDEO INDEXER] Poll error response text: {e.response.text}")
            if poll_count >= max_polls:
                update_callback(status="VIDEO: polling timeout")
                return 0
            time.sleep(30)
            continue
        except Exception as e:
            debug_print(f"[VIDEO INDEXER] Poll unexpected error: {str(e)}")
            if poll_count >= max_polls:
                update_callback(status="VIDEO: polling timeout")
                return 0
            time.sleep(30)
            continue

        info = data.get("videos", [{}])[0]
        prog = info.get("processingProgress", "0%").rstrip("%")
        state = info.get("state", "").lower()
        
        debug_print(f"[VIDEO INDEXER] Processing progress: {prog}%, State: {state}")
        update_callback(status=f"VIDEO: {prog}%")
        
        if state == "failed":
            debug_print(f"[VIDEO INDEXER] Processing failed for video ID: {vid}")
            update_callback(status="VIDEO: indexing failed")
            return 0
        if prog == "100":
            debug_print(f"[VIDEO INDEXER] Processing completed for video ID: {vid}")
            break
            
        if poll_count >= max_polls:
            debug_print(f"[VIDEO INDEXER] Maximum polling attempts reached for video ID: {vid}")
            update_callback(status="VIDEO: processing timeout")
            return 0
            
        time.sleep(30)

    # 4) Extract transcript & OCR
    debug_print(f"[VIDEO INDEXER] Starting insights extraction for video ID: {vid}")
    debug_print(f"[VIDEO INDEXER] Extracting insights from completed video")
    
    insights = info.get("insights", {})
    if not insights:
        debug_print(f"[VIDEO INDEXER] ERROR: No insights object in response")
        debug_print(f"[VIDEO INDEXER] Response info keys: {list(info.keys())}")
        return 0
    
    # Get video duration from insights (primary) or info (fallback)
    video_duration = insights.get("duration") or info.get("duration", "00:00:00")
    video_duration_seconds = to_seconds(video_duration) if video_duration else 0
    debug_print(f"[VIDEO INDEXER] Video duration: {video_duration} ({video_duration_seconds} seconds)")
    
    # Log raw insights JSON for complete visibility (debug only)
    import json
    debug_print(f"\n[VIDEO] ===== RAW INSIGHTS JSON =====", flush=True)
    try:
        insights_json = json.dumps(insights, indent=2, ensure_ascii=False)
        # Truncate if too long (show first 10000 chars)
        if len(insights_json) > 10000:
            debug_print(f"{insights_json[:10000]}\n... (truncated, total length: {len(insights_json)} chars)", flush=True)
        else:
            debug_print(insights_json, flush=True)
    except Exception as e:
        debug_print(f"[VIDEO] Could not serialize insights to JSON: {e}", flush=True)
    debug_print(f"[VIDEO] ===== END RAW INSIGHTS =====\n", flush=True)
    
    debug_print(f"[VIDEO INDEXER] Insights keys available: {list(insights.keys())}")
    debug_print(f"[VIDEO] Available insight types: {', '.join(list(insights.keys())[:15])}...", flush=True)
    
    # Debug: Show sample structures for all insight types
    debug_print(f"\n[VIDEO] ===== SAMPLE DATA STRUCTURES =====", flush=True)
    
    transcript_data = insights.get("transcript", [])
    if transcript_data:
        debug_print(f"[VIDEO] TRANSCRIPT sample: {transcript_data[0]}", flush=True)
    
    ocr_data = insights.get("ocr", [])
    if ocr_data:
        debug_print(f"[VIDEO] OCR sample: {ocr_data[0]}", flush=True)
    
    keywords_data_debug = insights.get("keywords", [])
    if keywords_data_debug:
        debug_print(f"[VIDEO] KEYWORDS sample: {keywords_data_debug[0]}", flush=True)
    
    labels_data_debug = insights.get("labels", [])
    if labels_data_debug:
        debug_print(f"[VIDEO INDEXER] LABELS sample: {labels_data_debug[0]}")
    
    topics_data_debug = insights.get("topics", [])
    if topics_data_debug:
        debug_print(f"[VIDEO INDEXER] TOPICS sample: {topics_data_debug[0]}")
    
    audio_effects_data_debug = insights.get("audioEffects", [])
    if audio_effects_data_debug:
        debug_print(f"[VIDEO INDEXER] AUDIO_EFFECTS sample: {audio_effects_data_debug[0]}")
    
    emotions_data_debug = insights.get("emotions", [])
    if emotions_data_debug:
        debug_print(f"[VIDEO INDEXER] EMOTIONS sample: {emotions_data_debug[0]}")
    
    sentiments_data_debug = insights.get("sentiments", [])
    if sentiments_data_debug:
        debug_print(f"[VIDEO INDEXER] SENTIMENTS sample: {sentiments_data_debug[0]}")
    
    scenes_data_debug = insights.get("scenes", [])
    if scenes_data_debug:
        debug_print(f"[VIDEO INDEXER] SCENES sample: {scenes_data_debug[0]}")
    
    shots_data_debug = insights.get("shots", [])
    if shots_data_debug:
        debug_print(f"[VIDEO INDEXER] SHOTS sample: {shots_data_debug[0]}")
    
    faces_data_debug = insights.get("faces", [])
    if faces_data_debug:
        debug_print(f"[VIDEO INDEXER] FACES sample: {faces_data_debug[0]}")
    
    namedLocations_data_debug = insights.get("namedLocations", [])
    if namedLocations_data_debug:
        debug_print(f"[VIDEO INDEXER] NAMED_LOCATIONS sample: {namedLocations_data_debug[0]}")
    
    # Check for other potential label sources
    brands_data_debug = insights.get("brands", [])
    if brands_data_debug:
        debug_print(f"[VIDEO INDEXER] BRANDS sample: {brands_data_debug[0]}")
    
    visualContentModeration_debug = insights.get("visualContentModeration", [])
    if visualContentModeration_debug:
        debug_print(f"[VIDEO INDEXER] VISUAL_MODERATION sample: {visualContentModeration_debug[0]}")
    
    # Show total counts for all available insights
    debug_print(f"[VIDEO] COUNTS:", flush=True)
    for key in insights.keys():
        value = insights.get(key, [])
        if isinstance(value, list):
            debug_print(f"  {key}: {len(value)} items", flush=True)
    
    debug_print(f"[VIDEO] ===== END SAMPLE DATA =====\n", flush=True)
    
    transcript = insights.get("transcript", [])
    ocr_blocks = insights.get("ocr", [])
    keywords_data = insights.get("keywords", [])
    labels_data = insights.get("labels", [])
    topics_data = insights.get("topics", [])
    audio_effects_data = insights.get("audioEffects", [])
    emotions_data = insights.get("emotions", [])
    sentiments_data = insights.get("sentiments", [])
    named_people_data = insights.get("namedPeople", [])
    named_locations_data = insights.get("namedLocations", [])
    speakers_data = insights.get("speakers", [])
    detected_objects_data = insights.get("detectedObjects", [])
    
    debug_print(f"[VIDEO INDEXER] Transcript segments found: {len(transcript)}")
    debug_print(f"[VIDEO INDEXER] OCR blocks found: {len(ocr_blocks)}")
    debug_print(f"[VIDEO INDEXER] Keywords found: {len(keywords_data)}")
    debug_print(f"[VIDEO INDEXER] Labels found: {len(labels_data)}")
    debug_print(f"[VIDEO INDEXER] Topics found: {len(topics_data)}")
    debug_print(f"[VIDEO INDEXER] Audio effects found: {len(audio_effects_data)}")
    debug_print(f"[VIDEO INDEXER] Emotions found: {len(emotions_data)}")
    debug_print(f"[VIDEO INDEXER] Sentiments found: {len(sentiments_data)}")
    debug_print(f"[VIDEO INDEXER] Named people found: {len(named_people_data)}")
    debug_print(f"[VIDEO INDEXER] Named locations found: {len(named_locations_data)}")
    debug_print(f"[VIDEO INDEXER] Speakers found: {len(speakers_data)}")
    debug_print(f"[VIDEO INDEXER] Detected objects found: {len(detected_objects_data)}")
    debug_print(f"[VIDEO INDEXER] Insights extracted - Transcript: {len(transcript)}, OCR: {len(ocr_blocks)}, Keywords: {len(keywords_data)}, Labels: {len(labels_data)}, Topics: {len(topics_data)}, Audio: {len(audio_effects_data)}, Emotions: {len(emotions_data)}, Sentiments: {len(sentiments_data)}, People: {len(named_people_data)}, Locations: {len(named_locations_data)}, Objects: {len(detected_objects_data)}")
    
    if len(transcript) == 0:
        debug_print(f"[VIDEO INDEXER] WARNING: No transcript data available")
        debug_print(f"[VIDEO INDEXER] Available insights keys: {list(insights.keys())}")

    # Build context lists for transcript and OCR
    speech_context = [
        {"text": seg["text"].strip(), "start": inst["start"]}
        for seg in transcript if seg.get("text", "").strip()
        for inst in seg.get("instances", [])
    ]
    ocr_context = [
        {"text": block["text"].strip(), "start": inst["start"]}
        for block in ocr_blocks if block.get("text", "").strip()
        for inst in block.get("instances", [])
    ]
    
    # Build context lists for additional insights
    keywords_context = [
        {"text": kw.get("name", ""), "start": inst["start"]}
        for kw in keywords_data if kw.get("name", "").strip()
        for inst in kw.get("instances", [])
    ]
    labels_context = [
        {"text": label.get("name", ""), "start": inst["start"]}
        for label in labels_data if label.get("name", "").strip()
        for inst in label.get("instances", [])
    ]
    topics_context = [
        {"text": topic.get("name", ""), "start": inst["start"]}
        for topic in topics_data if topic.get("name", "").strip()
        for inst in topic.get("instances", [])
    ]
    audio_effects_context = [
        {"text": ae.get("audioEffectType", ""), "start": inst["start"]}
        for ae in audio_effects_data if ae.get("audioEffectType", "").strip()
        for inst in ae.get("instances", [])
    ]
    emotions_context = [
        {"text": emotion.get("type", ""), "start": inst["start"]}
        for emotion in emotions_data if emotion.get("type", "").strip()
        for inst in emotion.get("instances", [])
    ]
    sentiments_context = [
        {"text": sentiment.get("sentimentType", ""), "start": inst["start"]}
        for sentiment in sentiments_data if sentiment.get("sentimentType", "").strip()
        for inst in sentiment.get("instances", [])
    ]
    named_people_context = [
        {"text": person.get("name", ""), "start": inst["start"]}
        for person in named_people_data if person.get("name", "").strip()
        for inst in person.get("instances", [])
    ]
    named_locations_context = [
        {"text": location.get("name", ""), "start": inst["start"]}
        for location in named_locations_data if location.get("name", "").strip()
        for inst in location.get("instances", [])
    ]
    detected_objects_context = [
        {"text": obj.get("type", ""), "start": inst["start"]}
        for obj in detected_objects_data if obj.get("type", "").strip()
        for inst in obj.get("instances", [])
    ]

    debug_print(f"[VIDEO INDEXER] Speech context items: {len(speech_context)}")
    debug_print(f"[VIDEO INDEXER] OCR context items: {len(ocr_context)}")
    debug_print(f"[VIDEO INDEXER] Keywords context items: {len(keywords_context)}")
    debug_print(f"[VIDEO INDEXER] Labels context items: {len(labels_context)}")
    debug_print(f"[VIDEO INDEXER] Topics context items: {len(topics_context)}")
    debug_print(f"[VIDEO INDEXER] Audio effects context items: {len(audio_effects_context)}")
    debug_print(f"[VIDEO INDEXER] Emotions context items: {len(emotions_context)}")
    debug_print(f"[VIDEO INDEXER] Sentiments context items: {len(sentiments_context)}")
    debug_print(f"[VIDEO INDEXER] Named people context items: {len(named_people_context)}")
    debug_print(f"[VIDEO INDEXER] Named locations context items: {len(named_locations_context)}")
    debug_print(f"[VIDEO INDEXER] Detected objects context items: {len(detected_objects_context)}")
    debug_print(f"[VIDEO INDEXER] Context built - Speech: {len(speech_context)}, OCR: {len(ocr_context)}, Keywords: {len(keywords_context)}, Labels: {len(labels_context)}, People: {len(named_people_context)}, Locations: {len(named_locations_context)}, Objects: {len(detected_objects_context)}")
    
    if len(speech_context) > 0:
        debug_print(f"[VIDEO INDEXER] First speech item: {speech_context[0]}")

    # Sort all contexts by timestamp
    speech_context.sort(key=lambda x: to_seconds(x["start"]))
    ocr_context.sort(key=lambda x: to_seconds(x["start"]))
    keywords_context.sort(key=lambda x: to_seconds(x["start"]))
    labels_context.sort(key=lambda x: to_seconds(x["start"]))
    topics_context.sort(key=lambda x: to_seconds(x["start"]))
    audio_effects_context.sort(key=lambda x: to_seconds(x["start"]))
    emotions_context.sort(key=lambda x: to_seconds(x["start"]))
    sentiments_context.sort(key=lambda x: to_seconds(x["start"]))
    named_people_context.sort(key=lambda x: to_seconds(x["start"]))
    named_locations_context.sort(key=lambda x: to_seconds(x["start"]))
    detected_objects_context.sort(key=lambda x: to_seconds(x["start"]))

    debug_print(f"[VIDEO INDEXER] Starting 30-second chunk processing")
    debug_print(f"[VIDEO INDEXER] Starting time-based chunk processing - Video duration: {video_duration_seconds}s")
    debug_print(f"[VIDEO INDEXER] Available insights - Speech: {len(speech_context)}, OCR: {len(ocr_context)}, Keywords: {len(keywords_context)}, Labels: {len(labels_context)}")
    
    # Check if we have any content at all
    total_insights = len(speech_context) + len(ocr_context) + len(keywords_context) + len(labels_context) + len(topics_context) + len(audio_effects_context) + len(emotions_context) + len(sentiments_context) + len(named_people_context) + len(named_locations_context) + len(detected_objects_context)
    
    if total_insights == 0 and video_duration_seconds == 0:
        debug_print(f"[VIDEO INDEXER] ERROR: No insights and no duration information available")
        update_callback(status="VIDEO: no data available")
        return 0
    
    # Use video duration to create time-based chunks, even without speech
    if video_duration_seconds == 0:
        debug_print(f"[VIDEO INDEXER] WARNING: No video duration available, estimating from insights")
        # Estimate duration from the latest timestamp in any insight
        max_timestamp = 0
        for context_list in [speech_context, ocr_context, keywords_context, labels_context, topics_context, audio_effects_context, emotions_context, sentiments_context, named_people_context, named_locations_context, detected_objects_context]:
            if context_list:
                max_ts = max(to_seconds(item["start"]) for item in context_list)
                max_timestamp = max(max_timestamp, max_ts)
        video_duration_seconds = max_timestamp + 30  # Add buffer
        debug_print(f"[VIDEO INDEXER] Estimated duration: {video_duration_seconds}s")
    
    # Create chunks based on time intervals (30 seconds each)
    num_chunks = int(video_duration_seconds / 30) + (1 if video_duration_seconds % 30 > 0 else 0)
    debug_print(f"[VIDEO INDEXER] Will create {num_chunks} time-based chunks")
    
    total = 0
    idx_s = 0
    n_s = len(speech_context)
    idx_o = 0
    n_o = len(ocr_context)
    idx_kw = 0
    n_kw = len(keywords_context)
    idx_lbl = 0
    n_lbl = len(labels_context)
    idx_top = 0
    n_top = len(topics_context)
    idx_ae = 0
    n_ae = len(audio_effects_context)
    idx_emo = 0
    n_emo = len(emotions_context)
    idx_sent = 0
    n_sent = len(sentiments_context)
    idx_people = 0
    n_people = len(named_people_context)
    idx_locations = 0
    n_locations = len(named_locations_context)
    idx_objects = 0
    n_objects = len(detected_objects_context)
    
    # Process chunks in 30-second intervals based on video duration
    for chunk_num in range(num_chunks):
        window_start = chunk_num * 30.0
        window_end = min((chunk_num + 1) * 30.0, video_duration_seconds)
        
        debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} window: {window_start}s to {window_end}s")

        # Collect speech for this time window
        speech_lines = []
        while idx_s < n_s and to_seconds(speech_context[idx_s]["start"]) < window_end:
            if to_seconds(speech_context[idx_s]["start"]) >= window_start:
                speech_lines.append(speech_context[idx_s]["text"])
            idx_s += 1
            if idx_s < n_s and to_seconds(speech_context[idx_s]["start"]) >= window_end:
                break
        
        # Reset idx_s if we went past window_end
        while idx_s > 0 and idx_s < n_s and to_seconds(speech_context[idx_s]["start"]) >= window_end:
            idx_s -= 1
        if idx_s < n_s and to_seconds(speech_context[idx_s]["start"]) < window_end:
            idx_s += 1
        
        debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} speech lines collected: {len(speech_lines)}")

        # Collect OCR for this time window
        ocr_lines = []
        while idx_o < n_o and to_seconds(ocr_context[idx_o]["start"]) < window_end:
            if to_seconds(ocr_context[idx_o]["start"]) >= window_start:
                ocr_lines.append(ocr_context[idx_o]["text"])
            idx_o += 1
            if idx_o < n_o and to_seconds(ocr_context[idx_o]["start"]) >= window_end:
                break
        
        while idx_o > 0 and idx_o < n_o and to_seconds(ocr_context[idx_o]["start"]) >= window_end:
            idx_o -= 1
        if idx_o < n_o and to_seconds(ocr_context[idx_o]["start"]) < window_end:
            idx_o += 1
        
        debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} OCR lines collected: {len(ocr_lines)}")
        
        # Collect keywords for this time window
        chunk_keywords = []
        while idx_kw < n_kw and to_seconds(keywords_context[idx_kw]["start"]) < window_end:
            if to_seconds(keywords_context[idx_kw]["start"]) >= window_start:
                chunk_keywords.append(keywords_context[idx_kw]["text"])
            idx_kw += 1
            if idx_kw < n_kw and to_seconds(keywords_context[idx_kw]["start"]) >= window_end:
                break
        while idx_kw > 0 and idx_kw < n_kw and to_seconds(keywords_context[idx_kw]["start"]) >= window_end:
            idx_kw -= 1
        if idx_kw < n_kw and to_seconds(keywords_context[idx_kw]["start"]) < window_end:
            idx_kw += 1
        
        # Collect labels for this time window
        chunk_labels = []
        while idx_lbl < n_lbl and to_seconds(labels_context[idx_lbl]["start"]) < window_end:
            if to_seconds(labels_context[idx_lbl]["start"]) >= window_start:
                chunk_labels.append(labels_context[idx_lbl]["text"])
            idx_lbl += 1
            if idx_lbl < n_lbl and to_seconds(labels_context[idx_lbl]["start"]) >= window_end:
                break
        while idx_lbl > 0 and idx_lbl < n_lbl and to_seconds(labels_context[idx_lbl]["start"]) >= window_end:
            idx_lbl -= 1
        if idx_lbl < n_lbl and to_seconds(labels_context[idx_lbl]["start"]) < window_end:
            idx_lbl += 1
        
        # Collect topics for this time window
        chunk_topics = []
        while idx_top < n_top and to_seconds(topics_context[idx_top]["start"]) < window_end:
            if to_seconds(topics_context[idx_top]["start"]) >= window_start:
                chunk_topics.append(topics_context[idx_top]["text"])
            idx_top += 1
            if idx_top < n_top and to_seconds(topics_context[idx_top]["start"]) >= window_end:
                break
        while idx_top > 0 and idx_top < n_top and to_seconds(topics_context[idx_top]["start"]) >= window_end:
            idx_top -= 1
        if idx_top < n_top and to_seconds(topics_context[idx_top]["start"]) < window_end:
            idx_top += 1
        
        # Collect audio effects for this time window
        chunk_audio_effects = []
        while idx_ae < n_ae and to_seconds(audio_effects_context[idx_ae]["start"]) < window_end:
            if to_seconds(audio_effects_context[idx_ae]["start"]) >= window_start:
                chunk_audio_effects.append(audio_effects_context[idx_ae]["text"])
            idx_ae += 1
            if idx_ae < n_ae and to_seconds(audio_effects_context[idx_ae]["start"]) >= window_end:
                break
        while idx_ae > 0 and idx_ae < n_ae and to_seconds(audio_effects_context[idx_ae]["start"]) >= window_end:
            idx_ae -= 1
        if idx_ae < n_ae and to_seconds(audio_effects_context[idx_ae]["start"]) < window_end:
            idx_ae += 1
        
        # Collect emotions for this time window
        chunk_emotions = []
        while idx_emo < n_emo and to_seconds(emotions_context[idx_emo]["start"]) < window_end:
            if to_seconds(emotions_context[idx_emo]["start"]) >= window_start:
                chunk_emotions.append(emotions_context[idx_emo]["text"])
            idx_emo += 1
            if idx_emo < n_emo and to_seconds(emotions_context[idx_emo]["start"]) >= window_end:
                break
        while idx_emo > 0 and idx_emo < n_emo and to_seconds(emotions_context[idx_emo]["start"]) >= window_end:
            idx_emo -= 1
        if idx_emo < n_emo and to_seconds(emotions_context[idx_emo]["start"]) < window_end:
            idx_emo += 1
        
        # Collect sentiments for this time window
        chunk_sentiments = []
        while idx_sent < n_sent and to_seconds(sentiments_context[idx_sent]["start"]) < window_end:
            if to_seconds(sentiments_context[idx_sent]["start"]) >= window_start:
                chunk_sentiments.append(sentiments_context[idx_sent]["text"])
            idx_sent += 1
            if idx_sent < n_sent and to_seconds(sentiments_context[idx_sent]["start"]) >= window_end:
                break
        while idx_sent > 0 and idx_sent < n_sent and to_seconds(sentiments_context[idx_sent]["start"]) >= window_end:
            idx_sent -= 1
        if idx_sent < n_sent and to_seconds(sentiments_context[idx_sent]["start"]) < window_end:
            idx_sent += 1
        
        # Collect named people for this time window
        chunk_people = []
        while idx_people < n_people and to_seconds(named_people_context[idx_people]["start"]) < window_end:
            if to_seconds(named_people_context[idx_people]["start"]) >= window_start:
                chunk_people.append(named_people_context[idx_people]["text"])
            idx_people += 1
            if idx_people < n_people and to_seconds(named_people_context[idx_people]["start"]) >= window_end:
                break
        while idx_people > 0 and idx_people < n_people and to_seconds(named_people_context[idx_people]["start"]) >= window_end:
            idx_people -= 1
        if idx_people < n_people and to_seconds(named_people_context[idx_people]["start"]) < window_end:
            idx_people += 1
        
        # Collect named locations for this time window
        chunk_locations = []
        while idx_locations < n_locations and to_seconds(named_locations_context[idx_locations]["start"]) < window_end:
            if to_seconds(named_locations_context[idx_locations]["start"]) >= window_start:
                chunk_locations.append(named_locations_context[idx_locations]["text"])
            idx_locations += 1
            if idx_locations < n_locations and to_seconds(named_locations_context[idx_locations]["start"]) >= window_end:
                break
        while idx_locations > 0 and idx_locations < n_locations and to_seconds(named_locations_context[idx_locations]["start"]) >= window_end:
            idx_locations -= 1
        if idx_locations < n_locations and to_seconds(named_locations_context[idx_locations]["start"]) < window_end:
            idx_locations += 1
        
        # Collect detected objects for this time window
        chunk_objects = []
        while idx_objects < n_objects and to_seconds(detected_objects_context[idx_objects]["start"]) < window_end:
            if to_seconds(detected_objects_context[idx_objects]["start"]) >= window_start:
                chunk_objects.append(detected_objects_context[idx_objects]["text"])
            idx_objects += 1
            if idx_objects < n_objects and to_seconds(detected_objects_context[idx_objects]["start"]) >= window_end:
                break
        while idx_objects > 0 and idx_objects < n_objects and to_seconds(detected_objects_context[idx_objects]["start"]) >= window_end:
            idx_objects -= 1
        if idx_objects < n_objects and to_seconds(detected_objects_context[idx_objects]["start"]) < window_end:
            idx_objects += 1

        # Format timestamp as HH:MM:SS
        hours = int(window_start // 3600)
        minutes = int((window_start % 3600) // 60)
        seconds = int(window_start % 60)
        start_ts = f"{hours:02d}:{minutes:02d}:{seconds:02d}.000"
        
        chunk_text = " ".join(speech_lines).strip()
        ocr_text = " ".join(ocr_lines).strip()
        
        # Build enhanced chunk text with insights appended
        if chunk_text:
            # Has speech - append insights to it
            insight_parts = []
            if chunk_keywords:
                insight_parts.append(f"Keywords: {', '.join(chunk_keywords)}")
            if chunk_labels:
                insight_parts.append(f"Visual elements: {', '.join(chunk_labels)}")
            if chunk_topics:
                insight_parts.append(f"Topics: {', '.join(chunk_topics)}")
            if chunk_audio_effects:
                insight_parts.append(f"Audio: {', '.join(chunk_audio_effects)}")
            if chunk_emotions:
                insight_parts.append(f"Emotions: {', '.join(chunk_emotions)}")
            if chunk_sentiments:
                insight_parts.append(f"Sentiment: {', '.join(chunk_sentiments)}")
            if chunk_people:
                insight_parts.append(f"People: {', '.join(chunk_people)}")
            if chunk_locations:
                insight_parts.append(f"Locations: {', '.join(chunk_locations)}")
            if chunk_objects:
                insight_parts.append(f"Objects: {', '.join(chunk_objects)}")
            
            if insight_parts:
                chunk_text = f"{chunk_text}\n\n{' | '.join(insight_parts)}"
                debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} enhanced with {len(insight_parts)} insight types")
        else:
            # No speech - build chunk text from other insights
            insight_parts = []
            if ocr_text:
                insight_parts.append(f"Visual text: {ocr_text}")
            if chunk_keywords:
                insight_parts.append(f"Keywords: {', '.join(chunk_keywords)}")
            if chunk_labels:
                insight_parts.append(f"Visual elements: {', '.join(chunk_labels)}")
            if chunk_topics:
                insight_parts.append(f"Topics: {', '.join(chunk_topics)}")
            if chunk_audio_effects:
                insight_parts.append(f"Audio: {', '.join(chunk_audio_effects)}")
            if chunk_emotions:
                insight_parts.append(f"Emotions: {', '.join(chunk_emotions)}")
            if chunk_sentiments:
                insight_parts.append(f"Sentiment: {', '.join(chunk_sentiments)}")
            if chunk_people:
                insight_parts.append(f"People: {', '.join(chunk_people)}")
            if chunk_locations:
                insight_parts.append(f"Locations: {', '.join(chunk_locations)}")
            if chunk_objects:
                insight_parts.append(f"Objects: {', '.join(chunk_objects)}")
            
            chunk_text = ". ".join(insight_parts) if insight_parts else "[No content detected]"
            debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} has no speech, using insights as text: {chunk_text[:100]}...")

        debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} at timestamp {start_ts}")
        debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} text length: {len(chunk_text)}, OCR text length: {len(ocr_text)}")
        debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} insights - Keywords: {len(chunk_keywords)}, Labels: {len(chunk_labels)}, Topics: {len(chunk_topics)}, Audio: {len(chunk_audio_effects)}, Emotions: {len(chunk_emotions)}, Sentiments: {len(chunk_sentiments)}, People: {len(chunk_people)}, Locations: {len(chunk_locations)}, Objects: {len(chunk_objects)}")
        debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1}: timestamp={start_ts}, text_len={len(chunk_text)}, ocr_len={len(ocr_text)}, insights={len(chunk_keywords)}kw/{len(chunk_labels)}lbl/{len(chunk_topics)}top")
        
        # Skip truly empty chunks (no content at all)
        if chunk_text == "[No content detected]" and not any([chunk_keywords, chunk_labels, chunk_topics, chunk_audio_effects, chunk_emotions, chunk_sentiments, chunk_people, chunk_locations, chunk_objects]):
            debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} is completely empty, skipping")
            continue
        
        update_callback(current_file_chunk=chunk_num+1, status=f"VIDEO: saving chunk @ {start_ts}")
        
        try:
            debug_print(f"[VIDEO INDEXER] Calling save_video_chunk for chunk {chunk_num + 1}")
            save_video_chunk(
                page_text_content=chunk_text,
                ocr_chunk_text=ocr_text,
                start_time=start_ts,
                file_name=original_filename,
                user_id=user_id,
                document_id=document_id,
                group_id=group_id
            )
            debug_print(f"[VIDEO INDEXER] Chunk {chunk_num + 1} saved successfully")
            total += 1
        except Exception as e:
            debug_print(f"[VIDEO INDEXER] Failed to save chunk {chunk_num + 1}: {str(e)}")
            import traceback
            debug_print(f"[VIDEO INDEXER] Chunk save traceback: {traceback.format_exc()}")
    
    debug_print(f"[VIDEO INDEXER] Chunk processing complete - Total chunks saved: {total}")

    # Extract metadata if enabled and chunks were processed
    settings = get_settings()
    enable_extract_meta_data = settings.get('enable_extract_meta_data', False)
    if enable_extract_meta_data and total > 0:
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
            debug_print(f"Warning: Error extracting final metadata for video document {document_id}: {str(e)}")
            update_callback(status=f"Processing complete (metadata extraction warning)")

    update_callback(status=f"VIDEO: done, {total} chunks")
    return total



def _get_content_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    mapping = {
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.mp4': 'audio/mp4'
    }
    return mapping.get(ext, 'application/octet-stream')

def _split_audio_file(input_path: str, chunk_seconds: int = 540) -> List[str]:
    """
    Splits `input_path` into WAV segments of length `chunk_seconds` seconds,
    writing files like input_chunk_000.wav.
    Returns the list of generated WAV chunk file paths.
    Each chunk is re-encoded to PCM WAV (16kHz) for compatibility.
    """
    import ffmpeg_binaries as ffmpeg_bin  # Lazy import — heavy library
    ffmpeg_bin.init()
    import ffmpeg as ffmpeg_py  # Lazy import — heavy library

    base, _ = os.path.splitext(input_path)
    pattern = f"{base}_chunk_%03d.wav"

    try:
        (
            ffmpeg_py
            .input(input_path)
            .output(
                pattern,
                acodec='pcm_s16le',
                ar='16000',
                f='segment',
                segment_time=chunk_seconds,
                reset_timestamps=1,
                map='0'
            )
            .run(quiet=True, overwrite_output=True)
        )
    except Exception as e:
        debug_print(f"[Error] FFmpeg segmentation to WAV failed for '{input_path}': {e}")
        raise RuntimeError(f"Segmentation failed: {e}")

    chunks = sorted(glob.glob(f"{base}_chunk_*.wav"))
    if not chunks:
        debug_print(f"[Error] No WAV chunks produced for '{input_path}'.")
        raise RuntimeError(f"No chunks produced by ffmpeg for file '{input_path}'")
    debug_print(f"Produced {len(chunks)} WAV chunks: {chunks}")
    return chunks

# Azure Speech SDK helper to get speech config with fresh token
def _get_speech_config(settings, endpoint: str, locale: str):
    """Get speech config with fresh token"""
    if settings.get("speech_service_authentication_type") == "managed_identity":
        credential = DefaultAzureCredential()
        token = credential.get_token(cognitive_services_scope)
        speech_config = speechsdk.SpeechConfig(endpoint=endpoint)

        # Set the authorization token AFTER creating the config
        speech_config.authorization_token = token.token
    else:
        key = settings.get("speech_service_key", "")
        speech_config = speechsdk.SpeechConfig(endpoint=endpoint, subscription=key)

    speech_config.speech_recognition_language = locale
    debug_print(f"[Debug] Speech config obtained successfully", flush=True)
    return speech_config

def process_audio_document(
    document_id: str,
    user_id: str,
    temp_file_path: str,
    original_filename: str,
    update_callback,
    group_id=None,
    public_workspace_id=None
) -> int:
    """Transcribe an audio file via Azure Speech, splitting >10 min into WAV chunks."""
    from services.blob_service import upload_to_blob
    from services.chunk_service import save_video_chunk, save_chunks
    from services.document_service import update_document, get_document_metadata
    from services.metadata_service import extract_document_metadata

    settings = get_settings()
    if settings.get("enable_enhanced_citations", False):
        update_callback(status="Uploading audio for enhanced citations…")
        blob_path = upload_to_blob(
            temp_file_path,
            user_id,
            document_id,
            original_filename,
            update_callback,
            group_id,
            public_workspace_id
        )
        update_callback(status=f"Enhanced citations: audio at {blob_path}")


    # 1) size guard
    file_size = os.path.getsize(temp_file_path)
    debug_print(f"File size: {file_size} bytes")
    if file_size > 300 * 1024 * 1024:
        raise ValueError("Audio exceeds 300 MB limit.")

    # 2) split to WAV chunks
    update_callback(status="Preparing audio for transcription…")
    chunk_paths = _split_audio_file(temp_file_path, chunk_seconds=540)

    # 3) transcribe each WAV chunk
    settings = get_settings()
    endpoint = settings.get("speech_service_endpoint", "").rstrip('/')
    locale = settings.get("speech_service_locale", "en-US")

    all_phrases: List[str] = []

    # Fast Transcription API not yet available in sovereign clouds, so use SDK
    if AZURE_ENVIRONMENT in ("usgovernment", "custom"):
        for idx, chunk_path in enumerate(chunk_paths, start=1):
            debug_print(f"[Debug] Transcribing chunk {idx}: {chunk_path}")

            # Get fresh config (tokens expire after ~1 hour)
            try:
                speech_config = _get_speech_config(settings, endpoint, locale)
            except Exception as e:
                debug_print(f"[Error] Failed to get speech config for chunk {idx}: {e}")
                raise RuntimeError(f"Speech configuration failed for chunk {idx}: {e}")

            try:
                audio_config = speechsdk.AudioConfig(filename=chunk_path)
            except Exception as e:
                debug_print(f"[Error] Failed to load audio file {chunk_path}: {e}")
                raise RuntimeError(f"Audio file loading failed: {e}")

            try:
                speech_recognizer = speechsdk.SpeechRecognizer(
                    speech_config=speech_config,
                    audio_config=audio_config
                )
            except Exception as e:
                debug_print(f"[Error] Failed to create speech recognizer for chunk {idx}: {e}")
                raise RuntimeError(f"Speech recognizer creation failed: {e}")

            # Use continuous recognition instead of recognize_once
            all_results = []
            done = False
            error_occurred = False
            error_message = None
            
            def stop_cb(evt):
                nonlocal done
                debug_print(f"[Debug] Session stopped for chunk {idx}")
                done = True
            
            def recognized_cb(evt):
                try:
                    if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                        all_results.append(evt.result.text)
                        debug_print(f"[Debug] Recognized: {evt.result.text}")
                    elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                        debug_print(f"[Debug] No speech recognized in segment")
                except Exception as e:
                    debug_print(f"[Error] Error in recognized callback: {e}")
                    # Don't fail on individual recognition errors
            
            def canceled_cb(evt):
                nonlocal done, error_occurred, error_message
                debug_print(f"[Debug] Recognition canceled for chunk {idx}: {evt.cancellation_details.reason}")
                
                if evt.cancellation_details.reason == speechsdk.CancellationReason.Error:
                    error_occurred = True
                    error_message = evt.cancellation_details.error_details
                    debug_print(f"[Error] Recognition error: {error_message}")
                elif evt.cancellation_details.reason == speechsdk.CancellationReason.EndOfStream:
                    debug_print(f"[Debug] End of audio stream reached")
                
                done = True
            
            try:
                # Connect callbacks
                speech_recognizer.recognized.connect(recognized_cb)
                speech_recognizer.session_stopped.connect(stop_cb)
                speech_recognizer.canceled.connect(canceled_cb)
                
                # Start continuous recognition
                debug_print(f"[Debug] Starting continuous recognition for chunk {idx}")
                speech_recognizer.start_continuous_recognition()
                
                # Wait for completion with timeout
                import time
                timeout_seconds = 600  # 10 minutes max per chunk
                start_time = time.time()
                
                while not done:
                    if time.time() - start_time > timeout_seconds:
                        debug_print(f"[Error] Recognition timeout for chunk {idx}")
                        error_occurred = True
                        error_message = f"Recognition timed out after {timeout_seconds} seconds"
                        break
                    time.sleep(0.5)
                
                # Stop recognition
                try:
                    speech_recognizer.stop_continuous_recognition()
                    debug_print(f"[Debug] Stopped continuous recognition for chunk {idx}")
                except Exception as e:
                    debug_print(f"[Warning] Error stopping recognition for chunk {idx}: {e}")
                    # Continue even if stop fails
                
                # Check for errors after completion
                if error_occurred:
                    raise RuntimeError(f"Recognition failed for chunk {idx}: {error_message}")
                
                # Add all recognized phrases to the overall list
                if all_results:
                    all_phrases.extend(all_results)
                    debug_print(f"[Debug] Total phrases from chunk {idx}: {len(all_results)}")
                else:
                    debug_print(f"[Warning] No speech recognized in {chunk_path}")
                    # Continue to next chunk - empty result is not necessarily an error
                    
            except RuntimeError as e:
                # Re-raise runtime errors (these are our custom errors)
                raise
            except Exception as e:
                debug_print(f"[Error] Unexpected error during recognition for chunk {idx}: {e}")
                raise RuntimeError(f"Recognition failed unexpectedly for chunk {idx}: {e}")
            finally:
                # Cleanup: disconnect callbacks and dispose recognizer
                try:
                    speech_recognizer.recognized.disconnect_all()
                    speech_recognizer.session_stopped.disconnect_all()
                    speech_recognizer.canceled.disconnect_all()
                except Exception as e:
                    debug_print(f"[Warning] Error disconnecting callbacks for chunk {idx}: {e}")

            # # Get fresh config (tokens expire after ~1 hour)
            # speech_config = _get_speech_config(settings, endpoint, locale)

            # audio_config = speechsdk.AudioConfig(filename=chunk_path)
            # speech_recognizer = speechsdk.SpeechRecognizer(
            #     speech_config=speech_config,
            #     audio_config=audio_config
            # )

            # result = speech_recognizer.recognize_once()
            # if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            #     print(f"[Debug] Recognized: {result.text}")
            #     all_phrases.append(result.text)
            # elif result.reason == speechsdk.ResultReason.NoMatch:
            #     print(f"[Warning] No speech in {chunk_path}")
            # elif result.reason == speechsdk.ResultReason.Canceled:
            #     print(f"[Error] {result.cancellation_details.reason}: {result.cancellation_details.error_details}")
            #     raise RuntimeError(f"Transcription canceled for {chunk_path}: {result.cancellation_details.error_details}")

    else:
        # Use the fast-transcription API if not in sovereign or custom cloud
        url = f"{endpoint}/speechtotext/transcriptions:transcribe?api-version=2024-11-15"
        for idx, chunk_path in enumerate(chunk_paths, start=1):
            update_callback(current_file_chunk=idx, status=f"Transcribing chunk {idx}/{len(chunk_paths)}…")
            debug_print(f"[Debug] Transcribing WAV chunk: {chunk_path}")

            with open(chunk_path, 'rb') as audio_f:
                files = {
                    'audio': (os.path.basename(chunk_path), audio_f, 'audio/wav'),
                    'definition': (None, json.dumps({'locales':[locale]}), 'application/json')
                }
                if settings.get("speech_service_authentication_type") == "managed_identity":
                    credential = DefaultAzureCredential()
                    token = credential.get_token(cognitive_services_scope)
                    headers = {'Authorization': f'Bearer {token.token}'}
                else:
                    key = settings.get("speech_service_key", "")
                    headers = {'Ocp-Apim-Subscription-Key': key}
                
                resp = requests.post(url, headers=headers, files=files)
            try:
                resp.raise_for_status()
            except Exception as e:
                debug_print(f"[Error] HTTP error for {chunk_path}: {e}")
                raise

            result = resp.json()
            phrases = result.get('combinedPhrases', [])
            debug_print(f"[Debug] Received {len(phrases)} phrases")
            all_phrases += [p.get('text','').strip() for p in phrases if p.get('text')]

    # 4) cleanup WAV chunks
    for p in chunk_paths:
        try:
            os.remove(p)
            debug_print(f"Removed chunk: {p}")
        except Exception as e:
            debug_print(f"[Warning] Could not remove chunk {p}: {e}")

    # 5) stitch and save transcript chunks
    full_text = ' '.join(all_phrases).strip()
    words = full_text.split()
    chunk_size = 400
    total_pages = max(1, math.ceil(len(words) / chunk_size))
    debug_print(f"Creating {total_pages} transcript pages")

    for i in range(total_pages):
        page_text = ' '.join(words[i*chunk_size:(i+1)*chunk_size])
        update_callback(current_file_chunk=i+1, status=f"Saving transcript chunk {i+1}/{total_pages}…")
        save_chunks(
            page_text_content=page_text,
            page_number=i+1,
            file_name=original_filename,
            user_id=user_id,
            document_id=document_id,
            group_id=group_id
        )

    # Extract metadata if enabled and chunks were processed
    settings = get_settings()
    enable_extract_meta_data = settings.get('enable_extract_meta_data', False)
    if enable_extract_meta_data and total_pages > 0:
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
            debug_print(f"Warning: Error extracting final metadata for audio document {document_id}: {str(e)}")
            update_callback(status=f"Processing complete (metadata extraction warning)")
    else:
        update_callback(number_of_pages=total_pages, status="Audio transcription complete", percentage_complete=100, current_file_chunk=None)

    debug_print("[Info] Audio transcription complete")
    return total_pages
