from db import SqlLiteClient
from domain import (
    Contract,
    ContractInput,
    Participant,
    ValidationError,
    ValidationException,
)

_db = None


def initialize_db(db: SqlLiteClient):
    global _db
    _db = db


def validate_discord_id(discord_id) -> list[ValidationError]:
    errors = []
    if not isinstance(discord_id, int):
        errors.append(ValidationError("discord_id", "Discord ID must be an integer."))
    return errors


def validate_participant(participant: Participant) -> list[ValidationError]:
    errors = validate_discord_id(participant.discord_id)
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
    errors = validate_discord_id(contract.discord_id)
    if contract.amount not in contract_amounts:
        contract_amounts_str = ", ".join(str(amount) for amount in contract_amounts)
        errors.append(
            ValidationError("amount", f"Amount must be one of: {contract_amounts_str}.")
        )
    return errors


async def participate_as_player(discord_id: int, first_name: str, last_name: str):
    participant = Participant(
        discord_id=discord_id,
        first_name=first_name,
        last_name=last_name,
        is_coach=False,
    )
    if len(errors := validate_participant(participant)) > 0:
        raise ValidationException(errors)
    _db.insert_participant(participant)


async def participate_as_coach(discord_id: int, first_name: str, last_name: str):
    participant = Participant(
        discord_id=discord_id,
        first_name=first_name,
        last_name=last_name,
        is_coach=True,
    )
    if len(errors := validate_participant(participant)) > 0:
        raise ValidationException(errors)
    _db.insert_participant(participant)


async def end_participation(discord_id: int):
    pass


async def create_contract(input: ContractInput):
    participant = Participant(
        discord_id=input.discord_id,
        first_name=input.first_name,
        last_name=input.last_name,
        is_coach=False,
    )
    contract = Contract(discord_id=input.discord_id, amount=input.amount)

    validation_errors = validate_participant(participant) + validate_contract(
        contract, input.contract_amounts
    )
    if len(validation_errors) > 0:
        raise ValidationException(validation_errors)

    _db.insert_contract(contract)


async def end_contract(discord_id: int):
    pass
    # if len(errors := validate_discord_id(discord_id)) > 0:
    #     raise ValidationException(errors)
    # _db.delete_contract_by_discord_id(discord_id)
