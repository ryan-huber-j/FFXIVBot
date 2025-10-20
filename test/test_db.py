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
        result = self.db_client.get_participant(987654321)
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
        result = self.db_client.get_participant("nonexistent_id")
        self.assertIsNone(result)

    def test_get_all_participants(self):
        participant1 = Participant(
            discord_id=111111111, first_name="Alice", last_name="Wonder", is_coach=False
        )
        participant2 = Participant(
            discord_id=222222222, first_name="Bob", last_name="Builder", is_coach=True
        )
        self.db_client.insert_participant(participant1)
        self.db_client.insert_participant(participant2)
        result = self.db_client.get_all_participants()
        self.assertEqual(len(result), 2)
        self.assertIn(participant1, result)
        self.assertIn(participant2, result)

    def test_should_return_empty_list_when_no_participants(self):
        result = self.db_client.get_all_participants()
        self.assertEqual(len(result), 0)

    def test_should_delete_participant(self):
        participant = Participant(
            discord_id=555555555, first_name="Test", last_name="User", is_coach=False
        )
        self.db_client.insert_participant(participant)
        self.db_client.delete_participant(555555555)
        result = self.db_client.get_participant(555555555)
        self.assertIsNone(result)

    def test_should_handle_deletion_of_nonexistent_participant_gracefully(self):
        try:
            self.db_client.delete_participant(999999999)
        except Exception as e:
            self.fail(f"Deletion of nonexistent participant raised an exception: {e}")

    def test_should_delete_contract(self):
        contract = Contract(discord_id=123456789, amount=100)
        self.db_client.insert_contract(contract)
        self.db_client.delete_contract(123456789)
        result = self.db_client.get_contract(123456789)
        self.assertIsNone(result)

    def test_should_handle_deletion_of_nonexistent_contract_gracefully(self):
        try:
            self.db_client.delete_contract(888888888)
        except Exception as e:
            self.fail(f"Deletion of nonexistent contract raised an exception: {e}")


class TestContracts(unittest.TestCase):
    def setUp(self):
        self.db_client = SqlLiteClient(":memory:")

    def test_should_insert_contract(self):
        contract = Contract(discord_id=123456789, amount=100)
        self.db_client.insert_contract(contract)
        result = self.db_client.get_contract(123456789)
        self.assertIsNotNone(result)
        self.assertEqual(result, contract)

    def test_should_return_none_for_nonexistent_contract(self):
        result = self.db_client.get_contract("nonexistent_id")
        self.assertIsNone(result)

    def test_should_fail_on_multiple_inserts_with_same_discord_id(self):
        contract1 = Contract(discord_id=123456789, amount=100)
        contract2 = Contract(discord_id=123456789, amount=200)
        self.db_client.insert_contract(contract1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db_client.insert_contract(contract2)
