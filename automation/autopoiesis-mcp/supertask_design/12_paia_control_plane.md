# PAIA Control Plane Architecture

## The Vision

The agent becomes a **persistent service** with multiple input channels. User can steer from anywhere via any interface.

## Architecture

```
                         ┌─────────────────────────┐
                         │   REST API (FastAPI)    │
                         │ POST /prompt            │
                         │ POST /queue             │
                         │ GET /status             │
                         └────────────┬────────────┘
                                      │ writes to
         ┌────────────┬───────────────┼───────────────┬────────────┐
         ▼            ▼               ▼               ▼            ▼
      Mobile       Electron          Web           Email         SMS
      (React       (Desktop         (React)       (parser)     (Twilio)
       Native)      App)
                                      │
                                      ▼
               /tmp/meta_brainhook_prompt.md (dynamic prompt)
               /tmp/meta_brainhook_queue.json (task queue)
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │  meta_brainhook daemon  │
                         │  (Claude in tmux)       │
                         │                         │
                         │  - reads prompt file    │
                         │  - spawns guru loops    │
                         │  - produces emanations  │
                         │  - never stops unless   │
                         │    explicitly killed    │
                         └─────────────────────────┘
```

## Components

### 1. REST API Layer
- FastAPI service running on localhost or cloud
- Endpoints:
  - `POST /prompt` - update current directive
  - `POST /queue` - add task to queue
  - `GET /status` - check agent state
  - `POST /stop` - graceful shutdown
- Writes to dynamic files that meta_brainhook reads

### 2. Frontend Interfaces
- **Mobile (React Native)** - steer agent from phone
- **Electron** - desktop app with full UI
- **Web** - browser-based control panel
- All hit the same REST API

### 3. External Triggers
- **Email parser** - watch inbox, extract tasks, POST to /queue
- **SMS (Twilio)** - text commands, POST to /prompt
- **Webhooks** - GitHub, Slack, etc. can trigger agent

### 4. Queue System
- Tasks queue up in `/tmp/meta_brainhook_queue.json`
- meta_brainhook processes queue FIFO
- Each task spawns a guru loop
- Emanations accumulate

### 5. Planning PAIA → Execution PAIA
- Separate planning context that thinks about what to do
- Queues tasks into execution daemon
- Planning PAIA can run on different schedule (daily planning session)
- Execution PAIA runs continuously

## The Loop

```
1. User sends task (any interface)
       ↓
2. REST API writes to queue/prompt file
       ↓
3. meta_brainhook reads update
       ↓
4. Spawns guru loop for task
       ↓
5. Agent works, produces emanation
       ↓
6. Samaya gate verifies
       ↓
7. KEPT → task done, read next from queue
       ↓
8. Repeat forever (or until explicit stop)
```

## Safety & Control

- User has explicit stop command
- Each task goes through samaya verification
- Emanation requirement prevents rushed completion
- Agent can't escape meta_brainhook on its own
- All interfaces require auth

## This Is The Product

The PAIA isn't just Claude in a terminal. It's:
- A persistent daemon
- With multiple input channels
- Self-verifying work quality
- Accumulating emanations (skills, flights, agents)
- Steerable from anywhere

The user becomes an **operator** of a persistent AI system.
