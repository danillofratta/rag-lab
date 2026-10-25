class InvalidSessionTokenHash(ValueError):
    """A session token hash is not a SHA-256 hex digest, or the token to hash is empty."""
