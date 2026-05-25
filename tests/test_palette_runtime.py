#!/usr/bin/env python3
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import palette, palette_runtime


class EndReached(Exception):
    pass


class FakeNumpy:
    uint8 = object()

    def frombuffer(self, value, dtype):
        return value


class FakeCv2:
    def imdecode(self, value, flags):
        return ("decoded", value, flags)


class FakeImage:
    def fromarray(self, value):
        return ("image", value)


class FailingImage:
    def fromarray(self, value):
        raise ValueError("bad image")


class FakeImageHash:
    def __init__(self, values):
        self.values = iter(values)

    def phash(self, image):
        return next(self.values)


@contextmanager
def clean_stderr(stream):
    yield stream


def libpng_stderr(message):
    @contextmanager
    def redirector(stream):
        stream.write(message.encode())
        yield stream

    return redirector


def build_guess_runtime(calls, side_notes=None, *, hashes=(10, 10, 15), stderr_redirector=clean_stderr, image=None):
    if side_notes is None:
        side_notes = []
    if image is None:
        image = FakeImage()

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    return palette_runtime.PaletteCountGuessRuntime(
        cv2=FakeCv2(),
        numpy=FakeNumpy(),
        image=image,
        imagehash=FakeImageHash(hashes),
        stderr_redirector=stderr_redirector,
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        emit=lambda message: calls.append(("emit", message)),
        candy=candy,
        end=lambda: calls.append(("end",)),
        raw_print=lambda *args: calls.append(("raw_print", args)),
        side_notes=side_notes,
        build_palette_png=lambda before, values, after: calls.append(
            ("build_palette_png", before, tuple(values), after)
        ) or b"png",
    )


def guess_context(**updates):
    values = {
        "x11_colors": ("000000", "111111", "222222"),
        "libpng_errors": ("libpng error:",),
        "ihdr_depth": "2",
    }
    values.update(updates)
    return palette_runtime.PaletteCountGuessContext(**values)


def test_manual_palette_after_index_preserves_legacy_expression():
    assert palette_runtime.manual_palette_after_index(8, 20) == 20
    assert palette_runtime.manual_palette_after_index(0, 20) == 20


def test_manual_palette_slices_preserve_legacy_before_after_cut():
    before, after = palette_runtime.manual_palette_slices("0011223344556677", 4, 10)

    assert before == bytes.fromhex("0011")
    assert after == bytes.fromhex("556677")


def test_create_manual_palette_session_builds_initial_png_and_state():
    calls = []

    def guess_palette_count(before, after):
        calls.append((before, after))
        return 3

    session = palette_runtime.create_manual_palette_session(
        data_hex="0011223344556677",
        data_offset=4,
        chunk_length=10,
        chunk_name=b"PLTE",
        guess_palette_count=guess_palette_count,
    )

    assert calls == [(bytes.fromhex("0011"), bytes.fromhex("556677"))]
    assert session.before == bytes.fromhex("0011")
    assert session.after == bytes.fromhex("556677")
    assert session.wanabyte == palette.initial_manual_palette_png(session.before, b"PLTE", session.after)
    assert session.palette_count == 3
    assert session.state.values == ["empty", "empty", "empty"]
    assert session.state.wanabyte == session.wanabyte


def test_manual_palette_full_new_data_returns_chunk_bytes_between_slices():
    session = palette_runtime.ManualPaletteSession(
        before=b"aa",
        after=b"zz",
        wanabyte=b"aaPLTEzz",
        palette_count=1,
        state=None,
    )
    no_after = palette_runtime.ManualPaletteSession(
        before=b"aa",
        after=b"",
        wanabyte=b"aaPLTE",
        palette_count=1,
        state=None,
    )

    assert palette_runtime.manual_palette_full_new_data(session) == b"PLTE"
    assert palette_runtime.manual_palette_full_new_data(no_after) == b"PLTE"


def test_guess_palette_count_uses_phash_distance_and_records_side_note():
    calls = []
    side_notes = []

    result = palette_runtime.guess_palette_count(
        build_guess_runtime(calls, side_notes),
        guess_context(),
        b"before",
        b"after",
    )

    assert result == 2
    assert (
        "build_palette_png",
        b"before",
        (0, 1118481, 2236962),
        b"after",
    ) in calls
    assert ("emit", "-PLTE palettes number estimation: <green:2>") in calls
    assert side_notes == ["-PLTE palettes number estimation: 2"]


def test_guess_palette_count_preserves_ihdr_depth_fallback():
    calls = []
    side_notes = []

    result = palette_runtime.guess_palette_count(
        build_guess_runtime(calls, side_notes, hashes=(10, 10, 10)),
        guess_context(ihdr_depth="3"),
        b"before",
        b"after",
    )

    assert result == 7
    assert ("emit", "<yellow:Warning:%s>" % "Could not estimate palette number.") in calls
    assert side_notes == [
        "Warning:Could not estimate palette number.Returning Max Palettes number according to IHDR Depht"
    ]


def test_guess_palette_count_routes_libpng_error_to_end():
    calls = []

    palette_runtime.guess_palette_count(
        build_guess_runtime(
            calls,
            hashes=(10, 11, 12),
            stderr_redirector=libpng_stderr("libpng error: broken"),
        ),
        guess_context(),
        b"before",
        b"after",
    )

    assert ("raw_print", ("-Error Guess_Palettes_Nbr():", "libpng error: broken")) in calls
    assert ("end",) in calls


def test_guess_palette_count_routes_image_error_to_betterror_and_end():
    calls = []

    def end():
        calls.append(("end",))
        raise EndReached()

    runtime = build_guess_runtime(calls, image=FailingImage())
    runtime = palette_runtime.PaletteCountGuessRuntime(
        **{**runtime.__dict__, "end": end}
    )

    try:
        palette_runtime.guess_palette_count(
            runtime,
            guess_context(),
            b"before",
            b"after",
        )
    except EndReached:
        pass
    else:
        raise AssertionError("TheEnd should stop image error path")

    assert ("betterror", "bad image", "Guess_Palettes_Nbr") in calls
    assert any(
        call[0] == "raw_print"
        and call[1][0] == "-Error Guess_Palettes_Nbr():"
        and str(call[1][1]) == "bad image"
        for call in calls
    )
    assert ("end",) in calls


def main():
    checks = [
        ("After index", test_manual_palette_after_index_preserves_legacy_expression),
        ("Before/after slices", test_manual_palette_slices_preserve_legacy_before_after_cut),
        ("Manual palette session", test_create_manual_palette_session_builds_initial_png_and_state),
        ("Full new data", test_manual_palette_full_new_data_returns_chunk_bytes_between_slices),
        ("Guess palette count", test_guess_palette_count_uses_phash_distance_and_records_side_note),
        ("Guess palette fallback", test_guess_palette_count_preserves_ihdr_depth_fallback),
        ("Guess palette libpng error", test_guess_palette_count_routes_libpng_error_to_end),
        ("Guess palette image error", test_guess_palette_count_routes_image_error_to_betterror_and_end),
    ]

    print("Running palette runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"palette runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
