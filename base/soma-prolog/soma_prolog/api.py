"""SOMA HTTP transport. ONE entrypoint: POST /event → core.ingest_event.

This is NOT a REST API. It is a transport for add_event. There is no
other route, ever. Every operation in SOMA is performed by submitting
an event whose observations describe what the agent wants. The Prolog
runtime observes the intent, decides if it can be done, and executes.

If you find yourself adding another route here, STOP. Read
~/.claude/rules/soma-only-entrypoint-is-add-event.md
"""

import json
import logging
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from soma_prolog import core

logging.basicConfig(level=logging.INFO, format="[SOMA] %(message)s")
logger = logging.getLogger(__name__)


class SOMAHandler(BaseHTTPRequestHandler):
    """One handler. One route. POST /event. Nothing else exists."""

    def do_POST(self):
        path = self.path.rstrip("/")
        if path == "/rule":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            try:
                data = json.loads(body) if body else {}
                rule_body = data.get("rule_body", "")
                if not rule_body:
                    self._respond(400, {"error": "rule_body required"})
                    return
                result = core.add_rule(rule_body)
                self._respond(200, {"result": result})
            except Exception as e:
                logger.error(f"add_rule error: {e}", exc_info=True)
                self._respond(500, {"error": str(e)})
            return

        if path != "/event":
            self._respond(404, {
                "error": "SOMA entrypoints: POST /event, POST /rule."
            })
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._respond(400, {"error": "Invalid JSON"})
            return

        try:
            source = data.get("source", "unknown")
            # Mirror CartON add_observation_batch: the payload can be either
            # `observation_data` (carton dict shape keyed by category) OR
            # legacy `observations` (list). ingest_event handles both via
            # build_obs_list_string.
            if "observation_data" in data:
                observations = data["observation_data"]
            else:
                observations = data.get("observations", [])
            domain = data.get("domain", "default")
            result = core.ingest_event(source, observations, domain=domain)
            self._respond(200, {"result": result})
        except Exception as e:
            logger.error(f"add_event error: {e}", exc_info=True)
            self._respond(500, {"error": str(e)})

    def do_GET(self):
        # SOMA has no GET routes. Submit an event.
        self._respond(404, {
            "error": "SOMA exposes ONE entrypoint: POST /event. "
                     "There are no GET routes. Submit an event."
        })

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format, *args):
        logger.info(format % args)


def main():
    parser = argparse.ArgumentParser(description="SOMA event sink")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    # No startup boot check. SOMA has ONE entrypoint: POST /event.
    # The Prolog runtime boots lazily on the first event via
    # ensure_rules_loaded inside mi_add_event/3. If anything is wrong,
    # the first POST /event will return the actual error.
    logger.info("SOMA daemon starting (Prolog boots lazily on first event)...")

    server = HTTPServer((args.host, args.port), SOMAHandler)
    logger.info(f"SOMA listening on {args.host}:{args.port}")
    logger.info("Single endpoint: POST /event {source, observations, domain?}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
