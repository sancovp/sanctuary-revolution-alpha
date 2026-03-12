"""
Utilities for working with Hyperon atoms in Python.

These utilities handle the conversion between MeTTa atoms and Python objects,
abstracting away the complexity of different atom types.
"""

from typing import Any, List
from hyperon import Atom, SymbolAtom, VariableAtom, GroundedAtom, ExpressionAtom


def unwrap_atom(atom: Any) -> Any:
    """
    Universal atom unwrapper - handles both grounded atoms and symbols.

    This is the KEY utility for grounded functions that use unwrap=False.
    It extracts Python values from any atom type:
    - ValueAtom (grounded) -> extract .value
    - SymbolAtom -> extract .get_name()
    - VariableAtom -> extract .get_name()
    - String/number literal -> return as-is
    - ExpressionAtom -> recursively unwrap to Python list

    Args:
        atom: Any MeTTa atom or Python object

    Returns:
        Python object extracted from the atom

    Examples:
        unwrap_atom(SymbolAtom('TestName')) -> 'TestName'
        unwrap_atom(ValueAtom("hello")) -> "hello"
        unwrap_atom(ValueAtom(42)) -> 42
        unwrap_atom("already a string") -> "already a string"
    """
    # Already a Python primitive
    if isinstance(atom, (str, int, float, bool)):
        return atom

    # Symbol or Variable - extract name
    if isinstance(atom, SymbolAtom) or isinstance(atom, VariableAtom):
        return atom.get_name()

    # Expression - recursively unwrap children to Python list
    if isinstance(atom, ExpressionAtom):
        return [unwrap_atom(child) for child in atom.get_children()]

    # Grounded atom - extract wrapped object
    if isinstance(atom, GroundedAtom):
        obj = atom.get_object()
        # ValueObject has .value property
        if hasattr(obj, 'value'):
            return obj.value
        # OperationObject has .content property
        if hasattr(obj, 'content'):
            return obj.content
        # Direct wrapped object
        return obj

    # Fallback to string representation
    return str(atom)


def unwrap_atom_list(atoms: List[Any]) -> List[Any]:
    """
    Unwrap a list of atoms to Python objects.

    Args:
        atoms: List of MeTTa atoms

    Returns:
        List of unwrapped Python objects
    """
    return [unwrap_atom(atom) for atom in atoms]
