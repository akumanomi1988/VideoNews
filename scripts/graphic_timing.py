"""Resolve scene animation cues against actual TTS word events."""
import re
from scripts.MediaManagers.SRT_Processor import SRTProcessor


def bind_timing(project, scene_id, specification, audio_duration):
    events=[(word,e['start']) for e in SRTProcessor(project['word_boundaries']).parse_srt()
            for word in re.findall(r'[^\W_]+',e['text'].casefold())]
    scenes=project['storyboard']; cursor=0; ranges={}
    for scene in scenes:
        words=re.findall(r'[^\W_]+',scene['narration'].casefold())
        if not words or [w for w,t in events[cursor:cursor+len(words)]]!=words:
            raise ValueError('Storyboard must match the current acoustic word transcript exactly')
        ranges[scene['id']]=(cursor,cursor+len(words));cursor+=len(words)
    if cursor!=len(events):
        raise ValueError('Storyboard does not cover the complete word transcript')
    first,last=ranges[scene_id]
    start=events[first][1] if first else 0.
    end=events[last][1] if last<len(events) else audio_duration
    indices=specification.get('cue_word_indices',[])
    if (len(indices)!=len(specification['items']) or any(type(i)!=int or not 0<=i<last-first for i in indices)
            or indices!=sorted(set(indices))):
        raise ValueError('Each animated item needs a distinct ordered scene-relative cue_word_indices entry')
    cues=[events[first+i][1]-start for i in indices]
    supplied=specification.get('cue_seconds',[])
    if supplied and (len(supplied)!=len(cues) or any(abs(a-b)>1/24 for a,b in zip(supplied,cues))):
        raise ValueError('Explicit cues disagree with acoustic word boundaries')
    return dict(specification,cue_seconds=cues,duration=end-start)
