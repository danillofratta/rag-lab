class InvalidWorkspace(ValueError):
    """A workspace violates its invariants (naive timestamps, non-positive lifetime)."""
