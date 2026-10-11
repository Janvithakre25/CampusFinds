import re
from app.db import query_db

def find_similar_items(item_id, item_type, category, title, description, limit=4):
    """
    Finds potentially matching items:
    - If current item is 'lost', search for open 'found' items.
    - If current item is 'found', search for open 'lost' items.
    Uses category match + keyword frequency from title & description.
    Simple, fast, and 100% free with no paid external APIs.
    """
    opposite_type = 'found' if item_type == 'lost' else 'lost'

    # Extract distinct alphanumeric keywords (length >= 4)
    words = re.findall(r'[a-zA-Z0-9]{4,}', f"{title} {description}".lower())
    # Exclude common stop words
    stop_words = {'with', 'this', 'that', 'from', 'have', 'lost', 'found', 'near', 'some', 'desk', 'room', 'area', 'floor'}
    keywords = list({w for w in words if w not in stop_words})[:8]

    # Fetch candidate items of the opposite type that are currently 'open'
    candidates = query_db(
        """
        SELECT i.*, u.full_name as reporter_name
        FROM items i
        JOIN users u ON i.user_id = u.id
        WHERE i.item_type = %s AND i.status = 'open' AND i.id != %s
        ORDER BY i.created_at DESC
        LIMIT 50
        """,
        (opposite_type, item_id)
    )

    if not candidates:
        return []

    scored_candidates = []
    for candidate in candidates:
        score = 0
        cand_text = f"{candidate['title']} {candidate['description']} {candidate['location']}".lower()

        # Same category gives a strong bonus
        if candidate['category'].lower() == category.lower():
            score += 5

        # Check keyword presence
        for kw in keywords:
            if kw in cand_text:
                score += 2

        if score > 0:
            scored_candidates.append({
                'item': candidate,
                'score': score
            })

    # Sort descending by score
    scored_candidates.sort(key=lambda x: x['score'], reverse=True)
    return [sc['item'] for sc in scored_candidates[:limit]]
