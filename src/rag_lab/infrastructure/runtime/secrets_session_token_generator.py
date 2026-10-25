import secrets


class SecretsSessionTokenGenerator:
    """32 random bytes (256 bits), URL-safe encoded to 43 characters."""

    def next_token(self) -> str:
        return secrets.token_urlsafe(32)
