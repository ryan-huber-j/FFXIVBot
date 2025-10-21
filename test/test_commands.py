from test.request_mocking import mock_fc_members_response, mock_gc_rankings_response
import unittest

import responses

from commands import *
from domain import GrandCompanyRanking, WinReason

tc = unittest.TestCase()
contract_values = [300000, 420000, 500000, 800000, 1000000]
default_discord_id = 123456789012345678
default_name = "Juhdu Khigbaa"
default_first_name = "Juhdu"
default_last_name = "Khigbaa"


def default_contract(
    discord_id=default_discord_id,
    amount=500000,
) -> Contract:
    return Contract(
        discord_id=discord_id,
        amount=amount,
    )


def default_participant(
    discord_id=default_discord_id,
    first_name=default_first_name,
    last_name=default_last_name,
    is_coach=False,
) -> Participant:
    return Participant(
        discord_id=discord_id,
        first_name=first_name,
        last_name=last_name,
        is_coach=is_coach,
    )


def default_contract_input(
    discord_id=default_discord_id,
    first_name=default_first_name,
    last_name=default_last_name,
    amount=500000,
) -> ContractInput:
    return ContractInput(
        discord_id=discord_id,
        first_name=first_name,
        last_name=last_name,
        amount=amount,
        contract_amounts=contract_values,
    )


def default_player_score(
    discord_id=default_discord_id,
    first_name=default_first_name,
    last_name=default_last_name,
    seals_earned=500000,
) -> PlayerScore:
    return PlayerScore(
        discord_id=discord_id,
        first_name=first_name,
        last_name=last_name,
        seals_earned=seals_earned,
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
        player = default_player_score()
        winner, reason = find_competition_winner([player])
        self.assertEqual(winner, player)
        self.assertEqual(reason, WinReason.HIGHEST_SEALS)

    def test_multiple_players_highest_seals(self):
        player1 = default_player_score()
        player2 = PlayerScore(456, "Another", "Player", 800000)
        player3 = PlayerScore(789, "Third", "Player", 300000)
        winner, reason = find_competition_winner([player1, player2, player3])
        self.assertEqual(winner, player2)
        self.assertEqual(reason, WinReason.HIGHEST_SEALS)

    def test_tie_breaker(self):
        player1 = default_player_score()
        player2 = PlayerScore(456, "Another", "Player", 500000)
        player3 = PlayerScore(789, "Third", "Gamer", 300000)
        winner, reason = find_competition_winner([player1, player2, player3])
        self.assertIsNotNone(winner)
        self.assertIn(winner, [player1, player2])
        self.assertEqual(reason, WinReason.TIE_BREAKER)


class TestFindDrawingWinner(unittest.TestCase):
    def test_no_players(self):
        winner = choose_random_drawing_winner([])
        self.assertIsNone(winner)

    def test_single_player(self):
        player = default_player_score()
        winner = choose_random_drawing_winner([player])
        self.assertEqual(winner, player)

    def test_multiple_players(self):
        player1 = default_player_score()
        player2 = default_player_score(456, "Another", "Player", 600000)
        player3 = default_player_score(789, "Third", "Player", 300000)
        winner = choose_random_drawing_winner([player1, player2, player3])
        self.assertIn(winner, [player1, player2, player3])


class TestGetCompetitionResults(unittest.IsolatedAsyncioTestCase):
    HOSTNAME = "fake.lodestone.test"
    BASE_URL = f"https://{HOSTNAME}"

    def setUp(self):
        self.db = SqlLiteClient(":memory:")
        self.lodestone = LodestoneScraper(self.BASE_URL)
        initialize(self.db, self.lodestone)

    def mock_player_fc_listings(self, players, ffxiv_ids):
        fc_members = [
            FCMember(
                ffxiv_id=ffxiv_id,
                name=f"{player.first_name} {player.last_name}",
                rank="Member",
            )
            for player, ffxiv_id in zip(players, ffxiv_ids)
        ]
        return mock_fc_members_response(
            self.HOSTNAME, 200, FREE_COMPANY_ID, members=fc_members
        )

    def mock_player_gc_rankings(self, players, ffxiv_ids, rankings, seals):
        gc_rankings = [
            GrandCompanyRanking(
                character_id=id,
                character_name=f"{player.first_name} {player.last_name}",
                rank=ranking,
                seals=seals,
            )
            for player, id, ranking, seals in zip(players, ffxiv_ids, rankings, seals)
        ]

        return [
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", gc_rankings, 1),
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", [], 2),
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", [], 3),
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", [], 4),
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", [], 5),
        ]

    def compare_player_with_score(self, participant, player_score):
        self.assertEqual(participant.discord_id, player_score.discord_id)
        self.assertEqual(participant.first_name, player_score.first_name)
        self.assertEqual(participant.last_name, player_score.last_name)

    def check_for_participant_in_results(self, results, participant):
        for ps in results.player_scores:
            if (
                ps.discord_id == participant.discord_id
                and ps.first_name == participant.first_name
                and ps.last_name == participant.last_name
            ):
                return
        self.fail(f"Participant {participant} not found in results.")

    @responses.activate
    async def test_should_return_no_results_when_no_competitors(self):
        participant = default_participant()
        fc_response = self.mock_player_fc_listings([participant], ["123"])
        gc_responses = self.mock_player_gc_rankings(
            [],
            [],
            [],
            [],
        )

        responses.add(fc_response)
        for gcr in gc_responses:
            responses.add(gcr)

        results = await get_competition_results()
        self.assertEqual(results.player_scores, [])
        self.assertIsNone(results.competition_winner)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.competition_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.completed_contracts, [])

    @responses.activate
    async def test_should_return_single_competitor_as_winner(self):
        participant = default_participant()
        fc_response = self.mock_player_fc_listings([participant], ["123"])
        gc_responses = self.mock_player_gc_rankings(
            [participant],
            ["123"],
            [1],
            [500000],
        )

        responses.add(fc_response)

        for gcr in gc_responses:
            responses.add(gcr)

        self.db.insert_participant(participant)
        results = await get_competition_results()
        self.check_for_participant_in_results(results, participant)
        self.compare_player_with_score(participant, results.player_scores[0])
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.completed_contracts, [])

    @responses.activate
    async def test_should_assign_two_competitors_correctly(self):
        participant1 = default_participant()
        participant2 = default_participant(
            discord_id=987654321098765432, first_name="Another", last_name="Player"
        )
        fc_response = self.mock_player_fc_listings(
            [participant1, participant2], ["123", "456"]
        )
        gc_responses = self.mock_player_gc_rankings(
            [participant1, participant2],
            ["123", "456"],
            [1, 2],
            [500000, 300000],
        )

        responses.add(fc_response)
        for gcr in gc_responses:
            responses.add(gcr)

        self.db.insert_participant(participant1)
        self.db.insert_participant(participant2)
        results = await get_competition_results()
        self.check_for_participant_in_results(results, participant1)
        self.check_for_participant_in_results(results, participant2)
        self.compare_player_with_score(participant1, results.competition_winner)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.compare_player_with_score(participant2, results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.RANDOM_DRAWING)
