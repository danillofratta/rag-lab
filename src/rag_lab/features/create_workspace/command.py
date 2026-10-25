from dataclasses import dataclass


@dataclass(frozen=True)
class CreateWorkspaceCommand:
    """Create a new anonymous workspace. Carries no data: the caller is unauthenticated."""
