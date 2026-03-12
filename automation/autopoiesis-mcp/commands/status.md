---
description: "Show autopoiesis loop status"
allowed-tools: ["Bash"]
---

# Autopoiesis Status

```!
if [[ -f /tmp/active_promise.md ]]; then
  echo "=== AUTOPOIESIS ACTIVE ==="
  echo ""
  cat /tmp/active_promise.md
else
  echo "No active autopoiesis loop."
fi
```

Report the status above to the user.
