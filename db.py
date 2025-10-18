from dataclasses import dataclass
import sqlite3

from domain import Contract

DB_FILE = "data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS contracts (
    discord_id INTEGER NOT NULL,
    character_first_name TEXT NOT NULL,
    character_last_name TEXT NOT NULL,
    amount INTEGER NOT NULL,
    PRIMARY KEY (discord_id)
);
"""


class SqlLiteClient:
    def __init__(self, source: str=DB_FILE):
        self.connection = sqlite3.connect(source)
        self.cursor = self.connection.cursor()
        self.cursor.executescript(SCHEMA)
        self.connection.commit()

    def insert_contract(self, contract: Contract) -> None:
        self.cursor.execute(
            """
            INSERT INTO contracts (discord_id, character_first_name, character_last_name, amount)
            VALUES (?, ?, ?, ?)
            """,
            (contract.discord_id, contract.first_name, contract.last_name, contract.amount)
        )
        self.connection.commit()

    def get_contract_by_discord_id(self, discord_id: int) -> Contract | None:
        self.cursor.execute(
            """
            SELECT discord_id, character_first_name, character_last_name, amount
            FROM contracts
            WHERE discord_id = ?
            """,
            (discord_id,)
        )
        row = self.cursor.fetchone()
        return Contract(*row) if row else None
