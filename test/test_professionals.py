from test.request_mocking import (
    register_fc_members,
    register_fc_rankings,
    register_gc_pages,
)
import unittest

import responses

from domain import GrandCompanyRanking, HonorableMention, WinReason
import professionals
from professionals import *

tc = unittest.TestCase()
contracts = {
    300000: 450000,
    420000: 550000,
    500000: 650000,
    800000: 900000,
    1000000: 3200000,
}
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
        contract_amounts=contracts.keys(),
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
        rank=1,
        seals_earned=seals_earned,
        is_coach=False,
    )


def default_contract_result(
    discord_id=default_discord_id,
    first_name=default_first_name,
    last_name=default_last_name,
    amount=500000,
    is_completed=True,
    payout=650000,
):
    return ContractResult(
        discord_id=discord_id,
        first_name=first_name,
        last_name=last_name,
        amount=amount,
        is_completed=is_completed,
        payout=payout,
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
                assert_error(errors, "first_name", "must be alphanumeric.")

    def test_invalid_last_name(self):
        tests = ["Khigbaa with Spaces", "Khigbaa-Khigbaa", " ", "/4iieh)OEWP\\"]
        for test in tests:
            with self.subTest(last_name=test):
                errors = validate_participant(default_participant(last_name=test))
                assert_error(errors, "last_name", "must be alphanumeric.")

    def test_should_accept_empty_first_and_last_name_within_contract_validation(self):
        errors = validate_participant(default_participant(first_name="", last_name=""))
        self.assertEqual(len(errors), 2)


class TestValidateContractInput(unittest.TestCase):
    def test_valid_input(self):
        errors = validate_contract_input(default_contract_input())
        self.assertEqual(len(errors), 0)

    def test_valid_input_with_no_first_or_last_name(self):
        errors = validate_contract_input(
            default_contract_input(first_name="", last_name="")
        )
        self.assertEqual(len(errors), 0)

    def test_invalid_input_when_only_first_name_empty(self):
        errors = validate_contract_input(
            default_contract_input(first_name="Juhdu", last_name="")
        )
        self.assertEqual(len(errors), 1)

    def test_invalid_input_when_only_last_name_empty(self):
        errors = validate_contract_input(
            default_contract_input(first_name="", last_name="Khigbaa")
        )
        self.assertEqual(len(errors), 1)

    def test_invalid_discord_id(self):
        tests = ["not_an_int", 123.456, None, [], {}]
        for test in tests:
            with self.subTest(discord_id=test):
                errors = validate_contract_input(default_contract_input(discord_id=test))
                assert_error(errors, "discord_id", "must be an integer.")

    def test_invalid_seals(self):
        tests = [0, -1, -100, 300001, 430000, 1e8]
        for test in tests:
            with self.subTest(amount=test):
                errors = validate_contract_input(default_contract_input(amount=test))
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
            await participate_as_coach("not an int", "   ikd", "Khigbaa1 23")
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
        with self.assertRaises(professionals.UserException):
            await create_contract(updated_input)

        # Stored contract should remain unchanged
        stored_contract = self.db.get_contract(default_discord_id)
        self.assertEqual(stored_contract, default_contract())

    async def test_graceful_update_of_existing_participant(self):
        await create_contract(default_contract_input())
        updated_first_name = "UpdatedName"
        updated_input = default_contract_input(first_name=updated_first_name)
        with self.assertRaises(professionals.UserException):
            await create_contract(updated_input)

        stored_participant = self.db.get_participant(default_discord_id)
        # Participant should remain with the original first name
        self.assertEqual(stored_participant, default_participant())

    async def test_coaches_may_not_create_contracts(self):
        input = default_contract_input()
        await participate_as_coach(input.discord_id, input.first_name, input.last_name)
        with self.assertRaises(UserException) as pe:
            await create_contract(input)
        user_message = pe.exception.user_message
        self.assertEqual(user_message, "Coaches may not create contracts.")

    async def test_invalid_contract_raises_exception(self):
        input = default_contract_input(
            amount=500000, first_name="Juhdu 123", last_name="Khigbaa"
        )
        with self.assertRaises(ValidationException) as ve:
            await create_contract(input)
        errors = ve.exception.errors
        self.assertEqual(len(errors), 1)

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
        player2 = PlayerScore(456, "Another", "Player", 1, 800000)
        player3 = PlayerScore(789, "Third", "Player", 2, 300000)
        winner, reason = find_competition_winner([player1, player2, player3])
        self.assertEqual(winner, player2)
        self.assertEqual(reason, WinReason.HIGHEST_SEALS)

    def test_tie_breaker(self):
        player1 = default_player_score()
        player2 = PlayerScore(456, "Another", "Player", 1, 500000)
        player3 = PlayerScore(789, "Third", "Gamer", 2, 300000)
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

    def setup_gc_rankings(self, rankings=[]):
        register_gc_pages(self.HOSTNAME, "Siren", rankings)

    def setup_players(
        self, ffxiv_ids_to_players, ffxiv_ids_to_honorable_mentions={}, contracts=[]
    ):
        for _, player in ffxiv_ids_to_players.items():
            self.db.insert_participant(
                Participant(
                    discord_id=player.discord_id,
                    first_name=player.first_name,
                    last_name=player.last_name,
                    is_coach=player.is_coach,
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

        register_fc_members(
            self.HOSTNAME, professionals._config.free_company_id, fc_members
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

        register_gc_pages(self.HOSTNAME, "Siren", gc_rankings)

        for contract in contracts:
            self.db.insert_contract(contract)

    async def wait_for_results(self):
        async for result in get_competition_results(contracts):
            if isinstance(result, CompetitionResults):
                return result
        self.fail("Did not receive CompetitionResults from async generator.")

    @responses.activate
    async def test_should_return_no_results_when_no_competitors(self):
        self.setup_players({})
        results = await self.wait_for_results()
        self.assertEqual(results.player_scores, [])
        self.assertIsNone(results.competition_winner)
        self.assertEqual(results.competition_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.contract_results, [])

    @responses.activate
    async def test_should_return_single_competitor_as_winner(self):
        player = default_player_score()
        self.setup_players({"123": player})

        results = await self.wait_for_results()
        self.assertIn(player, results.player_scores)
        self.assertEqual(results.competition_winner, player)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.contract_results, [])

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

        results = await self.wait_for_results()
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

        results = await self.wait_for_results()
        self.assertIn(player, results.player_scores)
        self.assertEqual(results.competition_winner, player)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.honorable_mentions, [honorable_mention])

    @responses.activate
    async def test_should_process_completed_contracts(self):
        player = default_player_score()
        contract = default_contract()
        self.setup_players({"123": player}, contracts=[contract])

        results = await self.wait_for_results()
        self.assertIn(player, results.player_scores)
        self.assertEqual(results.competition_winner, player)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.contract_results, [default_contract_result()])

    @responses.activate
    async def test_should_process_incomplete_contracts(self):
        player = default_player_score(seals_earned=200000)
        contract = default_contract()
        self.setup_players({"123": player}, contracts=[contract])

        results = await self.wait_for_results()
        self.assertIn(player, results.player_scores)
        self.assertEqual(results.competition_winner, player)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(
            results.contract_results,
            [default_contract_result(is_completed=False, payout=0)],
        )

    @responses.activate
    async def test_non_ranked_player_scores_0_and_wins_nothing(self):
        participant = default_participant()
        self.db.insert_participant(participant)
        contract = default_contract()
        self.db.insert_contract(contract)
        self.setup_gc_rankings()

        register_fc_members(
            self.HOSTNAME,
            professionals._config.free_company_id,
            [
                FCMember(
                    ffxiv_id="some_id",
                    name=f"{participant.first_name} {participant.last_name}",
                    rank="Member",
                )
            ],
        )

        results = await self.wait_for_results()
        self.assertIsNone(results.competition_winner)
        self.assertEqual(results.competition_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(
            results.contract_results,
            [default_contract_result(is_completed=False, payout=0)],
        )

    @responses.activate
    async def test_honorable_mentions_must_have_rank_to_qualify(self):
        self.setup_gc_rankings()

        register_fc_members(
            self.HOSTNAME,
            professionals._config.free_company_id,
            [
                FCMember(
                    ffxiv_id="some_id",
                    name=f"{default_first_name} {default_last_name}",
                    rank="Member",
                )
            ],
        )

        results = await self.wait_for_results()

        self.assertIsNone(results.competition_winner)
        self.assertEqual(results.competition_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertIsNone(results.drawing_winner)
        self.assertEqual(results.drawing_win_reason, WinReason.NO_ELIGIBLE_PLAYERS)
        self.assertEqual(results.honorable_mentions, [])

    @responses.activate
    async def test_realistic_scenario_with_players_and_coaches(self):
        player1 = default_player_score()
        player2 = default_player_score(
            discord_id=987654321098765432,
            first_name="Another",
            last_name="Player",
            seals_earned=300000,
        )
        coach = PlayerScore(
            discord_id=555555555555555555,
            first_name="Coach",
            last_name="Person",
            rank=1,
            seals_earned=10000000,
            is_coach=True,
        )
        contract1 = default_contract()
        contract2 = Contract(
            discord_id=987654321098765432,
            amount=800000,
        )
        self.setup_players(
            {"123": player1, "456": player2, "555": coach},
            contracts=[contract1, contract2],
        )

        results = await self.wait_for_results()
        self.assertEqual(results.player_scores, [player1, player2, coach])
        self.assertEqual(results.competition_winner, player1)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)
        self.assertEqual(results.drawing_winner, player2)
        self.assertEqual(results.drawing_win_reason, WinReason.RANDOM_DRAWING)
        self.assertEqual(
            results.contract_results,
            [
                default_contract_result(),
                default_contract_result(
                    discord_id=player2.discord_id,
                    first_name=player2.first_name,
                    last_name=player2.last_name,
                    amount=contract2.amount,
                    is_completed=False,
                    payout=0,
                ),
            ],
        )

    @responses.activate
    async def test_should_combine_multiple_rankings_for_single_participant(self):
        playerA = default_player_score(
            discord_id=111111111111111111,
            first_name="Alice",
            last_name="Example",
            seals_earned=25,
        )
        playerB = default_player_score(
            discord_id=222222222222222222,
            first_name="Bob",
            last_name="Player",
            seals_earned=30,
        )

        self.db.insert_participant(
            Participant(
                discord_id=playerA.discord_id,
                first_name=playerA.first_name,
                last_name=playerA.last_name,
                is_coach=False,
            )
        )
        self.db.insert_participant(
            Participant(
                discord_id=playerB.discord_id,
                first_name=playerB.first_name,
                last_name=playerB.last_name,
                is_coach=False,
            )
        )

        fc_members = [
            FCMember(
                ffxiv_id="charA1",
                name=f"{playerA.first_name} {playerA.last_name}",
                rank="Member",
            ),
            FCMember(
                ffxiv_id="charB1",
                name=f"{playerB.first_name} {playerB.last_name}",
                rank="Member",
            ),
        ]

        register_fc_members(
            self.HOSTNAME, professionals._config.free_company_id, fc_members
        )

        gc_rankings = [
            GrandCompanyRanking(
                character_id="charA1",
                character_name=f"{playerA.first_name} {playerA.last_name}",
                rank=1,
                seals=25,
            ),
            GrandCompanyRanking(
                character_id="charA1",
                character_name=f"{playerA.first_name} {playerA.last_name}",
                rank=2,
                seals=25,
            ),
            GrandCompanyRanking(
                character_id="charB1",
                character_name=f"{playerB.first_name} {playerB.last_name}",
                rank=1,
                seals=30,
            ),
        ]

        register_gc_pages(self.HOSTNAME, "Siren", gc_rankings)

        results = await self.wait_for_results()

        playerA_entries = [
            p for p in results.player_scores if p.discord_id == playerA.discord_id
        ]
        self.assertEqual(len(playerA_entries), 1)
        combined = playerA_entries[0]
        self.assertEqual(combined.seals_earned, 50)

        self.assertIsNotNone(results.competition_winner)
        self.assertEqual(results.competition_winner.discord_id, playerA.discord_id)
        self.assertEqual(results.competition_win_reason, WinReason.HIGHEST_SEALS)

        playerB_entry = next(
            p for p in results.player_scores if p.discord_id == playerB.discord_id
        )
        self.assertEqual(playerB_entry.seals_earned, 30)


class TestStartCompetition(unittest.IsolatedAsyncioTestCase):
    HOSTNAME = "fake.lodestone.test"
    BASE_URL = f"https://{HOSTNAME}"

    def setUp(self):
        self.db = SqlLiteClient(":memory:")
        self.lodestone = LodestoneScraper(self.BASE_URL)
        initialize(self.db, self.lodestone)

    @responses.activate
    async def test_happy_path(self):
        register_fc_rankings(
            "fake.lodestone.test",
            "Aether",
            [
                FreeCompanyRanking(
                    ffxiv_id="fc1", name="FC One", rank=1, seals_earned=1000
                ),
                FreeCompanyRanking(
                    ffxiv_id=professionals._config.free_company_id,
                    name="FC Two",
                    rank=2,
                    seals_earned=900,
                ),
            ],
        )

        self.db.insert_contract(default_contract())
        self.db.insert_participant(default_participant())

        last_week_seals = await professionals.start_new_competition()
        self.assertEqual(last_week_seals, 900)
        self.assertEqual(self.db.get_all_contracts(), [])
        self.assertEqual(self.db.get_all_participants(), [])
