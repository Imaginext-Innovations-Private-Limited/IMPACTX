"""Spoken bill summary in six languages, with the same no-invented-numbers guarantee as the screen."""

from .script import build
from .spoken import english_words, spoken, spoken_amount
from .tts import TTSUnavailable, backend, backends, quality, synthesize

__all__ = ["build", "english_words", "spoken", "spoken_amount", "TTSUnavailable", "backend", "backends", "quality", "synthesize"]
