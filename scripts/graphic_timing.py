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
    phrases=specification.get('cue_phrases',[])
    if phrases:
        occurrences=specification.get('cue_occurrences',[])
        if len(phrases)!=len(specification['items']) or occurrences and len(occurrences)!=len(phrases):
            raise ValueError('Each animation item requires a spoken phrase and optional occurrence')
        scene_words=[w for w,t in events[first:last]];resolved=[];previous_end=0
        for n,phrase in enumerate(phrases):
            tokens=re.findall(r'[^\W_]+',phrase.casefold())
            matches=[i for i in range(len(scene_words)-len(tokens)+1) if tokens and scene_words[i:i+len(tokens)]==tokens]
            if not matches:raise ValueError(f'Unresolved animation phrase: {phrase}')
            if not occurrences and len(matches)!=1:raise ValueError(f'Ambiguous animation phrase: {phrase}; provide occurrence')
            occurrence=occurrences[n] if occurrences else 1
            if type(occurrence)!=int or not 1<=occurrence<=len(matches):raise ValueError('Invalid phrase occurrence')
            selected=matches[occurrence-1]
            if selected<previous_end:raise ValueError('Animation phrases overlap or are out of spoken order')
            previous_end=selected+len(tokens)
            resolved.append(selected)
        if indices and indices!=resolved:raise ValueError('Phrase and word indices conflict')
        indices=resolved
    if (len(indices)!=len(specification['items']) or any(type(i)!=int or not 0<=i<last-first for i in indices)
            or indices!=sorted(set(indices))):
        raise ValueError('Each animated item needs a distinct ordered scene-relative cue_word_indices entry')
    cues=[events[first+i][1]-start for i in indices]
    supplied=specification.get('cue_seconds',[])
    if supplied and (len(supplied)!=len(cues) or any(abs(a-b)>1/24 for a,b in zip(supplied,cues))):
        raise ValueError('Explicit cues disagree with acoustic word boundaries')
    return dict(specification,cue_word_indices=indices,cue_seconds=cues,duration=end-start)
