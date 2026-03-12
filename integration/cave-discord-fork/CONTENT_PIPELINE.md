# Content Pipeline - Fully Automated Video Production

## The Realization

We can automate the entire video creation process because:
1. The content IS the demonstration (just record things working)
2. Live direction markers = edit decisions made while recording
3. Voiceover + diagrams generated from JourneyCore scripts
4. First 7+ videos are "free" - just demonstrate each component

## Why Skill, Not Flight

Recording CAN'T be a flight because you might DO flights during recording.
You record yourself working - which includes running flights.
So it's a **skill** (context injection) not a procedure.

The skill says: "You're recording content. Here's how marks work. Here's the template structure."

## The Template Structure

```
┌─────────────────────────────────────┐
│ WHO I AM (pre-recorded clip)        │ ← Your face, intro, "I'm Isaac..."
├─────────────────────────────────────┤
│ CONTENT (marks-processed recording) │ ← What you just recorded
├─────────────────────────────────────┤
│ CTA (pre-recorded clip)             │ ← "Join the community..."
└─────────────────────────────────────┘
```

Pre-record the WHO I AM and CTA clips once. They get slotted in automatically.

## The Full Pipeline

```
equip content-recording skill
    ↓
Start recording (OBS MCP)
    ↓
Do your thing (including running flights!)
    ↓
Mark good/bad takes as you go
    ↓
Stop recording
    ↓
full_pipeline() runs:
    - Process marks → segments
    - Keep good, delete bad
    - Slot into template (intro + content + CTA)
    - Add voiceover if provided
    ↓
JourneyCore generates:
    - Discord post
    - Twitter thread
    - LinkedIn post
    - Blog structure
    ↓
PACKAGE DELIVERED:
    - final.mp4 (ready to upload)
    - All platform posts (ready to copy/paste)
    ↓
YOU: upload video, post text, done
```

## Content MCP Tools

Location: `/tmp/obs-mcp-cave/` (CAVE fork of obs-mcp)

### Recording
```python
start_recording_session(name)     # Start + auto sync mark
mark(label="good/cut")            # Mark takes during recording
stop_recording_session()          # Stop + return video/marks paths
```

### Post-Processing
```python
process_marks(video, marks)       # Cut video at marks
assemble_video(segments, name)    # Concat + template slots
add_voiceover(video, audio, name) # Mix voiceover
full_pipeline(video, marks, name) # All-in-one
```

### Voiceover (ElevenLabs)
```python
generate_voiceover(text, output_name)  # Text → MP3
list_voices()                           # See available voices
```

Output: `$HEAVEN_DATA_DIR/content_voiceover/`

### Output
- Marks: `$HEAVEN_DATA_DIR/content_marks/`
- Videos: `$HEAVEN_DATA_DIR/content_output/`

## Template Clips Needed

Record these ONCE, reuse forever:

1. **intro_whoiam.mp4** - "Hey, I'm Isaac. I build AI infrastructure..."
2. **outro_cta.mp4** - "All the pieces are on GitHub. If you want the integrated base plus people doing this together, join the community. Link in description."

Store in: `$HEAVEN_DATA_DIR/content_templates/`

## First Video Structure (Meta-Reveal)

**ACT 1: The Demo**
- Show the component working (autopoiesis, hooks, etc.)
- Normal educational content

**ACT 2: The Reveal**
- "btw did you notice something?"
- "This video was made with the system I just showed you"

**ACT 3: The Breakdown**
- Rewind and show how:
  - "See this cut? That's the marks system"
  - "This voice? ElevenLabs from JourneyCore script"
  - "The diagrams? Generated from the same script"

**ACT 4: The Invitation**
- "All pieces on GitHub"
- "Integrated base + community = the offer"
- "Join us"

## The 7 Videos

1. **Hooks** - show hooks firing
2. **Autopoiesis** - show XML tag checkpoints
3. **Guru loop** - show the investigation (meaningful roles)
4. **Skills** - show equip/use
5. **Starship/Starlog** - show session persistence
6. **TreeShell** - show nav/jump/exec
7. **The Stack** - all together (community demo)

Each one: open terminal, show it working, talk about what you're curious about.
The recording + assembly is fully automated.

## Still TODO

- [x] ElevenLabs voiceover tool ✅
- [ ] JourneyCore platform post generation
- [ ] `content-recording` skill
- [ ] Pre-record intro/CTA clips
