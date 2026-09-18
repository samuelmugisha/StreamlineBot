"""Unit tests for backend.app.sentiment — pure keyword-based scoring, no mocking needed."""

import pytest

from backend.app.sentiment import analyze_message


@pytest.mark.parametrize("message", ["hello", "How do I add a new deal?", "thanks, that helped"])
def test_calm_message_scores_low_frustration(message):
    result = analyze_message(message)
    assert result.frustration == 1
    assert result.wants_human is False


def test_single_negative_word_bumps_score():
    result = analyze_message("this is broken")
    assert result.frustration == 2


def test_multiple_negative_words_score_higher():
    result = analyze_message("this is terrible, useless, and ridiculous")
    assert result.frustration >= 3


def test_shouting_increases_score():
    result = analyze_message("THIS DOES NOT WORK AT ALL PLEASE HELP")
    assert result.frustration >= 2


def test_score_is_capped_at_five():
    result = analyze_message("TERRIBLE AWFUL USELESS BROKEN GARBAGE TRASH!!!")
    assert result.frustration == 5


@pytest.mark.parametrize(
    "message",
    [
        "can I talk to a human?",
        "I want to speak with an agent",
        "connect me to customer support",
        "let me talk to a real person please",
    ],
)
def test_direct_human_request_detected(message):
    assert analyze_message(message).wants_human is True


def test_agreement_after_escalation_offer_counts_as_wants_human():
    previous_answer = "I can notify our support team and have them follow up with you by email."
    result = analyze_message("yes please", previous_answer=previous_answer)
    assert result.wants_human is True


def test_agreement_without_prior_offer_does_not_trigger_escalation():
    result = analyze_message("yes please", previous_answer="Here is how you add a new deal.")
    assert result.wants_human is False


def test_bare_agreement_with_no_history_does_not_trigger_escalation():
    result = analyze_message("sure")
    assert result.wants_human is False
