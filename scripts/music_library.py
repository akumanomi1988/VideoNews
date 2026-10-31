"""Owner-managed, explicit commercial-license music catalog. Never downloads media."""
import hashlib
import json
import math
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
        if not isinstance(items, list):
            raise ValueError('Music catalog must be an array')
        required = {'id', 'name', 'author', 'file', 'duration', 'category', 'intensity',
                    'license', 'source', 'attribution', 'commercial_use', 'moods'}
        seen = set()
        for item in items:
            if not isinstance(item, dict) or set(item) != required:
                raise ValueError('Invalid music catalog fields')
            if any(not isinstance(item[k], str) for k in ('id','name','author','file','license','source','attribution')):
                raise ValueError('Music text fields must be strings')
            if not item['id'] or item['id'] in seen:
                raise ValueError('Invalid music catalog fields or duplicate ID')
            seen.add(item['id'])
            path = (self.root / item['file']).resolve()
            if not path.is_relative_to(self.root) or not path.is_file():
                raise ValueError('Music file missing or outside library')
            if (type(item['intensity']) not in (int,float) or not math.isfinite(item['intensity'])
                    or type(item['duration']) not in (int,float) or not math.isfinite(item['duration'])
                    or not isinstance(item['moods'], list)
                    or item['category'] not in CATEGORIES or type(item['commercial_use']) is not bool
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

    def verify_selection(self, selection):
        """Recheck rights, bytes and catalog membership; never silently reselect."""
        saved = selection.get('track')
        if saved is None:
            return None
        current = self.select(track_id=saved['id'])['track']
        if not current or current != saved:
            raise ValueError('Selected music changed or authorization was revoked; select again explicitly')
        return current['path']
