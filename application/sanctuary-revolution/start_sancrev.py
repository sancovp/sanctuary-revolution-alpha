"""SANCREV entry point.

Creates WakingDreamer (CAVEAgent impl), wraps in CAVEHTTPServer,
adds sancrev domain routes via SancrevExtension, runs.
"""
from sanctuary_revolution.harness.server.waking_dreamer import WakingDreamer
from sanctuary_revolution.harness.server.sancrev_routes import SancrevExtension
from cave.server.cave_http_server import CAVEHTTPServer

wd = WakingDreamer()
server = CAVEHTTPServer(cave=wd, port=wd.config.port)
SancrevExtension(server)
server.run()
