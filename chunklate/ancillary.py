from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkNameSemantics:
    name: str
    letters: tuple[str, ...]

    @property
    def follows_naming(self) -> bool:
        return len(self.letters) == 4

    @property
    def is_critical(self) -> bool:
        return self.letters[0].isupper()

    @property
    def is_private(self) -> bool:
        return self.letters[1].isupper()

    @property
    def is_reserved_valid(self) -> bool:
        return self.letters[2].isupper()

    @property
    def is_unsafe_to_copy(self) -> bool:
        return self.letters[3].isupper()


def chunk_name_semantics(chunk: object) -> ChunkNameSemantics:
    name = str(chunk)
    charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    letters = []
    for character in name:
        if character in charset:
            letters.append(character)
        else:
            break
    return ChunkNameSemantics(name=name, letters=tuple(letters))


def semantic_labels(semantics: ChunkNameSemantics) -> tuple[tuple[str, str], ...]:
    if not semantics.follows_naming:
        return ()
    return (
        (semantics.letters[0], "Critical" if semantics.is_critical else "Not Critical"),
        (semantics.letters[1], "Private" if semantics.is_private else "Not Private"),
        (
            semantics.letters[2],
            (
                "Conform to PNG specifications"
                if semantics.is_reserved_valid
                else "Not Conform to PNG specifications"
            ),
        ),
        (semantics.letters[3], "Unsafe to Copy" if semantics.is_unsafe_to_copy else "Safe to Copy"),
    )
