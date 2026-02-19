"""Marimo-Obsessed vault library."""

from vault.index import VaultIndex
from vault.note import Note
from vault.parser import parse_note, parse_wikilinks

__all__ = ["Note", "VaultIndex", "parse_note", "parse_wikilinks"]
