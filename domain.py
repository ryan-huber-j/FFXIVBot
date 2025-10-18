from typing import NamedTuple


class ValidationError(NamedTuple):
    field: str
    message: str


class ValidationException(Exception):
    def __init__(self, errors: list[ValidationError]):
        self.errors = errors
        super().__init__(
            "Validation failed with errors: "
            + ", ".join([f"{e.field}: {e.message}" for e in errors])
        )


class Participant(NamedTuple):
    discord_id: int
    first_name: str
    last_name: str
    is_coach: bool


class Contract(NamedTuple):
    discord_id: int
    amount: int


class ContractInput(NamedTuple):
    discord_id: int
    first_name: str
    last_name: str
    amount: int
    contract_amounts: list[int]
