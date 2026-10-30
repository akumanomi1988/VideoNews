# Scene and output aspect-ratio consistency

Changing the approved brief from portrait to landscape previously invalidated
the render and thumbnail but retained portrait scene assets. FFmpeg also applied
`zoompan` output dimensions before fitting the source canvas, which could stretch
subjects when source and output proportions differed. Panning could exceed the
available horizontal crop range and clamp part of the movement.

The corrected workflow invalidates visual assets and scene asset IDs on a format
change, rejects contradictory scene prompts and incorrectly proportioned provider
results, and rejects opposite-orientation visuals before rendering. FFmpeg scales
and crops without stretching before camera motion, limits panning to the available
crop range, and writes square pixels and a defined display aspect ratio.

Regression coverage includes a real FFmpeg render in both orientations with a
circular subject: decoded subject width and height must agree within 4%, and
ffprobe must report the expected raster dimensions, SAR 1:1 and matching DAR.
Additional tests cover aspect-only brief revisions and wrong-ratio image-provider
responses. The Windows suite passed 374 tests with one skipped.

The real horizontal acceptance project is `282e390590c840cd8f2cdb0a5298abec`.
It reuses the existing Spanish narration and creates seven new Azure MAI images
at the provider-supported horizontal size 1360x768. This differs from exact 16:9
by less than 0.4%; the renderer crops that small excess to the final 1920x1080
canvas without stretching. No portrait images or Pexels assets are used.

Artifacts are stored in that project's directory under `output/studio/`:
`NewSphere_16x9_1920x1080.mp4`, `frame_16x9.png`, `qa_contact_sheet.jpg`,
`thumbnail.jpg` and `quality_acceptance.json`. The JSON report records measured
output properties. The existing public YouTube upload is not modified.

The completed file measured 1920x1080, DAR 16:9, SAR 1:1, 24 FPS, yuv420p,
67.625 seconds, -16.5 LUFS and -4.5 dBTP. Full decoding found no black intervals
or errors, and audio/video stream-duration drift was approximately 12 ms.
The final seven-scene contact sheet and a full-resolution second-scene frame
were visually inspected: images occupy landscape compositions, subjects retain
their proportions and the sampled subtitles are legible. No new upload occurred.
