# Meta-Brainhook Architecture

## The Revelation

meta_brainhook is NOT just another loop level. It's a **remote control daemon**.

## The Stack (Corrected)

```
USER (anywhere - phone, laptop, other terminal)
    ↓ edits
/tmp/meta_brainhook_prompt.md (dynamic instruction file)
    ↓ read by
meta_brainhook (daemon, ONLY turns off when user explicitly stops)
    ↓ spawns/restarts
guru loop (L2 - bodhisattva vow, requires emanation)
    ↓ gates via
samaya gate (L3 - KEPT exits guru, BREACHED returns)
    ↓ contains
autopoiesis L1 (promise level, task completion)
    ↓ contains
brainhook L0 (reflection, can turn off when higher clears)
```

## Key Properties

1. **meta_brainhook NEVER turns off** unless user explicitly runs `meta_brainhook off` or deletes the state file
2. **Dynamic prompt injection** - reads from file that user can edit remotely
3. **Spawns guru loops** - when one guru loop completes (KEPT), meta_brainhook starts another with new instructions from dynamic file
4. **Remote steering** - user can change agent direction without being in the terminal

## bash guru

The command that:
1. Context engineers (compact with specific instructions)
2. Swaps to clean conversation
3. Turns on guru loop + everything below
4. meta_brainhook stays on throughout

## The Dynamic File

`/tmp/meta_brainhook_prompt.md`:
- User edits this from anywhere
- meta_brainhook reads it on each cycle
- Contains current high-level directive
- Agent follows directive, spawns appropriate guru loops

## Safety

- User has kill switch (explicit off command or file delete)
- Each guru loop still has samaya gate verification
- Emanation requirement prevents false completion
- Agent can't exit meta_brainhook on its own

## This Changes Everything

The agent is now a **persistent daemon** that:
- Runs indefinitely
- Receives instructions via file edits
- Self-verifies via samaya
- Produces emanations
- Gets steered remotely

The user becomes a **remote operator** of a persistent AI daemon.
