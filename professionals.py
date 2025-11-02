import random
from typing import AsyncGenerator, Tuple

from config import load_config
from db import SqlLiteClient
from domain import *
from lodestone import LodestoneScraper

_db = None
_lodestone = None
_config = load_config()


def initialize(db: SqlLiteClient, scraper: LodestoneScraper):
    global _db, _lodestone
    _db = db
    _lodestone = scraper


def validate_discord_id(discord_id) -> list[ValidationError]:
    errors = []
    if not isinstance(discord_id, int):
        errors.append(ValidationError("discord_id", "must be an integer."))
    return errors


def validate_alphanumeric(name: str, field_name: str) -> list[ValidationError]:
    errors = []
    if not name.isalnum() and name != "":
        errors.append(ValidationError(field_name, "must be alphanumeric."))
    return errors


def validate_participant(participant: Participant) -> list[ValidationError]:
    errors = validate_discord_id(participant.discord_id)
    if participant.first_name == "":
        errors.append(ValidationError("first_name", "must be non-empty."))
    else:
        errors += validate_alphanumeric(participant.first_name, "first_name")
    if participant.last_name == "":
        errors.append(ValidationError("last_name", "must be non-empty."))
    else:
        errors += validate_alphanumeric(participant.last_name, "last_name")
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
    _db.upsert_participant(participant)


async def participate_as_coach(discord_id: int, first_name: str, last_name: str):
    participant = Participant(
        discord_id=discord_id,
        first_name=first_name,
        last_name=last_name,
        is_coach=True,
    )
    if len(errors := validate_participant(participant)) > 0:
        raise ValidationException(errors)
    _db.upsert_participant(participant)
    _db.delete_contract(discord_id)


async def end_participation(discord_id: int):
    if len(errors := validate_discord_id(discord_id)) > 0:
        raise ValidationException(errors)
    _db.delete_participant(discord_id)
    _db.delete_contract(discord_id)


def validate_contract_input(contract: ContractInput) -> list[ValidationError]:
    errors = validate_discord_id(contract.discord_id)
    contract_amounts = contract.contract_amounts

    if contract.amount not in contract_amounts:
        if len(contract_amounts) == 1:
            contract_amounts_str = f"must be {contract_amounts[0]}."
        elif len(contract_amounts) == 2:
            contract_amounts_str = (
                f"must be {contract_amounts[0]} or {contract_amounts[1]}."
            )
        else:
            sorted_amounts = sorted(contract_amounts)
            contract_amounts_str = (
                f"must be one of: {', '.join(str(amount) for amount in sorted_amounts[:-1])}, "
                f"or {sorted_amounts[-1]}."
            )
        errors.append(ValidationError("amount", contract_amounts_str))

    if contract.first_name != "" and contract.last_name == "":
        errors.append(
            ValidationError("last_name", "must be non-empty if first name is provided.")
        )
    elif contract.last_name != "" and contract.first_name == "":
        errors.append(
            ValidationError("first_name", "must be non-empty if last name is provided.")
        )
    else:
        errors += validate_alphanumeric(contract.first_name, "first_name")
        errors += validate_alphanumeric(contract.last_name, "last_name")

    return errors


async def create_contract(input: ContractInput):
    validation_errors = validate_contract_input(input)
    if len(validation_errors) > 0:
        raise ValidationException(validation_errors)

    participant = _db.get_participant(input.discord_id)
    if participant is None:
        if input.first_name == "" or input.last_name == "":
            raise UserException(
                log_message=f"User {input.discord_id} attempted to create a contract without an existing participant record and no first or last name provided.",
                user_message="First name and last name are required for new participants.",
            )
        participant = Participant(
            discord_id=input.discord_id,
            first_name=input.first_name,
            last_name=input.last_name,
            is_coach=False,
        )
    elif participant.is_coach:
        raise UserException(
            log_message=f"User {input.discord_id} attempted to create a contract but is a coach.",
            user_message="Coaches may not create contracts.",
        )
    else:
        participant = Participant(
            discord_id=input.discord_id,
            first_name=input.first_name,
            last_name=input.last_name,
            is_coach=False,
        )

    _db.upsert_participant(participant)
    contract = Contract(discord_id=input.discord_id, amount=input.amount)
    _db.upsert_contract(contract)


