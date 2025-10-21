from operator import iand
import random
from typing import Iterable, Tuple

from db import SqlLiteClient
from domain import (
    CompetitionResults,
    Contract,
    ContractInput,
    FCMember,
    GrandCompanyRanking,
    Participant,
    PlayerScore,
    ValidationError,
    ValidationException,
    WinReason,
)
from lodestone import LodestoneScraper

FREE_COMPANY_ID = "9231394073691073564"
WORLD = "Siren"

_db = None
_lodestone = None


def initialize(db: SqlLiteClient, scraper: LodestoneScraper):
    global _db, _lodestone
    _db = db
    _lodestone = scraper


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
    if len(errors := validate_discord_id(discord_id)) > 0:
        raise ValidationException(errors)
    _db.delete_participant(discord_id)
    _db.delete_contract(discord_id)


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
    if len(errors := validate_discord_id(discord_id)) > 0:
        raise ValidationException(errors)
    _db.delete_contract(discord_id)


def assemble_eligible_player_scores(
    fc_members: list[FCMember],
    participants: list[Participant],
    gc_rankings: list[GrandCompanyRanking],
) -> list[PlayerScore]:
    player_scores = []
    for participant in participants:
        name = f"{participant.first_name} {participant.last_name}"
        member = next((m for m in fc_members if m.name == name), None)
        if member is None:
            continue
        ranking = next(r for r in gc_rankings if r.character_id == member.ffxiv_id)
        player_scores.append(
            PlayerScore(
                discord_id=participant.discord_id,
                first_name=participant.first_name,
                last_name=participant.last_name,
                seals_earned=ranking.seals,
                is_coach=participant.is_coach,
            )
        )
    return player_scores


def find_competition_winner(
    players: list[PlayerScore],
) -> Tuple[PlayerScore | None, WinReason]:
    if len(players) == 0:
        return None, WinReason.NO_ELIGIBLE_PLAYERS

    winner_score = max(player.seals_earned for player in players)
    winners = [player for player in players if player.seals_earned == winner_score]

    if len(winners) > 1:
        choice = random.randint(0, len(winners) - 1)
        return winners[choice], WinReason.TIE_BREAKER

    return winners[0], WinReason.HIGHEST_SEALS


def choose_random_drawing_winner(participants: list[PlayerScore]) -> PlayerScore | None:
    return (
        None
        if len(participants) == 0
        else participants[random.randint(0, len(participants) - 1)]
    )


async def get_competition_results() -> CompetitionResults:
    participants = _db.get_all_participants()
    fc_members = _lodestone.get_free_company_members(FREE_COMPANY_ID)
    gc_rankings = _lodestone.get_grand_company_rankings(WORLD)
    players = assemble_eligible_player_scores(fc_members, participants, gc_rankings)

    eligible_players = [p for p in players if not p.is_coach]
    competition_winner, competition_win_reason = find_competition_winner(eligible_players)

    eligible_for_drawing = [
        p for p in eligible_players if p.discord_id != competition_winner.discord_id
    ]
    drawing_winner = choose_random_drawing_winner(eligible_for_drawing)
    drawing_win_reason = (
        WinReason.RANDOM_DRAWING
        if drawing_winner is not None
        else WinReason.NO_ELIGIBLE_PLAYERS
    )

    return CompetitionResults(
        player_scores=players,
        competition_winner=competition_winner,
        drawing_winner=drawing_winner,
        competition_win_reason=competition_win_reason,
        drawing_win_reason=drawing_win_reason,
        completed_contracts=[],
    )
