"""Ensure presets retain the editorial scene instead of substituting generic art."""
from unittest.mock import Mock

import pytest

from scripts.AI.text_to_image import AspectRatio, FluxImageGenerator, StylePreset


@pytest.mark.parametrize("style", [StylePreset.NEWSPHERE_CINEMATIC,
                                  StylePreset.YOUTUBE_THUMBNAIL, StylePreset.NONE])
def test_provider_receives_each_requested_subject_and_orientation(tmp_path, monkeypatch, style):
    generator = FluxImageGenerator(output_dir=str(tmp_path))
    monkeypatch.setattr(generator, "preflight", lambda: None)
    provider = Mock(return_value="generated.png")
    monkeypatch.setattr(generator, "_generate_with_azure", provider)
    scenes = [("A precision gauge aligned with a panel seam", AspectRatio.LANDSCAPE),
              ("An overhead physical workflow with a missing connection", AspectRatio.SHORTS)]
    for prompt, ratio in scenes:
        assert generator.generate_image(prompt, style, ratio) == "generated.png"
        actual, width, height = provider.call_args.args
        assert actual.startswith(prompt)
        assert (width, height) == ratio.value
    assert provider.call_count == 2
