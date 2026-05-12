"""Super layer — metaprogramming runtime on top of the meta-interpreter.

This layer can:
- Register new operations at runtime
- Hot-reload operations from disk
- Create new operations from within MAP itself
- Self-modify the registry and even its own dispatch logic
"""
