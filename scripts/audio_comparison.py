"""Matched-loudness listening copies; never replaces project narration or master."""
import json
from pathlib import Path
from scripts.audio_engine import export_audio


def main():
    report=json.loads(Path('output/av_upgrade/complete_acceptance.json').read_text(encoding='utf-8'))
    project=Path('output/studio')/report['project_id']
    original=Path('output/studio/a32e5c2505fc454d96c3f734f3b3a469')
    root=Path('output/av_upgrade/complete_comparison');root.mkdir(exist_ok=True)
    measurements={}
    for label,source in [('A_raw',original/'narration.wav'),('B_legacy_mp3',original/'narration.mp3'),
                         ('C_project_master',project/'mastered.wav')]:
        measurements[label]=export_audio(source,root/(label+'.wav'))
    (root/'measurements.json').write_text(json.dumps(measurements,indent=2),encoding='utf-8')
    print('Matched -16 LUFS comparison copies saved; subjective quality is not certified.')


if __name__=='__main__':main()
