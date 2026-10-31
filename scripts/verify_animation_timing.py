"""Verify acoustic frame-clock drift and actual final-MP4 scene content."""
import json
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scripts.studio_mcp import VideoNewsStudio
from scripts.video_assembler import VideoAssembler
from scripts.atomic_storage import write_json


def main():
    evidence=json.loads(Path('output/av_upgrade/complete_acceptance.json').read_text(encoding='utf-8'))
    studio=VideoNewsStudio();project=studio.get_project(evidence['project_id']);folder=studio._dir(project['id'])
    duration=studio._probe_duration(Path(project['voice']))
    durations=studio._scene_image_durations(project,duration)
    counts=VideoAssembler._allocate_frame_counts(durations,round(duration*24))
    offsets={};acoustic=rendered=0.
    for scene,seconds,count in zip(project['storyboard'],durations,counts):
        offsets[scene['id']]=(acoustic,rendered);acoustic+=seconds;rendered+=count/24
    comparisons=[]
    for scene in evidence['animations']:
        spoken_start,frame_start=offsets[scene['scene_id']]
        spec=scene['resolved'];clip_duration=studio._probe_duration(Path(scene['animation']))
        assert abs(clip_duration-spec['duration'])<=1/24+.001
        assert abs(frame_start-spoken_start)<=1/24
        for i,(phrase,cue) in enumerate(zip(spec['cue_phrases'],spec['cue_seconds'])):
            local=min(spec['duration']-.1,cue+.8)
            paths=[]
            for name,video,at in [('final',project['video'],frame_start+local),('clip',scene['animation'],local)]:
                path=folder/f"verify_{scene['scene_id']}_{i}_{name}.png"
                subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-ss',str(at),'-i',video,'-frames:v','1',
                    '-vf','crop=iw:ih*0.72:0:0,scale=480:-1',str(path)],capture_output=True,check=True,timeout=30)
                paths.append(path)
            a,b=[np.asarray(Image.open(p).convert('RGB'),dtype=float) for p in paths]
            difference=float(np.mean(np.abs(a-b)))
            assert difference<8,(scene['scene_id'],difference)
            comparisons.append({'scene':scene['scene_id'],'phrase':phrase,'acoustic_seconds':spoken_start+cue,
                'rendered_seconds':frame_start+cue,'drift_seconds':frame_start-spoken_start,
                'frame_pixel_mean_absolute_error':difference})
    write_json(folder/'animation_validation.json',{'method':'Acoustic SRT versus quantized frame clock and final MP4 pixels',
        'checks':comparisons,'passed':True})
    print(json.dumps(comparisons,ensure_ascii=True))


if __name__=='__main__':main()
