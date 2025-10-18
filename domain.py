from dataclasses import dataclass


@dataclass
class ValidationError:
    field: str
    message: str


class ValidationException(Exception):
    def __init__(self, errors: list[ValidationError]):
        self.errors = errors
        super().__init__(
            "Validation failed with errors: "
            + ", ".join([f"{e.field}: {e.message}" for e in errors])
        )


@dataclass
class Contract:
    discord_id: int
    first_name: str
    last_name: str
    amount: int
