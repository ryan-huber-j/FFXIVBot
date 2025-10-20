import unittest

from commands import *
from domain import WinReason

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


def default_contract_input(
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


class TestParticipation(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SqlLiteClient(":memory:")
        initialize(self.db, None)

    async def test_should_store_valid_participant_as_non_coach(self):
        participant = default_participant()
        await participate_as_player(
            participant.discord_id, participant.first_name, participant.last_name
        )
        stored_participant = self.db.get_participant(participant.discord_id)
        self.assertEqual(stored_participant, participant)

    async def test_should_store_valid_coach(self):
        coach = default_participant(is_coach=True)
        await participate_as_coach(coach.discord_id, coach.first_name, coach.last_name)
        stored_participant = self.db.get_participant(coach.discord_id)
        self.assertEqual(stored_participant, coach)

    async def test_invalid_participant(self):
        with self.assertRaises(ValidationException) as ve:
            await participate_as_player("not an int", "Juhdu 123", "Kh igs09j3kE$$##baa")
        errors = ve.exception.errors
        self.assertEqual(len(errors), 3)

    async def test_invalid_coach(self):
        with self.assertRaises(ValidationException) as ve:
            await participate_as_coach("not an int", "", "Khigbaa123")
        errors = ve.exception.errors
        self.assertEqual(len(errors), 3)

    async def test_should_end_participation(self):
        participant = default_participant()
        await participate_as_player(
            participant.discord_id, participant.first_name, participant.last_name
        )
        await end_participation(participant.discord_id)
        stored_participant = self.db.get_participant(participant.discord_id)
        self.assertIsNone(stored_participant)

    async def test_should_end_participation_with_contract(self):
        participant = default_participant()
        contract = default_contract()
        await participate_as_player(
            participant.discord_id, participant.first_name, participant.last_name
        )
        await create_contract(default_contract_input())
        await end_participation(participant.discord_id)
        stored_participant = self.db.get_participant(participant.discord_id)
        stored_contract = self.db.get_contract(contract.discord_id)
        self.assertIsNone(stored_participant)
        self.assertIsNone(stored_contract)


class TestCreateContract(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SqlLiteClient(":memory:")
        initialize(self.db, None)

    async def test_valid_contract_creation(self):
        await create_contract(default_contract_input())
        stored_contract = self.db.get_contract(default_discord_id)
        self.assertEqual(stored_contract, default_contract())

    async def test_invalid_contract_raises_exception(self):
        input = default_contract_input(amount=-500000, first_name="Juhdu 123")
        with self.assertRaises(ValidationException) as ve:
            await create_contract(input)
        errors = ve.exception.errors
        self.assertEqual(len(errors), 2)

    async def test_should_end_contract(self):
        contract = default_contract()
        await create_contract(default_contract_input())
        await end_contract(contract.discord_id)
        stored_contract = self.db.get_contract(contract.discord_id)
        self.assertIsNone(stored_contract)


class TestFindCompetitionWinner(unittest.TestCase):
    def test_no_players(self):
        winner, reason = find_competition_winner([])
        self.assertIsNone(winner)
        self.assertEqual(reason, WinReason.NO_ELIGIBLE_PLAYERS)

    def test_single_player(self):
        player = PlayerScore(123, "Juhdu", "Khigbaa", 500000)
        winner, reason = find_competition_winner([player])
        self.assertEqual(winner, player)
        self.assertEqual(reason, WinReason.HIGHEST_SEALS)

    def test_multiple_players_highest_seals(self):
        player1 = PlayerScore(123, "Juhdu", "Khigbaa", 500000)
        player2 = PlayerScore(456, "Another", "Player", 800000)
        player3 = PlayerScore(789, "Third", "Gamer", 300000)
        winner, reason = find_competition_winner([player1, player2, player3])
        self.assertEqual(winner, player2)
        self.assertEqual(reason, WinReason.HIGHEST_SEALS)

    def test_tie_breaker(self):
        player1 = PlayerScore(123, "Juhdu", "Khigbaa", 800000)
        player2 = PlayerScore(456, "Another", "Player", 800000)
        player3 = PlayerScore(789, "Third", "Gamer", 300000)
        winner, reason = find_competition_winner([player1, player2, player3])
        self.assertIsNotNone(winner)
        self.assertIn(winner, [player1, player2])
        self.assertEqual(reason, WinReason.TIE_BREAKER)


class TestFindDrawingWinner(unittest.TestCase):
    def test_no_players(self):
        winner = find_drawing_winner([])
        self.assertIsNone(winner)

    def test_single_player(self):
        player = Participant(123, "Juhdu", "Khigbaa", False)
        winner = find_drawing_winner([player])
        self.assertEqual(winner, player)

    def test_multiple_players(self):
        player1 = Participant(123, "Juhdu", "Khigbaa", False)
        player2 = Participant(456, "Another", "Player", False)
        player3 = Participant(789, "Third", "Gamer", False)
        winner = find_drawing_winner([player1, player2, player3])
        self.assertIsNotNone(winner)
        self.assertIn(winner, [player1, player2, player3])


class TestGetCompetitionResults(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SqlLiteClient(":memory:")
        initialize(self.db, None)

    def check_for_participant_in_results(self, results, participant):
        for ps in results.player_scores:
            if (
                ps.discord_id == participant.discord_id
                and ps.first_name == participant.first_name
                and ps.last_name == participant.last_name
            ):
                return
        self.fail(f"Participant {participant} not found in results.")

    async def test_should_return_no_results_when_no_competitors(self):
        results = await get_competition_results()
        self.assertEqual(results.player_scores, [])
        self.assertIsNone(results.competition_winner)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.competition_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.completed_contracts, [])

    async def test_should_return_single_competitor_as_winner(self):
        participant = default_participant()
        self.db.insert_participant(participant)
        results = await get_competition_results()
        self.check_for_participant_in_results(results, participant)
        self.assertIsNotNone(results.competition_winner)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.completed_contracts, [])
