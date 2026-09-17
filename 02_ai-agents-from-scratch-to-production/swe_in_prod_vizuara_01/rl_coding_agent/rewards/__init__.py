"""Rewards module for verifiable coding agent training."""

from rewards.syntax import SyntaxReward
from rewards.verifier import TestRunnerReward
from rewards.composite import CompositeReward

__all__ = ["SyntaxReward", "TestRunnerReward", "CompositeReward"]
