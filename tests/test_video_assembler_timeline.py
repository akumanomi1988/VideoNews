from scripts.video_assembler import VideoAssembler


def test_scene_frame_counts_follow_voice_duration():
    assert VideoAssembler._allocate_frame_counts([1.0, 2.0, 1.0], 96) == [24, 48, 24]


def test_scene_frame_counts_cover_output_exactly():
    counts = VideoAssembler._allocate_frame_counts([0.15, 0.35, 0.5], 101)
    assert len(counts) == 3
    assert sum(counts) == 101
    assert all(count > 0 for count in counts)
