# NewSphere visual direction

Read this before writing a storyboard or revising image prompts. ChatGPT authors
the visual concepts; Python validates and executes them without a second LLM call.

## Design the sequence before individual prompts

Write a one-line visual beat for each narration segment: what new idea becomes
visible, why that image explains this sentence, and how it differs from the previous
scene. A person looking at an AI screen cannot illustrate every idea about AI.

Increase meaningful information density. Identify the precise narrated concept,
then choose a main action and roughly three to five relevant supporting details:
a tool or object, a setting clue, an interaction, a visible process or comparison.
Explain how they relate in space. Build foreground action, midground process and
background context around one clear focal point. Do not add objects merely to
fill the frame; an attractive image that could accompany an unrelated story fails.
An empty room, bag, blank phone or anonymous monitor is not a default substitute
for explaining a mechanism. Reserve such symbolic shots for an actual narrative role.
If sources do not establish a technical device's appearance, use a clear original
functional diagram rather than fabricating precise-looking hardware.

For a seven-scene sequence, aim for at least four shot families: establishing wide,
human-scale action, macro detail, overhead evidence arrangement, process cutaway,
or an explicitly conceptual tableau. This is an editorial planning heuristic, not
an automated quality score. Do not force variety that misrepresents the topic.
Avoid more than two consecutive scenes with the same subject, location and framing.
Alternate scale and viewpoint at meaningful narrative turns, rather than at random.

Keep a short continuity bible: photographic realism versus graphic illustration,
material texture, contrast, brand accents, and recurring objects where relevant.
Keep that treatment consistent. Vary natural location colors and lighting: daylight,
warm practicals, neutral workshop light and restrained cyan accents can coexist.
The brand is not a requirement to make every scene a dark office with a blue screen.

## Prompt construction

Write prompts in English, with this order:

1. **Visible idea:** one specific subject performing one readable action; name the
   object or spatial relationship that makes it relevant to the narration.
2. **Place and depth:** foreground, focal plane and background; use details that
   explain the scene rather than decorating it.
   Say what each supporting object reveals about the narrated point. Describe
   purposeful activity and material texture, not a list of cinematic adjectives.
3. **Camera and composition:** shot size, viewpoint and lens character when useful;
   specify landscape 16:9 or portrait 9:16 from the approved brief, focal position,
   room for restrained camera movement and an unobtrusive subtitle-safe area.
4. **Light and texture:** motivated light and believable materials, chosen for that
   scene. Do not repeat the same long style paragraph inside every prompt.
5. **Truth boundary:** label metaphors and synthetic illustrations explicitly.
   Do not recreate named people's unverified actions or pass invented imagery off
   as a real company, location or incident. No fake logos or documentary claims.
6. **Useful exclusions:** only likely failure modes, such as generated lettering,
   an unwanted portrait panel or cartoon rendering. Avoid a generic negative list.

Put the visual explanation in `visual_concept`, camera-safe placement in
`composition`, and source-backed limits in `documented_facts`. Keep narration exact.
Set `semantic_review_required` to true: an attractive image is not factual proof.
Use `on_screen_text`/deterministic overlays for exact numbers and wording. Never
ask the image generator to invent a chart, map, survey sample or readable data.

## Example: AI and the limits of replacing human knowledge

Weak: "A professional looks at a glowing AI screen in a modern office. Cinematic,
ultra detailed, dramatic, navy and cyan."

**Context as a visual metaphor:**
"Horizontal 16:9 conceptual editorial still, clearly a constructed metaphor:
an overhead view of a physical workflow model on a pale workbench, a precise cyan
route reaches a missing connection; a human hand places a worn amber connector
across the gap. The connector's texture contrasts with the immaculate model.
One clear focal point, tactile paper and metal surfaces, soft daylight from the
left, shallow shadows, lower margin kept uncluttered within the workbench. No
letters, numerical chart, holograms or blank caption panel. Synthetic illustration
of context supplied by people, not a real company process or proof of AI failure."

**A different shot for the engineering example:**
"Horizontal 16:9 synthetic editorial film still in a fictional automotive inspection
workshop: a macro side view of an experienced technician's fingers aligning a
precision gauge with a panel seam. The gauge and seam occupy the focal plane;
an out-of-focus optical inspection rig establishes the wider process behind them.
Neutral workshop light reveals brushed metal and skin texture, with a restrained
cyan reflection and warm task light. Leave the lower center quiet for captions.
No badge, readable display, damaged vehicle or recognizable employee. Illustrative
human inspection alongside automation, not documentary footage of Ford."

The survey scene should use a clearly designed evidence graphic or a different
visual construction; it should not reuse the workshop, the same man, or another
monitor. Precise percentages and attribution are composed by the renderer.

## Editorial rejection pass

Before generating, read the sequence as a contact sheet in your mind. Replace a
prompt if it merely repeats narration, adds a screen to fill space, duplicates the
previous composition, or would fit any unrelated news story. Remove unsupported
drama, stereotyped subjects and sensational catastrophe. The hook should raise a
specific visual question; it must not exaggerate the evidence.

After generation, inspect the actual contact sheet for style drift, irrelevant
objects, anatomy, unintended lettering, crop, repetition and semantic fit. Change
only the failing scene, retain the others, and inspect the new result. Never mark
this subjective review as passed just because image generation or technical QA passed.
