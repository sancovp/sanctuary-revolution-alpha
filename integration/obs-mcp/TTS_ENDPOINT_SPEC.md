# TTS Endpoint Specification

## Overview

The Claude Code hook system needs to trigger text-to-speech on the Mac host. Since hooks run inside Docker, they cannot access macOS `say` command directly. The Electron frontend (running on Mac) should expose an HTTP endpoint for TTS.

## Endpoint

```
POST /speak
Content-Type: application/json

{
  "text": "The voiceover text to speak"
}
```

## Response

```json
{
  "ok": true
}
```

## Implementation (Node.js/Electron)

```javascript
// Add to frontend HTTP server

app.post('/speak', (req, res) => {
  const { text } = req.body;
  if (!text) {
    return res.status(400).json({ ok: false, error: 'No text provided' });
  }

  const { exec } = require('child_process');
  // Escape quotes for shell safety
  const escaped = text.replace(/"/g, '\\"').replace(/`/g, '\\`').replace(/\$/g, '\\$');

  exec(`say "${escaped}"`, (err) => {
    if (err) {
      console.error('TTS error:', err);
      return res.json({ ok: false, error: err.message });
    }
    res.json({ ok: true });
  });
});
```

## Port

The frontend HTTP server should be accessible from Docker at:
- `http://host.docker.internal:<PORT>/speak`

Orchestrator port: **8090**

## Hook Integration

The Claude Code hook (`~/.claude/hooks/obs_recording_hook.py`) calls this endpoint when it detects a voiceover fence `<🎤>text</🎤>` in Claude's output.

Hook calls:
```python
urllib.request.urlopen(
    urllib.request.Request(
        "http://host.docker.internal:8090/speak",
        data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json"}
    ),
    timeout=30
)
```

## Optional: Voice Selection

Future enhancement - allow voice selection:

```json
{
  "text": "Hello world",
  "voice": "Samantha",
  "rate": 200
}
```

```javascript
exec(`say -v "${voice}" -r ${rate} "${escaped}"`);
```

## Optional: BlackHole Audio Isolation

For isolated voiceover track in OBS:

1. Install BlackHole (virtual audio device)
2. Change command to: `say -a "BlackHole 2ch" "${escaped}"`
3. OBS captures BlackHole as separate audio track

---

**Status:** Waiting for frontend implementation
**Priority:** Medium
**Depends on:** Electron frontend HTTP server
