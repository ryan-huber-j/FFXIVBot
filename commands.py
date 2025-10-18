from attr import dataclass


@dataclass
class ValidationError:
    field: str
    message: str


class ValidationException(Exception):
    def __init__(self, errors: list[ValidationError]):
        self.errors = errors
        super().__init__("Validation failed with errors: " + ", ".join([f"{e.field}: {e.message}" for e in errors]))


@dataclass
class Contract:
    discord_id: str
    first_name: str
    last_name: str
    amount: int


def validate_contract(contract: Contract) -> list[ValidationError]:
    errors = []
    if not contract.first_name.isalpha():
        errors.append(ValidationError('first_name', 'First name must be non-empty and alphabetic.'))
    if not contract.last_name.isalpha():
        errors.append(ValidationError('last_name', 'Last name must be non-empty and alphabetic.'))
    if contract.amount <= 0:
        errors.append(ValidationError('amount', 'Amount must be a positive integer.'))
    return errors


async def create_contract(contract: Contract):
    if len(errors := validate_contract(contract)) > 0:
        raise ValidationException(errors)