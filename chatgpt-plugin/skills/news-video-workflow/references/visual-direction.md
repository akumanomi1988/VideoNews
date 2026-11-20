# NewSphere visual direction

Read this before writing a storyboard or revising image prompts. The active agent authors
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

Keep a short continuity bible: the approved illustration style, material texture,
contour weight, palette and recurring objects where relevant. The default
NewSphere style is `RUBBER_HOSE` (see below), so keep cream, mustard, terracotta
and faded teal across the sequence, with thick black ink contours and sepia
grain. Vary natural location props and lighting beats inside that palette:
daylight, warm practicals, harbour haze and night lamps can coexist. The style is
not a requirement to make every scene a brown sepia postcard.

## Current NewSphere style: Rubber Hose

Pass `style="RUBBER_HOSE"` to `generate_images` and state the intent in each
`visual_prompt`; the preset supplies the rendering language, not the story.

- 1930s rubber-hose cartoon: noodle limbs, white four-fingered gloves, oval
  shoes, pie-cut or dot eyes, squash-and-stretch poses.
- Hand-inked cel look: thick black contours, flat cel shading, light halftone,
  sepia grain and soft vignette; cream, mustard, terracotta, faded teal.
- Every scene keeps this look. Do not mix in photorealism, 3D renders, anime or
  modern vector flat design.
- People are anonymous vintage cartoon characters, never portraits of real,
  identifiable individuals and never caricatures of victims or protected groups.
- No lettering, logos, watermarks, UI, charts or readable data inside the image;
  add exact numbers and labels through GraphicsEngine.
- When the story involves death, injury, rescue or distress, keep the frame
  respectful: wide distance, backs turned, empty objects, weather, coastlines and
  maps instead of comic suffering. Gravity and restraint, not slapstick.

## Write news-specific prompts, not generic art

A prompt fails when it could illustrate any story in the feed. Before writing it,
extract from the reporting: who acts, how many, where, when, wearing what, what
object is involved, what visibly changes. Then build the frame around those
details.

Use this order, one or two sentences per block:

1. `[Shot and place]` — e.g. "Horizontal 16:9 wide shot of a steep volcanic dock
   at dawn".
2. `[Specific action and count]` — the exact action with numbers when the story
   gives them: "three red rescue boats alongside a wooden cayuco with nineteen
   people aboard, two crew helping a child step off".
3. `[Story objects and local detail]` — named gear, clothing, terrain, weather:
   "orange life vests, white helmets, wet black rocks, low sea mist, a Spanish
   Red Cross van parked uphill".
4. `[Composition and camera]` — focal point, foreground/midground/background,
   movement room, subtitle-safe margin.
5. `[Light, texture, mood]` — motivated light and materials, not a list of
   adjectives.
6. `[Truth boundary]` — "synthetic illustration, anonymous vintage cartoon
   characters, no real identifiable people" plus scene-specific exclusions.

Bad: "A dramatic scene about immigration in Spain. Cinematic, emotional, highly
detailed."

Good: "Horizontal 16:9 wide shot of a Canary Island volcanic dock at first light:
two rescue workers in mustard overalls and white gloves steady a small wooden
boat while a third counts arrivals with a clipboard; nineteen simplified
passengers wait in a line on wet black rock, one child holding a red bag. Cream
sky, faded teal sea, sepia grain, thick ink contours. Foreground boat, midground
rescue line, background volcanic slope with a small white van. Keep the lower
third quiet for captions. Synthetic 1930s rubber-hose illustration, anonymous
vintage cartoon characters, not documentary footage, no logos or readable text."

If the reporting does not give a detail, do not invent it. Use a functional map,
timeline or diagram instead; `generate_graphic` keeps exact numbers and
attribution.

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
5. **Truth boundary:** describe metaphors and illustrations as such in the storyboard and prompts.
   Do not recreate named people's unverified actions or pass invented imagery off
   as a real company, location or incident. No fake logos or documentary claims.
6. **Useful exclusions:** only likely failure modes for this scene, such as
   generated lettering, an unwanted portrait panel, extra limbs or photographic
   realism. Avoid a generic negative list.

Put the visual explanation in `visual_concept`, camera-safe placement in
`composition`, and source-backed limits in `documented_facts`. Keep narration exact.
Set `semantic_review_required` to true: an attractive image is not factual proof.
Use `on_screen_text`/deterministic overlays for exact numbers and wording. Never
ask the image generator to invent a chart, map, survey sample or readable data.
Do not request blank white boards, empty caption panels or fake dashboards to be
filled later unless a supported composition step will actually fill them. For a
data scene, use `generate_graphic` with registered sources and inspect its output
before rendering. If a layout rejects dense text, shorten labels or split the
explanation into supported panels without dropping attribution or changing values.
Use acoustically resolved narration cues for animation; static graphics are valid
when motion adds no explanation. Check that generated graphic text remains safe
after subtitles and any final framing are applied.

## NewSphere GraphicsEngine: layout and motion

This applies to deterministic charts, maps, cards and diagrams made with
`generate_graphic`, not to Azure image prompts. The renderer shares the
illustration palette: warm paper background, cream cards, dark hand-ink contours,
muted teal, mustard and terracotta. Keep the layout calm and editorial, with
generous margins, a clear title, one visual focal point and readable type. Use
color consistently to distinguish categories; do not add decorative panels,
fake UI or extra values. Preserve source attribution, units and exact registered
data. Readability at phone size is the standard. Inspect the rendered PNG; if
text or values are missing, correct the specification and inspect the replacement
before attaching it to a scene.

Choose a graphic only when it explains a number, change, sequence, comparison,
location or causal relationship. Prefer one claim per graphic and up to six
source-backed items; shorten labels rather than shrinking them. Select a layout
that matches the idea (`statistical_chart`, `comparison`, `timeline`,
`process_diagram`, `flow_diagram`, `fact_card`, `scientific_schematic` or a
source-bound map). Diagrams need explicit, source-supported relations. Do not
reuse one generic layout for unrelated facts.

Use motion to teach, not decorate. Reveal bars as values are spoken; trace a
timeline or causal path in narrated order; highlight a comparison only while
that point is explained. Give each item one clear entrance and let it settle
before the next. Change scenes when the idea changes, not on every word.

Motion comes in two levels:

1. **Entrance (default).** When `animation` is omitted, `generate_graphic`
   renders `entrance`: cards fade in and settle upward one after another
   (0.5 s apart) and then hold. It claims nothing about narration timing, so it
   needs no voice and is the right motion for graphics made before
   `generate_images`. Pass `animation: "none"` only for a deliberate still.
2. **Narration-timed.** After Kokoro acoustic alignment, upgrade the scenes
   where timing teaches something to `reveal`, `bars`, `highlight`, `timeline`,
   `path`, `move` or `before_after`, binding each item to an exact spoken
   `cue_phrase` and occurrence (or verified word index). Never estimate seconds.
   Cue phrases must match the spoken words: narration spells numbers out
   ("diecisiete horas"), so cue on those words, not on the card value "17".
   If cues overlap, are absent or ambiguous, keep the entrance.

All motion uses eased curves; illustrations get a supersampled, eased Ken Burns
move, so pick `camera_movement` for meaning (push in to focus, pull out to reveal
context, pan to follow a line of action). Motion must preserve labels, values
and attribution.

## Example: AI and the limits of replacing human knowledge

These older examples show the level of specificity required; render them in the
current Rubber Hose treatment rather than photorealism.

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
