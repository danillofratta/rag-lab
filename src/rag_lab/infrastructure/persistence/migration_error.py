class MigrationError(RuntimeError):
    """A migration cannot be applied safely. The message names the migration, never data."""
