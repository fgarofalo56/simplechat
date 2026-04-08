# masking.py
# Utility functions for masking and unmasking content in chat messages.
# Extracted from route_backend_chats.py — Phase 4 God File Decomposition.


def merge_masked_ranges(ranges):
    """
    Merge overlapping and adjacent masked ranges.
    Preserves the earliest timestamp and user info for merged ranges.
    """
    if not ranges:
        return []

    # Sort by start position
    sorted_ranges = sorted(ranges, key=lambda x: x['start'])
    merged = [sorted_ranges[0]]

    for current in sorted_ranges[1:]:
        last_merged = merged[-1]

        # Check if current range overlaps or is adjacent to the last merged range
        if current['start'] <= last_merged['end']:
            # Merge: extend the end if current goes further
            if current['end'] > last_merged['end']:
                last_merged['end'] = current['end']
                # Update text to cover merged range
                last_merged['text'] = last_merged['text'] + current['text'][last_merged['end'] - current['start']:]
            # Keep the earliest timestamp
            if current['timestamp'] < last_merged['timestamp']:
                last_merged['timestamp'] = current['timestamp']
        else:
            # No overlap, add as separate range
            merged.append(current)

    return merged


def remove_masked_content(content, masked_ranges):
    """
    Remove masked portions from message content.
    Works backwards through sorted ranges to maintain correct offsets.
    """
    if not masked_ranges or not content:
        return content

    # Sort ranges by start position (descending) to work backwards
    sorted_ranges = sorted(masked_ranges, key=lambda x: x['start'], reverse=True)

    # Create a list from content for easier manipulation
    result = content

    # Remove masked ranges working backwards to maintain offsets
    for range_item in sorted_ranges:
        start = range_item['start']
        end = range_item['end']

        # Ensure indices are within bounds
        if start < 0:
            start = 0
        if end > len(result):
            end = len(result)

        # Remove the masked portion
        if start < end:
            result = result[:start] + result[end:]

    return result
