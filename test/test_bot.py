from dataclasses import dataclass
import unittest

import discord

from bot import Scorer, create_contract, get_results_2, mark_winner


class FakeInteraction:
    def __init__(self):
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self.guild = FakeGuild()

class FakeResponse():
    deferred: bool = False
    ephemeral: bool = False
    thinking: bool = False
    async def defer(self, ephemeral: bool=True, thinking: bool=True):
        self.deferred = True
        self.ephemeral = ephemeral
        self.thinking = thinking

class FakeFollowup:
    messages: list = []
    async def send(self, message: str):
        self.messages.append(message)

@dataclass
class FakeChannel:
    name: str

class FakeGuild:
    channels: list[FakeChannel] = []


class TestMainBotFunctions(unittest.TestCase):
    def test_mark_winner_empty_map(self):
        scores = {}
        winner = mark_winner(scores)
        self.assertIsNone(winner)


    def test_mark_winner_single(self):
        scores = {
            1: Scorer(1, "Player 1", 1, 12, "p", False)
        }
        winner = mark_winner(scores)
        self.assertEqual(winner.id, 1)
        self.assertEqual(winner.winner, True)


    def test_mark_winner_all_coaches(self):
        scores = {
            1: Scorer(1, "Coach 1", 1, 12, "c", False),
            3: Scorer(1, "Coach 1", 1, 12, "c", False),
        }
        winner = mark_winner(scores)
        self.assertIsNone(winner)


    def test_mark_winner_one_participant_and_coaches(self):
        scores = {
            123: Scorer(123, "Player 1", 1, 49, "p", False),
            124: Scorer(124, "Coach 1", 24, 12, "c", False),
            4983: Scorer(4983, "Coach 1", 250, 12, "c", False),
        }
        winner = mark_winner(scores)
        self.assertEqual(winner.id, 123)
        self.assertEqual(winner.winner, True)


    def test_mark_winner_multiple_participants_and_coaches(self):
        scores = {
            123: Scorer(123, "Player 1", 1, 49, "p", False),
            234: Scorer(234, "Player 2", 2, 48, "p", False),
            124: Scorer(124, "Coach 1", 24, 12, "c", False),
            4983: Scorer(4983, "Coach 1", 250, 12, "c", False),
        }
        winner = mark_winner(scores)
        self.assertEqual(winner.id, 234)
        self.assertEqual(winner.winner, True)