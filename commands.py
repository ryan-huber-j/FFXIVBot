from attr import dataclass

from db import SqlLiteClient
from domain import Contract, ValidationError, ValidationException

_db = None


def initialize_db(db: SqlLiteClient):
    global _db
    _db = db


def validate_contract(
    contract: Contract, contract_amounts: list[int]
) -> list[ValidationError]:
    errors = []
    if not contract.first_name.isalpha():
        errors.append(
            ValidationError("first_name", "First name must be non-empty and alphabetic.")
        )
    if not contract.last_name.isalpha():
        errors.append(
            ValidationError("last_name", "Last name must be non-empty and alphabetic.")
        )
    if contract.amount not in contract_amounts:
        contract_amounts_str = ", ".join(str(amount) for amount in contract_amounts)
        errors.append(
            ValidationError("amount", f"Amount must be one of: {contract_amounts_str}.")
        )
    return errors


async def create_contract(contract: Contract, contract_amounts: list[int] = []):
    if len(errors := validate_contract(contract, contract_amounts)) > 0:
        raise ValidationException(errors)
    _db.insert_contract(contract)
