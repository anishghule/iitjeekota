"""Error type for problems a person must fix (bad data, missing tool, failed check)."""


class BuildError(Exception):
    """Raised by any dsapkit step. The CLI prints the message and exits with status 1."""
