# OpenRoom → SANCREV OPERA Integration Design
## "Rooms" for Agent Chat Modals

**Date:** 2026-03-20
**Status:** DESIGN — ready for implementation

---

## THE IDEA

The current agent-control-panel has two chat modals:
1. **ConductorChatModal** — connects to harness at `:8090`, SSE events, conversation management
2. **CaveAgentModal** — WoW gear-slot state viewer connecting to CAVE at `:8080`

These are functional but look like **admin panels**. OpenRoom shows what a **consumer product** looks like: themed rooms with animated characters, video backgrounds, emotion states, and social interactions.

**The integration:** Turn the existing chat modals into expandable "rooms" by porting three subsystems from OpenRoom:

1. **Character System** — emotion-mapped video/image rendering
2. **Room Layout** — full-screen background + character + chat overlay
3. **Character Configurator** — users customize their AI companion

---

## WHAT WE PORT FROM OPENROOM

### 1. Character Manager (`characterManager.ts` → `src/lib/characterManager.ts`)

Port directly. Key data structures:

```typescript
// Emotion types that map to Psychoblood states
const SANCREV_EMOTION_LIST = [
  'default',        // WakingDreamer normal
  'happy',          // PLE running, positive flow
  'contemplative',  // OVP mode, deep thinking
  'compassionate',  // Berserking (golden state) 
  'intense',        // DC mode, adversarial truth
  'peaceful',       // Sanctuary state
  'concerned',      // Warning, context decay detected
] as const;

interface CharacterConfig {
  id: string;
  character_name: string;           // "Conductor", "GNOSYS", user's PAIA name
  character_desc: string;           // System prompt personality
  character_emotion_list: string[];
  character_meta_info: {
    base_image_url?: string;        // Default character art
    back_img_url?: string;          // Room background
    emotion_videos?: Record<string, string[]>;  // Emotion → video clips
    emotion_images?: Record<string, string>;    // Emotion → static images
    avatar_img_url?: string;        // Small avatar for chat bubbles
  };
}
```

**Emotion mapping to SANCREV identity system:**

| Identity State | Emotion | Visual |
|---------------|---------|--------|
| WakingDreamer | default, happy, contemplative | Calm, present, coordinating |
| OVP | contemplative, peaceful | Meta-aware, seeing patterns |
| Demon Champion | intense, concerned | Adversarial truth, won't let you BS |
| PBB (Golden) | compassionate | Angry compassion in full action |

### 2. Room Layout (new component: `src/components/RoomView/`)

```
┌─────────────────────────────────────────────────┐
│  [background video/image - full bleed]           │
│                                                   │
│           ┌──────────────────────┐               │
│           │   CHARACTER VIDEO    │   ← emotion   │
│           │   (center, large)    │     mapped     │
│           └──────────────────────┘               │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  Chat messages (scrollable, semi-transparent)│ │
│  │  ─────────────────────────────────────────── │ │
│  │  🔧 Tool use (collapsible)                   │ │
│  │  💭 Thinking (collapsible)                   │ │
│  │  🎼 Conductor: "Here's what I found..."      │ │
│  ├─────────────────────────────────────────────┤ │
│  │  [Input bar]                    [Send]       │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  [Status indicators]    [⚙️ Config] [👤 Char]   │
└─────────────────────────────────────────────────┘
```

### 3. Character Configurator (`CharacterPanel.tsx` → `src/components/CharacterConfigurator/`)

Port OpenRoom's `CharacterPanel` + `CharacterEditor`. Already has:
- Character list with active selection
- Add/delete characters
- Edit: name, gender, description (persona)
- Emotion list management (add/remove custom emotions)
- Per-emotion image/video URL inputs with preview thumbnails
- Base avatar URL

**Our additions:**
- SANCREV identity mode selector (WakingDreamer / OVP / DC)
- TTS voice config (links to existing tts-avatar MCP)
- Backend connection config (harness URL, CAVE URL)

---

## FILE STRUCTURE

