from attr import dataclass

from db import SqlLiteClient
from domain import Contract, ValidationError, ValidationException

_db = None


def initialize_db(db: SqlLiteClient):
    global _db
    _db = db


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
    _db.insert_contract(contract)
