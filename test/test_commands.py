import unittest

from commands import *

tc = unittest.TestCase()
contract_values = [300000, 420000, 500000, 800000, 1000000]
default_discord_id = 123456789012345678


def default_contract(
    discord_id=default_discord_id,
    amount=500000,
) -> Contract:
    return Contract(
        discord_id=discord_id,
        amount=amount,
    )


def default_participant(
    discord_id=default_discord_id, first_name="Juhdu", last_name="Khigbaa", is_coach=False
) -> Participant:
    return Participant(
        discord_id=discord_id,
        first_name=first_name,
        last_name=last_name,
        is_coach=is_coach,
    )


def assert_error(errors, field, message):
    tc.assertEqual(len(errors), 1)
    tc.assertEqual(errors[0].field, field)
    tc.assertEqual(errors[0].message, message)


class TestValidateParticipant(unittest.TestCase):
    def test_valid_input(self):
        errors = validate_participant(default_participant())
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


class TestValidateContract(unittest.TestCase):
    def test_valid_input(self):
        errors = validate_contract(default_contract(), contract_values)
        self.assertEqual(len(errors), 0)

    def test_invalid_discord_id(self):
        tests = ["not_an_int", 123.456, None, [], {}]
        for test in tests:
            with self.subTest(discord_id=test):
                errors = validate_contract(
                    default_contract(discord_id=test), contract_values
                )
                assert_error(errors, "discord_id", "Discord ID must be an integer.")

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


class TestParticipate(unittest.TestCase):
    def setUp(self):
        self.db = SqlLiteClient(":memory:")
        initialize_db(self.db)

    def test_participate_no_error(self):
        participant = default_participant()
        participate(participant)
        stored_participant = self.db.get_participant_by_discord_id(participant.discord_id)
        self.assertEqual(stored_participant, participant)

    def test_participate_invalid_participant(self):
        participant = Participant(
            discord_id="not_an_int",
            first_name="Juhdu 123",
            last_name="Kh igs09j3kE$$##baa",
            is_coach=False,
        )
        with self.assertRaises(ValidationException) as ve:
            participate(participant)
        errors = ve.exception.errors
        self.assertEqual(len(errors), 3)


class TestCreateContract(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SqlLiteClient(":memory:")
        initialize_db(self.db)

    def default_input(
        self,
        discord_id=default_discord_id,
        first_name="Juhdu",
        last_name="Khigbaa",
        amount=500000,
    ) -> ContractInput:
        return ContractInput(
            discord_id=discord_id,
            first_name=first_name,
            last_name=last_name,
            amount=amount,
            contract_amounts=contract_values,
        )

    async def test_valid_contract_creation(self):
        await create_contract(self.default_input())
        stored_contract = self.db.get_contract_by_discord_id(default_discord_id)
        self.assertEqual(stored_contract, default_contract())

    async def test_invalid_contract_raises_exception(self):
        input = self.default_input(amount=-500000, first_name="Juhdu 123")
        with self.assertRaises(ValidationException) as ve:
            await create_contract(input)
        errors = ve.exception.errors
        self.assertEqual(len(errors), 2)
