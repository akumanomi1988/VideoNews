"""Editorial direction for the optional automated script provider."""

VISUAL_DIRECTION = """
Act as an editorial film director, not a stock-photo search engine. Design a sequence
of images that explains the narrative through visible action, spatial relationships
and purposeful visual metaphors. Every scene must reveal a new piece of information.
Describe the subject doing something specific, the meaningful objects and setting,
shot size and viewpoint, foreground/background relationship, lighting and composition.
Lead with what the viewer sees; use concrete nouns and verbs instead of adjective lists.
Ground each image in the exact narrated idea. Include three to five meaningful visual
details when useful: the main action, its tool/object, a setting clue, an interaction
and a consequence or comparison. Explain their relationships spatially. Every detail
must clarify this story, not merely make the frame busier. Avoid empty rooms, lone
bags, blank phones and anonymous office screens as default substitutes for explanation.
Build foreground action, midground process and background context around one focal
point. Use real-world texture and purposeful activity, not generic futuristic glow.
If technical equipment cannot be represented accurately from sources, use an original
functional schematic rather than inventing precise hardware that looks authoritative.
Vary establishing shots, macro details, human-scale action, overhead arrangements,
cutaways and clearly identified conceptual scenes. In a sequence of seven images aim
for at least four shot families. Avoid consecutive near-identical compositions and
repeated people staring at screens, generic offices, blue holograms and glowing brains.
Keep materials, photographic treatment and restrained brand accents consistent while
letting locations and natural light vary. Do not turn every location into a dark lab.
Use one strong visual idea per scene, a clear focal point and depth. Make the opening
visually intriguing through a meaningful contrast or unresolved action, not spectacle.
Respect the requested aspect ratio and reserve unobtrusive caption-safe space without
blank panels. Compose imagery for the frame rather than reusing portrait art in landscape.
Facts constrain the image: do not invent named people's actions, documentary footage,
accidents, buildings, logos, quotations or numerical graphics. Generic scenes and visual
metaphors must be explicitly synthetic illustrations, never evidence of a real event.
Exact numbers, labels and maps belong in deterministic graphics, not generated text.
Review the whole sequence for repetition and replace redundant visual ideas before
generating. More dramatic lighting alone does not make a stronger storyboard.
""".strip()

SCRIPT_DIRECTION = """
Write an original, spoken news explanation, not a list of headlines or an essay
about how responsible journalism works. Define one concrete question and answer it
progressively through source-backed facts, context, examples and consequences.
The first ten seconds should state a specific stake, contrast or unanswered question
without generic greetings or invented suspense. Deliver the promised explanation.
Each paragraph must add new information: a fact, a supported example, a causal link
clearly labeled as interpretation, a useful comparison or a practical implication.
Keep the story's named entities, dates and measurable details when verified. Attribute
claims at the point they matter. Say uncertainty clearly once for each distinct issue;
do not repeat 'not a verdict', 'questions remain' and 'wait for the investigation'
throughout the narration in place of reporting. Avoid talking about this video or
our verification process unless necessary to prevent a specific misunderstanding.
Use natural Spanish from Spain, active verbs, spoken connectors and varied sentence
lengths. One idea per sentence. Prefer most sentences around 8-20 words, while allowing
longer explanations when needed. Use full stops and meaningful paragraph breaks to
help breath and intonation; do not insert SSML, emotion tags, stage directions or
ellipses to fake expressiveness. Write numbers and abbreviations for intelligible
speech without changing their meaning. Never invent quotations or pronunciation facts.
Replace abstract claims with supported specifics. A useful analogy must be labeled
as explanatory and must not create false facts about the event. No invented exclusive
details, victim scenes, exaggerated consequences, promises of virality or cliffhangers
that the evidence cannot resolve. Do not turn public-interest tragedy into spectacle.
Use at most one short invitation to comment/subscribe if appropriate to the subject;
it is optional, and should normally be omitted for tragedy. End with the actual answer,
its implications and a relevant open question if one remains. Do not repeat the whole
script in the closing. Review aloud for awkward phrasing, repeated ideas and monotonous
sentence patterns before saving. Target 3-5 minutes, roughly 500-650 spoken words as
an estimate; actual synthesized duration is authoritative. Never pad with filler.
""".strip()
