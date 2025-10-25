from test.request_mocking import mock_fc_members_response, mock_gc_rankings_response
import unittest

import responses

from domain import GrandCompanyRanking, HonorableMention, WinReason
from professionals import *

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
        is_coach=False,
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
                assert_error(errors, "discord_id", "must be an integer.")

    def test_invalid_first_name(self):
        tests = ["Juhdu with Spaces", "Juhdu-Khigbaa", " ", "/4iieh)OEWP\\"]
        for test in tests:
            with self.subTest(first_name=test):
                errors = validate_participant(default_participant(first_name=test))
                assert_error(errors, "first_name", "must be non-empty and alphabetic.")

    def test_invalid_last_name(self):
        tests = ["Khigbaa with Spaces", "Khigbaa-Khigbaa", " ", "/4iieh)OEWP\\"]
        for test in tests:
            with self.subTest(last_name=test):
                errors = validate_participant(default_participant(last_name=test))
                assert_error(errors, "last_name", "must be non-empty and alphabetic.")

    def test_should_accept_empty_first_and_last_name_within_contract_validation(self):
        errors = validate_participant(default_participant(first_name="", last_name=""))
        self.assertEqual(len(errors), 0)


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
                assert_error(errors, "discord_id", "must be an integer.")

    def test_invalid_seals(self):
        tests = [0, -1, -100, 300001, 430000, 1e8]
        for test in tests:
            with self.subTest(amount=test):
                errors = validate_contract(default_contract(amount=test), contract_values)
                assert_error(
                    errors,
                    "amount",
                    "must be one of: 300000, 420000, 500000, 800000, or 1000000.",
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
            await participate_as_coach("not an int", "   ikd", "Khigbaa123")
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
        stored_participant = self.db.get_participant(default_discord_id)
        self.assertEqual(stored_contract, default_contract())
        self.assertEqual(stored_participant, default_participant())

    async def test_graceful_update_of_existing_contract(self):
        await create_contract(default_contract_input())
        updated_amount = 800000
        updated_input = default_contract_input(amount=updated_amount)
        await create_contract(updated_input)
        stored_contract = self.db.get_contract(default_discord_id)
        self.assertEqual(
            stored_contract,
            Contract(discord_id=default_discord_id, amount=updated_amount),
        )

    async def test_graceful_update_of_existing_participant(self):
        await create_contract(default_contract_input())
        updated_first_name = "UpdatedName"
        updated_input = default_contract_input(first_name=updated_first_name)
        await create_contract(updated_input)
        stored_participant = self.db.get_participant(default_discord_id)
        self.assertEqual(
            stored_participant,
            default_participant(first_name=updated_first_name),
        )

    async def test_coaches_may_not_create_contracts(self):
        input = default_contract_input()
        await participate_as_coach(input.discord_id, input.first_name, input.last_name)
        with self.assertRaises(ProfessionalsException) as pe:
            await create_contract(input)
        user_message = pe.exception.user_message
        self.assertEqual(user_message, "Coaches may not create contracts.")

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

    def setup_players(self, ffxiv_ids_to_players, ffxiv_ids_to_honorable_mentions={}):
        for _, player in ffxiv_ids_to_players.items():
            self.db.upsert_participant(
                Participant(
                    discord_id=player.discord_id,
                    first_name=player.first_name,
                    last_name=player.last_name,
                    is_coach=False,
                )
            )

        fc_members = [
            FCMember(
                ffxiv_id=id,
                name=f"{player.first_name} {player.last_name}",
                rank="Member",
            )
            for id, player in ffxiv_ids_to_players.items()
        ] + [
            FCMember(
                ffxiv_id=id,
                name=f"{hm.first_name} {hm.last_name}",
                rank="Member",
            )
            for id, hm in ffxiv_ids_to_honorable_mentions.items()
        ]

        responses.add(
            mock_fc_members_response(
                self.HOSTNAME, 200, FREE_COMPANY_ID, members=fc_members
            )
        )

        gc_rankings = [
            GrandCompanyRanking(
                character_id=id,
                character_name=f"{player.first_name} {player.last_name}",
                rank=1,
                seals=player.seals_earned,
            )
            for id, player in ffxiv_ids_to_players.items()
        ] + [
            GrandCompanyRanking(
                character_id=id,
                character_name=f"{hm.first_name} {hm.last_name}",
                rank=hm.rank,
                seals=hm.seals_earned,
            )
            for id, hm in ffxiv_ids_to_honorable_mentions.items()
        ]

        gc_responses = [
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", gc_rankings, 1),
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", [], 2),
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", [], 3),
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", [], 4),
            mock_gc_rankings_response(self.HOSTNAME, 200, "Siren", [], 5),
        ]

        for gc_response in gc_responses:
            responses.add(gc_response)

    @responses.activate
    async def test_should_return_no_results_when_no_competitors(self):
        self.setup_players({})
        results = await get_competition_results()
        self.assertEqual(results.player_scores, [])
        self.assertIsNone(results.competition_winner)
        self.assertEqual(results.competition_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.completed_contracts, [])

    @responses.activate
    async def test_should_return_single_competitor_as_winner(self):
        player = default_player_score()
        self.setup_players({"123": player})

        results = await get_competition_results()
        self.assertIn(player, results.player_scores)
        self.assertEqual(results.competition_winner, player)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.completed_contracts, [])

    @responses.activate
    async def test_should_assign_two_competitors_correctly(self):
        player = default_player_score()
        player2 = default_player_score(
            discord_id=987654321098765432,
            first_name="Another",
            last_name="Player",
            seals_earned=300000,
        )
        self.setup_players({"123": player, "456": player2})

        results = await get_competition_results()
        self.assertIn(player, results.player_scores)
        self.assertIn(player2, results.player_scores)
        self.assertEqual(results.competition_winner, player)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertEqual(results.drawing_winner, player2)
        self.assertEqual(results.drawing_win_reason, WinReason.RANDOM_DRAWING)

    @responses.activate
    async def test_should_award_honorable_mentions(self):
        player = default_player_score()
        honorable_mention = HonorableMention(
            first_name="Honorable",
            last_name="Mention",
            rank=10,
            seals_earned=250000,
        )
        self.setup_players({"123": player}, {"honorable1": honorable_mention})

        results = await get_competition_results()
        self.assertIn(player, results.player_scores)
        self.assertEqual(results.competition_winner, player)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.honorable_mentions, [honorable_mention])
