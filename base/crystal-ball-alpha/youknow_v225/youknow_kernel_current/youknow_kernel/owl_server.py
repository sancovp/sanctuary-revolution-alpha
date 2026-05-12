"""OWL Reasoner subprocess server — NO pyswip/libswipl in this process.

Runs on port 8103. Loaded once at startup. Accepts POST /validate with
concept_data JSON, returns validation result. The daemon (which has pyswip)
communicates with this server instead of calling OWLReasoner directly.

Why subprocess: libswipl.so (loaded by pyswip) corrupts owlready2's weakref-
based namespace cache (_get_by_storid/_load_by_storid infinite recursion),
even when NOT inside a Prolog query. Two separate processes = isolated address
spaces = owlready2 unaffected.
"""

import json
import logging
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [OWL] %(levelname)s %(message)s",
)
logger = logging.getLogger("owl_server")

PORT = 8103

logger.info("Loading OWLReasoner...")
from youknow_kernel.owl_reasoner import OWLReasoner
_reasoner = OWLReasoner()
logger.info("OWLReasoner ready.")

# Pre-compute class list by parsing OWL XML directly (avoids owlready2 threading issues)
import xml.etree.ElementTree as _ET
_OWL_NS = "http://www.w3.org/2002/07/owl#"
_RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"

def _parse_owl_classes(owl_path):
    """Extract class names from an OWL/RDF-XML file without owlready2."""
    classes = []
    try:
        tree = _ET.parse(owl_path)
        root = tree.getroot()
        for elem in root.iter(f"{{{_OWL_NS}}}Class"):
            about = elem.get(f"{{{_RDF_NS}}}about") or elem.get(f"{{{_RDF_NS}}}ID", "")
            name = about.split("#")[-1] if "#" in about else about.split("/")[-1]
            if not name or name.startswith("http"):
                continue
            # Collect is_a from rdfs:subClassOf
            is_a = []
            for sub in elem.findall(f"{{{_RDFS_NS}}}subClassOf"):
                ref = sub.get(f"{{{_RDF_NS}}}resource", "")
                parent = ref.split("#")[-1] if "#" in ref else ref.split("/")[-1]
                if parent and parent != "Thing":
                    is_a.append(parent)
            classes.append({"name": name, "is_a": is_a})
    except Exception as e:
        logger.warning(f"Could not parse {owl_path}: {e}")
    return classes

_classes_cache = []
_owl_files = [OWLReasoner._UARL_LOCAL_PATH, OWLReasoner._STARSYSTEM_LOCAL_PATH]
for _owl_file in _owl_files:
    if _owl_file.exists():
        _classes_cache.extend(_parse_owl_classes(_owl_file))
logger.info(f"Pre-computed {len(_classes_cache)} OWL classes for /classes endpoint.")


class OWLHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok"})
        elif self.path == "/classes":
            self._respond(200, {"classes": _classes_cache})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/validate":
            self._respond(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            concept_data = json.loads(body)
            result = _reasoner.validate_concept(concept_data)
            self._respond(200, {
                "valid": result.valid,
                "errors": [
                    {"message": e.get("message", str(e)), "property_path": e.get("property_path", "")}
                    if isinstance(e, dict) else {"message": str(e), "property_path": ""}
                    for e in result.errors
                ],
                "concept_uri": result.concept_uri,
            })
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
    server = HTTPServer(("localhost", PORT), OWLHandler)
    logger.info("OWL server listening on port %d", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
