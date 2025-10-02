import unittest

from backends.db import *

class TestDatabaseBackend(unittest.TestCase):
    def setUp(self):
        self.db_client = SqlLiteClient(":memory:")

    def test_should_insert_contract(self):
        contract = Contract(
            discord_id="123456789",
            first_name="John",
            last_name="Doe",
            amount=100
        )
        self.db_client.insert_contract(contract)
        result = self.db_client.get_contract_by_discord_id("123456789")
        self.assertIsNotNone(result)
        self.assertEqual(result, contract)

    def test_should_return_none_for_nonexistent_contract(self):
        result = self.db_client.get_contract_by_discord_id("nonexistent_id")
        self.assertIsNone(result)

    def test_should_fail_on_multiple_inserts_with_same_discord_id(self):
        contract1 = Contract(
            discord_id="123456789",
            first_name="John",
            last_name="Doe",
            amount=100
        )
        contract2 = Contract(
            discord_id="123456789",
            first_name="Jane",
            last_name="Smith",
            amount=200
        )
        self.db_client.insert_contract(contract1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db_client.insert_contract(contract2)
