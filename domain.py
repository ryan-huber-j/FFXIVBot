from enum import Enum
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


class ProfessionalsException(Exception):
    def __init__(self, log_message: str, user_message: str):
        super().__init__(log_message)
        self.user_message = user_message


class FCMember(NamedTuple):
    ffxiv_id: str
    name: str
    rank: str


class GrandCompanyRanking(NamedTuple):
    character_id: str
    character_name: str
    rank: int
    seals: int


class FreeCompany(NamedTuple):
    id: str
    name: str


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


class PlayerScore(NamedTuple):
    discord_id: int
    first_name: str
    last_name: str
    seals_earned: int
    is_coach: bool = False


class WinReason(Enum):
    HIGHEST_SEALS = 1
    TIE_BREAKER = 2
    NO_ELIGIBLE_PLAYERS = 3
    RANDOM_DRAWING = 4


class CompletedContract(NamedTuple):
    discord_id: int
    first_name: str
    last_name: str
    amount: int
    is_completed: bool
    payout: int


class HonorableMention(NamedTuple):
    first_name: str
    last_name: str
    rank: int
    seals_earned: int


class CompetitionResults(NamedTuple):
    player_scores: list[PlayerScore]
    competition_winner: PlayerScore | None
    drawing_winner: PlayerScore | None
    competition_win_reason: WinReason
    drawing_win_reason: WinReason
    completed_contracts: list[CompletedContract]
    honorable_mentions: list[HonorableMention]
