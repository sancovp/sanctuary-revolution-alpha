# Omnisanc Queue Architecture

## The Pipeline

```
PAIA (internal)              Queue              External
────────────────────────────────────────────────────────
Omnisanc Hook
    ↓
MCP Manager (direct calls)
    ↓
Queue Producer ──────────→ Redis/Celery ──────────→ n8n
                              │                       ↓
                              │                    World
                              │                 (APIs, social,
                              │                  payments, etc.)
                              ↓
                         Queue Consumer
                         (n8n webhook or
                          celery worker)
```

---

## Why Queue?

**Synchronous (current):**
- Agent calls MCP
- Waits for result
- Blocks until done
- Can't do async work

**Asynchronous (with queue):**
- Agent queues task
- Continues working
- n8n/worker processes later
- Night work happens while user sleeps

---

## Queue Options

### Option 1: Redis + RQ (Simple)
```python
from redis import Redis
from rq import Queue

redis = Redis()
queue = Queue(connection=redis)

def queue_task(task_type, payload):
    """Queue a task for async processing."""
    queue.enqueue(
        'workers.process_task',
        task_type=task_type,
        payload=payload
    )
```

### Option 2: Celery (Full-featured)
```python
from celery import Celery

app = Celery('omnisanc', broker='redis://localhost:6379/0')

@app.task
def process_task(task_type, payload):
    """Async task processor."""
    if task_type == "discord_post":
        post_to_discord(payload)
    elif task_type == "content_publish":
        publish_content(payload)
    # etc.
```

### Option 3: n8n Webhook (Simplest)
```python
import requests

N8N_WEBHOOK = "http://localhost:5678/webhook/omnisanc"

def queue_task(task_type, payload):
    """Fire and forget to n8n."""
    requests.post(N8N_WEBHOOK, json={
        "task_type": task_type,
        "payload": payload,
        "timestamp": datetime.now().isoformat()
    })
```

---

## Omnisanc Integration

```python
# omnisanc_hook.py

from gnosys_strata import MCPManager
from queue_client import QueueClient

manager = MCPManager()
queue = QueueClient()  # Redis, Celery, or n8n

class OmnisancHook:

    def queue_night_work(self, task):
        """Queue work for night mode processing."""
        queue.enqueue({
            "type": task.type,
            "payload": task.payload,
            "priority": task.priority,
            "scheduled_for": "night"
        })

    def queue_immediate(self, task):
        """Queue for immediate async processing."""
        queue.enqueue({
            "type": task.type,
            "payload": task.payload,
            "priority": "high"
        })

    def on_landing_complete(self, session_data):
        """After session, queue follow-up tasks."""
        # Queue content generation
        if session_data.has_deliverables:
            self.queue_night_work({
                "type": "content_generation",
                "payload": session_data.deliverables
            })

        # Queue knowledge ingestion
        self.queue_night_work({
            "type": "carton_ingestion",
            "payload": session_data.journey_logs
        })
```

---

## Task Types

### Day Tasks (Immediate)
```yaml
- type: notification
  desc: Send notification to user
  processor: n8n webhook

- type: quick_api_call
  desc: Non-blocking API call
  processor: celery worker
```

### Night Tasks (Scheduled)
```yaml
- type: content_generation
  desc: Generate social content from DeliverableLogs
  processor: n8n content workflow

- type: carton_ingestion
  desc: Process conversations into CartON
  processor: celery + carton MCP

- type: discord_post
  desc: Post to Discord channels
  processor: n8n discord workflow

- type: email_send
  desc: Send emails
  processor: n8n email workflow

- type: funnel_work
  desc: CAVE business tasks
  processor: n8n business workflow
```

---

## Queue Storage

```
/tmp/heaven_data/queue/
├── pending.json         # Tasks waiting
├── processing.json      # Currently being processed
├── completed.json       # Done (for review)
├── failed.json          # Failed (for retry/debug)
└── scheduled/
    ├── night_queue.json
    └── timed_tasks.json
```

---

## n8n Integration

### Webhook Receiver (n8n)
```
[Webhook] → [Switch by task_type] → [Execute workflow]
                    ↓
    ┌───────────────┼───────────────┐
    ↓               ↓               ↓
[Discord]     [Content]        [Email]
 workflow      workflow        workflow
```

### Example n8n Workflow: Discord Post
```
1. Webhook receives task
2. Extract payload (content, channel, etc.)
3. Format for Discord
4. POST to Discord API
5. Log result back to queue
```

---

## Night Mode Flow

```
Evening:
────────
User leaves
    ↓
Omnisanc transitions to NIGHT state
    ↓
Night queue loaded
    ↓
For each task:
    ├── If MCP task: run internally
    └── If external task: queue to n8n

Night:
──────
n8n processes queue
    ↓
Discord posts go out
Content gets published
Emails sent
Funnel work done
    ↓
Results logged

Morning:
────────
User returns
    ↓
HUD shows:
├── Night work completed
├── Any failures
└── Dream insights (autonomous brain queries)
```

---

## Failure Handling

```python
class QueueClient:

    def enqueue(self, task):
        try:
            self._send_to_queue(task)
        except QueueError:
            # Fallback: write to local file
            self._write_to_fallback(task)
            self._notify_meta_brainhook("queue_failure")

    def _write_to_fallback(self, task):
        """Local fallback when queue unavailable."""
        fallback_path = HEAVEN_DATA / "queue" / "fallback.json"
        tasks = json.loads(fallback_path.read_text() or "[]")
        tasks.append(task)
        fallback_path.write_text(json.dumps(tasks))
```

---

## Configuration

```json
// /tmp/heaven_data/queue/config.json
{
  "backend": "redis",  // or "celery" or "n8n"
  "redis_url": "redis://localhost:6379/0",
  "n8n_webhook": "http://localhost:5678/webhook/omnisanc",
  "celery_broker": "redis://localhost:6379/0",
  "night_start": "22:00",
  "night_end": "06:00",
  "retry_failed": true,
  "max_retries": 3
}
```

---

## Key Insight

**Queue = the boundary between PAIA and World.**

- Inside queue: PAIA territory (internal MCPs, hooks, state)
- Outside queue: World territory (n8n, APIs, services)

Omnisanc manages inside. n8n manages outside. Queue is the handoff.

This enables true async operation - PAIA queues work, goes to sleep (or compacts), world keeps turning.

---

*Session 18 (2026-01-11)*
