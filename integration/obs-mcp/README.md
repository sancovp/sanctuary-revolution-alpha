# OBS MCP Server (CAVE Fork)

Fork of [royshil/obs-mcp](https://github.com/royshil/obs-mcp) with **marks system** for automated content pipeline.

## Added: Marks System

Mark timestamps during recording for automated ffmpeg post-processing:

```python
start_recording_session(name="my_video")  # Start recording + auto sync mark
mark(label="good")                         # End of good take - keep segment
mark(label="cut")                          # End of bad take - delete segment
stop_recording_session()                   # Stop + returns video path + marks file
get_marks()                                # Get all marks from current session
undo_last_mark()                           # Remove last mark
```

Marks saved to: `$HEAVEN_DATA_DIR/content_marks/marks_{session}.json`

## Added: ffmpeg Post-Processing

```python
process_marks(video_path, marks_file)     # Cut video at marks → segments
assemble_video(segment_paths, output_name) # Concat segments + optional intro/outro
add_voiceover(video_path, audio_path, name) # Mix voiceover audio
full_pipeline(video, marks, name, ...)     # All-in-one: marks → assemble → voice
```

Output saved to: `$HEAVEN_DATA_DIR/content_output/`

### Full Workflow

1. `start_recording_session()` - begin recording
2. `mark(label="good/cut")` - mark takes during recording
3. `stop_recording_session()` - stop, get video + marks paths
4. `full_pipeline(video, marks, "my_video")` - auto-process everything

## Original Features

- Connect to OBS WebSocket server
- Control OBS via MCP tools
- Provides tools for:
  - General operations
  - Scene management
  - Source control
  - Scene item manipulation
  - Streaming and recording
  - Transitions
  - **Marks (CAVE addition)** - timestamp marking for content pipeline


## Usage

1. Make sure OBS Studio is running with WebSocket server enabled (Tools > WebSocket Server Settings). Note the password for the WS.
2. Set the WebSocket password in environment variable (if needed):

```bash
export OBS_WEBSOCKET_PASSWORD="your_password_here"
```

3. Add the MCP server to Claude desktop with the MCP server settings:

```json
{
  "mcpServers": {
    "obs": {
      "command": "npx",
      "args": ["-y", "obs-mcp@latest"],
      "env": {
        "OBS_WEBSOCKET_PASSWORD": "<password_from_obs>"
      }
    }
  }
}
```

4. Use Claude to control your OBS!

## Development

If you want to run the server locally using the code in this git repo, you can do the following:


```bash
npm run build
npm run start
```

Then configure Claude desktop:

```json
{
  "mcpServers": {
    "obs": {
      "command": "node",
      "args": [
        "<obs-mcp_root>/build/index.js"
      ],
      "env": {
        "OBS_WEBSOCKET_PASSWORD": "<password_from_obs>"
      }
    }
  }
}
```

## Available Tools

The server provides tools organized by category:

- General tools: Version info, stats, hotkeys, studio mode
- Scene tools: List scenes, switch scenes, create/remove scenes
- Source tools: Manage sources, settings, audio levels, mute/unmute
- Scene item tools: Manage items in scenes (position, visibility, etc.)
- Streaming tools: Start/stop streaming, recording, virtual camera
- Transition tools: Set transitions, durations, trigger transitions

## Environment Variables

- `OBS_WEBSOCKET_URL`: WebSocket URL (default: ws://localhost:4455)
- `OBS_WEBSOCKET_PASSWORD`: Password for authenticating with OBS WebSocket (if required)

## Requirements

- Node.js 16+
- OBS Studio 31+ with WebSocket server enabled
- Claude desktop

## License

See the [LICENSE](LICENSE) file for details.