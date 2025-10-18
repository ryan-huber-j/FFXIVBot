import unittest

from commands import *

tc = unittest.TestCase()
contract_values = [300000, 420000, 500000, 800000, 1000000]


def default_contract(
    discord_id=123456789012345678, first_name="Juhdu", last_name="Khigbaa", amount=500000
) -> Contract:
    return Contract(
        discord_id=discord_id, first_name=first_name, last_name=last_name, amount=amount
    )


def default_participant(
    discord_id=123456789012345678, first_name="Juhdu", last_name="Khigbaa"
) -> Participant:
    return Participant(discord_id=discord_id, first_name=first_name, last_name=last_name)


def assert_error(errors, field, message):
    tc.assertEqual(len(errors), 1)
    tc.assertEqual(errors[0].field, field)
    tc.assertEqual(errors[0].message, message)


class TestValidateParticipant(unittest.TestCase):
    def test_valid_input(self):
        errors = validate_participant(
            Participant(
                discord_id=123456789012345678, first_name="Juhdu", last_name="Khigbaa"
            )
        )
        self.assertEqual(len(errors), 0)

    def test_invalid_discord_id(self):
        tests = ["not_an_int", 123.456, None, [], {}]
        for test in tests:
            with self.subTest(discord_id=test):
                errors = validate_participant(default_participant(discord_id=test))
                assert_error(errors, "discord_id", "Discord ID must be an integer.")

    def test_invalid_first_name(self):
        tests = ["", "Juhdu with Spaces", "Juhdu-Khigbaa", " ", "/4iieh)OEWP\\"]
        for test in tests:
            with self.subTest(first_name=test):
                errors = validate_participant(default_participant(first_name=test))
                assert_error(
                    errors, "first_name", "First name must be non-empty and alphabetic."
                )

    def test_invalid_last_name(self):
        tests = ["", "Khigbaa with Spaces", "Khigbaa-Khigbaa", " ", "/4iieh)OEWP\\"]
        for test in tests:
            with self.subTest(last_name=test):
                errors = validate_participant(default_participant(last_name=test))
                assert_error(
                    errors, "last_name", "Last name must be non-empty and alphabetic."
                )


class TestParticipate(unittest.TestCase):
    def test_participate_no_error(self):
        participant = Participant(
            discord_id=123456789012345678, first_name="Juhdu", last_name="Khigbaa"
        )
        try:
            participate(participant)
        except Exception as e:
            self.fail(f"participate() raised an exception: {e}")

    def test_participate_invalid_participant(self):
        participant = Participant(
            discord_id="not_an_int",
            first_name="Juhdu 123",
            last_name="Kh igs09j3kE$$##baa",
        )
        try:
            participate(participant)
        except Exception as e:
            self.fail(f"participate() raised an exception: {e}")


class TestValidateContractInput(unittest.TestCase):
    def test_valid_input(self):
        errors = validate_contract(default_contract(), contract_values)
        self.assertEqual(len(errors), 0)

    def test_invalid_seals(self):
        tests = [0, -1, -100, 300001, 430000, 1e8]
        for test in tests:
            with self.subTest(amount=test):
                errors = validate_contract(default_contract(amount=test), contract_values)
                assert_error(
                    errors,
                    "amount",
                    "Amount must be one of: 300000, 420000, 500000, 800000, 1000000.",
                )

    def test_invalid_first_name(self):
        tests = ["", "Juhdu with Spaces", "Juhdu-Khigbaa", " ", "/4iieh)OEWP\\"]
        for test in tests:
            with self.subTest(first_name=test):
                errors = validate_contract(
                    default_contract(first_name=test), contract_values
                )
                assert_error(
                    errors, "first_name", "First name must be non-empty and alphabetic."
                )

    def test_invalid_last_name(self):
        tests = ["", "Khigbaa with Spaces", "Khigbaa-Khigbaa", " ", "/4iieh)OEWP\\"]
        for test in tests:
            with self.subTest(last_name=test):
                errors = validate_contract(
                    default_contract(last_name=test), contract_values
                )
                assert_error(
                    errors, "last_name", "Last name must be non-empty and alphabetic."
                )


class TestCreateContract(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SqlLiteClient(":memory:")
        initialize_db(self.db)

    async def test_valid_contract_creation(self):
        contract = default_contract()
        await create_contract(contract, contract_values)
        stored_contract = self.db.get_contract_by_discord_id(123456789012345678)
        self.assertEqual(stored_contract, contract)

    async def test_invalid_contract_raises_exception(self):
        contract = default_contract(
            first_name="Juhdu 123", last_name="Khigba  a", amount=-500000
        )
        with self.assertRaises(ValidationException) as ve:
            await create_contract(contract, contract_values)
        errors = ve.exception.errors
        self.assertEqual(len(errors), 3)
