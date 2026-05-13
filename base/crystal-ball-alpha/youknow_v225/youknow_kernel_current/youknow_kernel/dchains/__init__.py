"""D-chains package.

Importing this package triggers registration of all chains in submodules.
Each submodule that defines DeductionChain instances must call
`register(chain, body)` at module top level. Importing it from here is
what makes those registrations happen.
"""

from . import skill_chains  # noqa: F401 — import side effect registers chains
