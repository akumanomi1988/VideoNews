"""Owner-managed, explicit commercial-license music catalog. Never downloads media."""
import hashlib
import json
from pathlib import Path

CATEGORIES = ('Science & Space', 'Technology', 'Economy', 'Documentary',
              'General News', 'Dramatic / Tension', 'Neutral Ambient')
MOODS = ('ambient', 'cinematic', 'minimal', 'dramatic', 'none')


class MusicLibrary:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def tracks(self):
        catalog = self.root / 'catalog.json'
        if not catalog.is_file():
            return []
        items = json.loads(catalog.read_text(encoding='utf-8'))
        required = {'id', 'name', 'author', 'file', 'duration', 'category', 'intensity',
                    'license', 'source', 'attribution', 'commercial_use', 'moods'}
        seen = set()
        for item in items:
            if set(item) != required or item['id'] in seen:
                raise ValueError('Invalid music catalog fields or duplicate ID')
            seen.add(item['id'])
            path = (self.root / item['file']).resolve()
            if not path.is_relative_to(self.root) or not path.is_file():
                raise ValueError('Music file missing or outside library')
            if (item['category'] not in CATEGORIES or type(item['commercial_use']) is not bool
                    or not 0 <= item['intensity'] <= 1 or item['duration'] <= 0
                    or not item['license'] or not item['source'] or not item['author']
                    or not item['moods'] or any(m not in MOODS[:-1] for m in item['moods'])):
                raise ValueError('Invalid music rights or selection data')
        return items

    def select(self, mood='ambient', category='Neutral Ambient', track_id=None):
        if mood not in MOODS or category not in CATEGORIES:
            raise ValueError('Unsupported music selection')
        if mood == 'none':
            return {'track': None, 'reason': 'Music explicitly disabled'}
        candidates = [t for t in self.tracks() if t['commercial_use'] and
                      (t['id'] == track_id if track_id else t['category'] == category and mood in t['moods'])]
        if not candidates:
            return {'track': None, 'reason': 'No compatible commercially authorized track; no substitution'}
        chosen = sorted(candidates, key=lambda t: (t['intensity'], t['id']))[0]
        path = (self.root / chosen['file']).resolve()
        return {'track': dict(chosen, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()),
                'reason': 'Deterministic selection from owner-authorized catalog'}
