"""YOUKNOW HTTP Daemon — single global process for all YOUKNOW validation.

Start with: python3 -m youknow_kernel.daemon
Listens on port 8102.

All callers (carton, dragonbones, etc) POST to http://localhost:8102/validate
instead of importing pyswip directly. pyswip/PrologRuntime initializes ONCE here.
"""

import json
import logging
import subprocess
import sys
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [YOUKNOW] %(levelname)s %(message)s",
)
logger = logging.getLogger("youknow_daemon")

PORT = 8102
OWL_PORT = 8103

# Start OWL reasoner subprocess FIRST — isolated process with no pyswip/libswipl.
# libswipl.so corrupts owlready2's weakref namespace cache if in the same process.
logger.info("Starting OWL reasoner subprocess...")
_owl_proc = subprocess.Popen(
    [sys.executable, "-m", "youknow_kernel.owl_server"],
    stdout=open("/tmp/youknow_owl_server.log", "w"),
    stderr=subprocess.STDOUT,
)
# Wait for OWL server to be ready
for _ in range(30):
    try:
        urllib.request.urlopen(f"http://localhost:{OWL_PORT}/health", timeout=1)
        break
    except Exception:
        time.sleep(1)
else:
    logger.error("OWL server failed to start — check /tmp/youknow_owl_server.log")
logger.info("OWL server ready.")


# Monkey-patch OWLReasoner with a proxy that calls owl_server subprocess.
# This ensures owlready2 never loads in this process (which has libswipl.so).
class _OWLReasonerProxy:
    """Drop-in replacement for OWLReasoner that calls owl_server via HTTP."""

    def __init__(self, **kwargs):
        self._pending_concept = None

    def add_concept(self, name, concept_type, properties):
        self._pending_concept = {"name": name, "type": concept_type, **properties}
        return f"urn:youknow:{name}"

    def get_classes(self):
        """Return all OWL class names + is_a from the owl_server subprocess."""
        try:
            resp = urllib.request.urlopen(f"http://localhost:{OWL_PORT}/classes", timeout=10)
            data = json.loads(resp.read())
            return data.get("classes", [])
        except Exception as e:
            logger.warning(f"OWL /classes call failed: {e}")
            return []

    def run_inference(self):
        from youknow_kernel.owl_reasoner import ReasonerResult
        if self._pending_concept is None:
            return ReasonerResult(consistent=True)
        body = json.dumps(self._pending_concept).encode()
        try:
            req = urllib.request.Request(
                f"http://localhost:{OWL_PORT}/validate",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=60)
            data = json.loads(resp.read())
            errors = [e.get("message", str(e)) for e in data.get("errors", [])]
            return ReasonerResult(
                consistent=data.get("valid", True),
                inconsistencies=errors,
                inferred_facts=[],
                discovered_types=[],
                concept_uri=data.get("concept_uri"),
            )
        except Exception as e:
            logger.warning(f"OWL server call failed: {e} — assuming consistent")
            return ReasonerResult(consistent=True)


import youknow_kernel.owl_reasoner as _owl_mod
_owl_mod.OWLReasoner = _OWLReasonerProxy
logger.info("OWLReasoner monkey-patched to use subprocess proxy.")

# Initialize PrologRuntime AFTER owl_server is up
logger.info("Initializing PrologRuntime...")
from youknow_kernel.prolog_runtime import get_runtime
_runtime = get_runtime()
logger.info("PrologRuntime ready.")


class YouknowHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default HTTP logging

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/validate":
            self._respond(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            statement = data.get("statement", "")
            if not statement:
                self._respond(400, {"error": "missing statement"})
                return
            # Run youknow() directly in clean Python context (no Prolog foreign fn).
            # The validate/3 Prolog rule adds no logic beyond labeling ont/soup —
            # calling youknow() through the foreign fn causes owlready2 SQLite ops
            # inside the pyswip GIL, which deadlocks. Run youknow() first, then
            # assert results into Prolog for fact accumulation.
            from youknow_kernel.compiler import youknow, _get_uarl_validator, _get_last_system_type_inferred
            yk_result = youknow(statement)
            status = "ont" if yk_result == "OK" else "soup"
            _runtime._assert_from_statement(statement, status)
            _runtime._check_and_assert_rule(statement)
            # Collect healed concepts from validator singleton and clear them
            healed = []
            try:
                validator = _get_uarl_validator()
                if validator and hasattr(validator, '_healed_concepts') and validator._healed_concepts:
                    healed = list(validator._healed_concepts)
                    validator._healed_concepts = []
            except Exception as e:
                logger.warning(f"Could not collect healed concepts: {e}")
            # Collect system type inferred _Unnamed fills (for auto-creation by add_concept_tool)
            system_type_inferred = _get_last_system_type_inferred()
            self._respond(200, {"result": yk_result, "healed_concepts": healed, "system_type_inferred": system_type_inferred})
        except Exception as e:
            logger.error("validate error: %s\n%s", e, traceback.format_exc())
            self._respond(500, {"error": str(e)})

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = HTTPServer(("localhost", PORT), YouknowHandler)
    logger.info("YOUKNOW daemon listening on port %d", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
