"""One parse per distinct formula text.

The rules, the graph, the redundancy comparison and the findings all parse formulas; on an
8,600-line-item estate that was 73,000 parses for 6,700 formulas, and the parser is where the
time went. Every consumer reads the AST and builds new structures from it (none mutates it), so
one shared parse per formula text is safe. The cache lives for the process: the CLI runs once
and exits, and the web service runs each analysis in its own subprocess.
"""
from __future__ import annotations
from functools import lru_cache
from anaplan_grammar.parser import parse as _parse, references_ctx, ParseError  # noqa: F401
from anaplan_grammar.lexer import LexError  # noqa: F401


@lru_cache(maxsize=None)
def parse(formula: str):
    return _parse(formula)


def clear() -> None:
    parse.cache_clear()