async def end_contract(discord_id: int):
    if len(errors := validate_discord_id(discord_id)) > 0:
        raise ValidationException(errors)
    _db.delete_contract(discord_id)


async def get_participation_status(
    discord_id: int,
) -> Tuple[Participant | None, Contract | None]:
    if len(errors := validate_discord_id(discord_id)) > 0:
        raise ValidationException(errors)
    participant = _db.get_participant(discord_id)
    contract = _db.get_contract(discord_id)
    return participant, contract


def score_players_and_honorable_mentions(
    fc_members: list[FCMember],
    participants: list[Participant],
    gc_rankings: list[GrandCompanyRanking],
) -> tuple[list[PlayerScore], list[HonorableMention]]:
    player_scores = []
    honorable_mentions = []

    id_to_rankings: dict[str, list[GrandCompanyRanking]] = {}
    for gcr in gc_rankings:
        id_to_rankings.setdefault(gcr.character_id, []).append(gcr)

    for member in fc_members:
        rankings = id_to_rankings.get(member.ffxiv_id)
        if not rankings:
            continue

        ranking = rankings[0]
        sum_of_seals = sum(r.seals for r in rankings)
        best_ranking = min(r.rank for r in rankings)

        first_name, last_name = member.name.split(" ")

        participant = next(
            (
                p
                for p in participants
                if p.first_name == first_name and p.last_name == last_name
            ),
            None,
        )
        if participant is not None:
            player_scores.append(
                PlayerScore(
                    discord_id=participant.discord_id,
                    first_name=participant.first_name,
                    last_name=participant.last_name,
                    rank=best_ranking,
                    seals_earned=sum_of_seals,
                    is_coach=participant.is_coach,
                )
            )
        else:
            honorable_mentions.append(
                HonorableMention(
                    first_name=member.name.split(" ")[0],
                    last_name=" ".join(member.name.split(" ")[1:]),
                    rank=best_ranking,
                    seals_earned=sum_of_seals,
                )
            )

    return player_scores, honorable_mentions


def find_competition_winner(
    players: list[PlayerScore],
) -> tuple[PlayerScore | None, WinReason]:
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


def evaluate_contracts(
    player_scores: list[PlayerScore],
    contracts: list[Contract],
    amounts_to_payouts: dict[int, int],
) -> list[ContractResult]:
    completed_contracts = []

    for ps in player_scores:
        contract = next((c for c in contracts if c.discord_id == ps.discord_id), None)
        if contract is None:
            continue

        is_completed = ps.seals_earned >= contract.amount
        payout = amounts_to_payouts.get(contract.amount, 0) if is_completed else 0

        completed_contracts.append(
            ContractResult(
                discord_id=ps.discord_id,
                first_name=ps.first_name,
                last_name=ps.last_name,
                amount=contract.amount,
                is_completed=is_completed,
                payout=payout,
            )
        )

    return completed_contracts


async def get_competition_results(
    contract_payouts: dict[int, int]
) -> AsyncGenerator[str | CompetitionResults, None]:
    yield "Fetching participants..."
    participants = _db.get_all_participants()

    yield "Fetching Free Company members..."
    fc_members = _lodestone.get_free_company_members(_config.free_company_id)

    yield "Fetching Grand Company rankings..."
    gc_rankings = _lodestone.get_grand_company_rankings(_config.world_name)

    players, honorable_mentions = score_players_and_honorable_mentions(
        fc_members, participants, gc_rankings
    )

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

    yield "Evaluating contracts..."
    contracts = _db.get_all_contracts()
    contract_results = evaluate_contracts(players, contracts, contract_payouts)

    yield CompetitionResults(
        player_scores=players,
        competition_winner=competition_winner,
        drawing_winner=drawing_winner,
        competition_win_reason=competition_win_reason,
        drawing_win_reason=drawing_win_reason,
        contract_results=contract_results,
        honorable_mentions=honorable_mentions,
    )
