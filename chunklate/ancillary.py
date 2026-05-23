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
