import sqlite3

from domain import Contract, Participant

DB_FILE = "data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS participants (
    discord_id INTEGER NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    is_coach BOOLEAN NOT NULL,
    PRIMARY KEY (discord_id)
);

CREATE TABLE IF NOT EXISTS contracts (
    discord_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    PRIMARY KEY (discord_id)
);
"""


class SqlLiteClient:
    def __init__(self, source: str = DB_FILE):
        self.connection = sqlite3.connect(source)
        self.cursor = self.connection.cursor()
        self.cursor.executescript(SCHEMA)
        self.connection.commit()

    def insert_participant(self, participant: Participant) -> None:
        self.cursor.execute(
            """
            INSERT INTO participants (discord_id, first_name, last_name, is_coach)
            VALUES (?, ?, ?, ?)
            """,
            (
                participant.discord_id,
                participant.first_name,
                participant.last_name,
                participant.is_coach,
            ),
        )
        self.connection.commit()

    def get_participant_by_discord_id(self, discord_id: int) -> Participant | None:
        self.cursor.execute(
            """
            SELECT discord_id, first_name, last_name, is_coach
            FROM participants
            WHERE discord_id = ?
            """,
            (discord_id,),
        )
        row = self.cursor.fetchone()
        return Participant(*row) if row else None

    def insert_contract(self, contract: Contract) -> None:
        self.cursor.execute(
            """
            INSERT INTO contracts (discord_id, amount)
            VALUES (?, ?)
            """,
            (
                contract.discord_id,
                contract.amount,
            ),
        )
        self.connection.commit()

    def get_contract_by_discord_id(self, discord_id: int) -> Contract | None:
        self.cursor.execute(
            """
            SELECT discord_id, amount
            FROM contracts
            WHERE discord_id = ?
            """,
            (discord_id,),
        )
        row = self.cursor.fetchone()
        return Contract(*row) if row else None
