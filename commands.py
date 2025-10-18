from attr import dataclass

from db import SqlLiteClient
from domain import Contract, Participant, ValidationError, ValidationException

_db = None


def initialize_db(db: SqlLiteClient):
    global _db
    _db = db


def validate_participant(participant: Participant) -> list[ValidationError]:
    errors = []
    if not isinstance(participant.discord_id, int):
        errors.append(ValidationError("discord_id", "Discord ID must be an integer."))
    if not participant.first_name.isalpha():
        errors.append(
            ValidationError("first_name", "First name must be non-empty and alphabetic.")
        )
    if not participant.last_name.isalpha():
        errors.append(
            ValidationError("last_name", "Last name must be non-empty and alphabetic.")
        )
    return errors


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


def participate(participant: Participant):
    pass


async def create_contract(contract: Contract, contract_amounts: list[int] = []):
    if len(errors := validate_contract(contract, contract_amounts)) > 0:
        raise ValidationException(errors)
    _db.insert_contract(contract)
