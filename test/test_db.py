import unittest

from db import *


class TestParticipants(unittest.TestCase):
    def setUp(self):
        self.db_client = SqlLiteClient(":memory:")

    def test_should_insert_and_retrieve_participant(self):
        participant = Participant(
            discord_id=987654321, first_name="Boy", last_name="Detective", is_coach=True
        )
        self.db_client.insert_participant(participant)
        result = self.db_client.get_participant_by_discord_id(987654321)
        self.assertIsNotNone(result)
        self.assertEqual(result, participant)

    def test_should_fail_on_multiple_inserts_with_same_discord_id(self):
        participant1 = Participant(
            discord_id=987654321, first_name="Boy", last_name="Detective", is_coach=True
        )
        participant2 = Participant(
            discord_id=987654321, first_name="Boy", last_name="Detective", is_coach=False
        )
        self.db_client.insert_participant(participant1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db_client.insert_participant(participant2)

    def test_should_return_none_for_nonexistent_participant(self):
        result = self.db_client.get_participant_by_discord_id("nonexistent_id")
        self.assertIsNone(result)


class TestContracts(unittest.TestCase):
    def setUp(self):
        self.db_client = SqlLiteClient(":memory:")

    def test_should_insert_contract(self):
        contract = Contract(
            discord_id=123456789, amount=100
        )
        self.db_client.insert_contract(contract)
        result = self.db_client.get_contract_by_discord_id(123456789)
        self.assertIsNotNone(result)
        self.assertEqual(result, contract)

    def test_should_return_none_for_nonexistent_contract(self):
        result = self.db_client.get_contract_by_discord_id("nonexistent_id")
        self.assertIsNone(result)

    def test_should_fail_on_multiple_inserts_with_same_discord_id(self):
        contract1 = Contract(
            discord_id=123456789, amount=100
        )
        contract2 = Contract(
            discord_id=123456789, amount=200
        )
        self.db_client.insert_contract(contract1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db_client.insert_contract(contract2)
