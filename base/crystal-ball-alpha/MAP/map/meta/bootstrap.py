"""Bootstrap loader for the meta-circular evaluator.

Loads meta_circular.map into the base interpreter,
making META-EVAL and META-ENV available.
"""

from .meta_interp import boot_meta

def bootstrap():
    """Boot the meta-circular evaluator and return the meta-interpreter.

    Usage:
        meta = bootstrap()
        result = meta.eval_in_meta("{+ 1 2}")  # => Atom(3)
        result = meta.eval_program_in_meta("{bind x 10} {+ x 5}")  # => Atom(15)
    """
    return boot_meta()


if __name__ == "__main__":
    meta = bootstrap()
    print("Meta-circular evaluator bootstrapped successfully.")
    print(f"Trace depth: {len(meta.trace)} eval steps")

    # Quick smoke test
    result = meta.eval_in_meta("{+ 1 2}")
    print(f"META-EVAL {{+ 1 2}} => {result}")

    result = meta.eval_in_meta("{* 6 7}")
    print(f"META-EVAL {{* 6 7}} => {result}")