```
src/
  lib/
    characterManager.ts       ← NEW (ported from OpenRoom)
    roomBackgrounds.ts        ← NEW (background presets/management)
  components/
    RoomView/
      RoomView.tsx            ← NEW (room layout: bg + character + chat)
      RoomView.css            ← NEW
      CharacterDisplay.tsx    ← NEW (emotion-mapped video/image rendering)
      CharacterDisplay.css    ← NEW
    CharacterConfigurator/
      CharacterPanel.tsx      ← NEW (ported from OpenRoom CharacterPanel)
      CharacterEditor.tsx     ← NEW (ported from OpenRoom CharacterEditor)
      CharacterConfigurator.css ← NEW
    ConductorChatModal.tsx    ← MODIFIED (add RoomView mode toggle)
    CaveAgentModal.tsx        ← UNCHANGED (this is admin, not consumer)
```

---

## IMPLEMENTATION PLAN

### Phase 1: Port Character System (lib layer)
1. Copy `characterManager.ts` from OpenRoom, adapt types
2. Replace OpenRoom's emotion list with SANCREV emotions
3. Add `roomBackgrounds.ts` for default background presets
4. Storage: localStorage for now (same as OpenRoom)

### Phase 2: Build CharacterDisplay Component
1. `CharacterDisplay.tsx` — renders character video/image based on emotion
2. Uses `resolveEmotionMedia()` from characterManager
3. Handles video playback, fallback to static image
4. Emotion transitions (change video on emotion change)

### Phase 3: Build RoomView Component
1. Full-screen container with:
   - Background layer (video or image, CSS `object-fit: cover`)
   - Character layer (centered, emotion-responsive)
   - Chat overlay (bottom portion, semi-transparent black)
   - Input bar (bottom, styled like OpenRoom's yellow bar)
2. Toggle between "room mode" (full visual) and "compact mode" (current modal)

### Phase 4: Integrate with ConductorChatModal
1. Add a "Room Mode" toggle button to the conductor header
2. When toggled: replace the current modal content with `RoomView`
3. RoomView wraps the existing chat logic (messages, send, SSE)
4. Emotion state driven by conductor's current identity mode:
   - SSE event `IDENTITY_CHANGE { mode: "waking_dreamer" }` → update emotion
   - Or derive from message sentiment/content

### Phase 5: Port Character Configurator
1. Port `CharacterPanel` + `CharacterEditor` from OpenRoom
2. Add to CAVE Agent Modal or as standalone settings panel
3. Let users:
   - Create/edit characters for their Conductor
   - Upload/link emotion videos
   - Set room backgrounds
   - Choose TTS voice (if tts-avatar MCP available)

### Phase 6: Default Characters
1. Ship with 2-3 default characters:
   - **Conductor** — orchestration personality, professional sci-fi aesthetic
   - **GNOSYS** — knowledge/philosophy personality, mystical aesthetic
   - **Custom** — blank template for user creation
2. Each comes with default backgrounds and emotion presets

---

## CSS PATTERN FOR ROOM MODE

```css
/* Room container — fills the modal */
.room-view {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 12px;
}

/* Background — full bleed video or image */
.room-background {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.room-background video,
.room-background img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Character — centered, above background */
.room-character {
  position: absolute;
  bottom: 40%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1;
  max-width: 50%;
  max-height: 60%;
}

.room-character video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  mix-blend-mode: screen; /* or normal, depending on character art style */
}

/* Chat overlay — bottom portion */
.room-chat-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 45%;
  z-index: 2;
  background: linear-gradient(transparent, rgba(0,0,0,0.85) 30%);
  display: flex;
  flex-direction: column;
}

.room-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 60px 20px 10px;
}

.room-chat-input {
  padding: 12px 20px;
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(10px);
}
```

---

## WHAT THIS ENABLES

1. **Consumer product feel** — not admin panel, but immersive AI companion
2. **Psychoblood visualization** — character emotions reflect internal state
3. **Identity system visible** — WakingDreamer/OVP/DC shown through character appearance
4. **User attachment** — customizable characters create ownership
5. **Premium differentiation** — this is what you sell. The patterns are free. This is the product.

---

## RELATIONSHIP TO OPENROOM

We are NOT forking OpenRoom. We are:
- **Porting the character rendering pattern** (emotion → video → display)
- **Porting the character configurator UI** (list + editor)
- **Adapting the room layout concept** (background + character + chat)
- **Keeping our own backend** (harness, CAVE, SSE — not OpenRoom's IndexedDB action system)

OpenRoom's app system, window manager, and action routing are NOT needed — we have our own (ModalStack, CAVE MCP tools, etc).

MIT license allows this.
