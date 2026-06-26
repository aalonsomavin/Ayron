from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class UnsupportedFormatError(ValueError):
    pass


@dataclass
class ParsedUpload:
    content_json: dict
    preview_html: str
    mime_type: str
    format_key: str
    parse_warnings: list[str] = field(default_factory=list)


class FileParser(Protocol):
    extensions: frozenset[str]
    mime_types: frozenset[str]

    def supports(self, mime_type: str, original_name: str) -> bool: ...

    def parse(self, file_bytes: bytes, original_name: str) -> ParsedUpload: ...


PARSERS: list[FileParser] = []


def _register_parsers() -> None:
    from apps.files.parsers.xlsx import XlsxParser

    global PARSERS
    PARSERS = [XlsxParser()]


def _parser_extensions(parser: FileParser) -> frozenset[str]:
    return frozenset(getattr(parser, "extensions", frozenset()))


def _parser_mimes(parser: FileParser) -> frozenset[str]:
    return frozenset(getattr(parser, "mime_types", frozenset()))


def supported_upload_extensions() -> frozenset[str]:
    if not PARSERS:
        _register_parsers()
    extensions: set[str] = set()
    for parser in PARSERS:
        extensions.update(_parser_extensions(parser))
    return frozenset(extensions)


def supported_upload_mimes() -> frozenset[str]:
    if not PARSERS:
        _register_parsers()
    mimes: set[str] = set()
    for parser in PARSERS:
        mimes.update(_parser_mimes(parser))
    return frozenset(mimes)


def supported_upload_accept() -> str:
    parts = sorted(supported_upload_extensions()) + sorted(supported_upload_mimes())
    return ",".join(parts)


def parse_upload(file_bytes: bytes, original_name: str, mime_type: str = "") -> ParsedUpload:
    if not PARSERS:
        _register_parsers()
    for parser in PARSERS:
        if parser.supports(mime_type, original_name):
            return parser.parse(file_bytes, original_name)
    raise UnsupportedFormatError(f"Unsupported file format: {original_name}")


def is_supported_upload(mime_type: str, original_name: str) -> bool:
    if not PARSERS:
        _register_parsers()
    return any(parser.supports(mime_type, original_name) for parser in PARSERS)
