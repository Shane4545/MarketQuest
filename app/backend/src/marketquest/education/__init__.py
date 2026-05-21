"""MarketQuest education layer."""

from marketquest.education.glossary import get_education, get_glossary
from marketquest.education.lesson_cards import get_lessons, lesson_for_event
from marketquest.education.quiz_engine import get_active_challenge, submit_challenge

__all__ = [
    "get_education",
    "get_glossary",
    "get_lessons",
    "lesson_for_event",
    "get_active_challenge",
    "submit_challenge",
]
