#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import bruteforce, bruteforce_runtime, bruteforce_viewer, smash_bruteforce
from types import SimpleNamespace


def build_runtime(calls, *, scan_result, result_value="legacy-result"):
    side_notes = []

    def load_spec(request):
        calls.append(("load_spec", request))
        return "spec"

    def product(chunk_data, color_type):
        calls.append(("product", chunk_data, color_type))
        return []

    def loadingbar(*args):
        calls.append(("loadingbar", args))

    def minibar(**kwargs):
        calls.append(("minibar", kwargs))

    def register_image_viewers(image_show):
        calls.append(("register_image_viewers", image_show))

    def run_scan(scan_runtime, scan_context):
        calls.append(("run_scan", scan_runtime, scan_context))
        return scan_result

    def show_candidate(viewer_runtime, png_bytes, candidate_bytes, loop_index, debug_bytes=None):
        calls.append(
            (
                "show_candidate",
                viewer_runtime,
                png_bytes,
                candidate_bytes,
                loop_index,
                debug_bytes,
            )
        )
        return bruteforce_viewer.BruteForceViewerResult(True, "viewer-diff")

    def run_result(result_runtime, result_context):
        calls.append(("run_result", result_runtime, result_context))
        return result_value

    def sync_state(crash, eta_seconds, diff):
        calls.append(("sync_state", crash, eta_seconds, diff))

    return smash_bruteforce.SmashBruteBrawlLegacyRuntime(
        load_spec=load_spec,
        product=product,
        loadingbar=loadingbar,
        minibar=minibar,
        image_show="ImageShow",
        cv2="cv2",
        numpy="numpy",
        image="Image",
        psutil="psutil",
        stderr_redirector=lambda stream: stream,
        sleep=lambda seconds: None,
        ask_timeout=lambda **kwargs: "yes",
        naming=lambda file_origin: ("name.png", "/tmp"),
        emit=lambda message: calls.append(("emit", message)),
        candy=lambda *args: "candy",
        summarise=lambda message: calls.append(("summarise", message)),
        save_error=lambda error, name: calls.append(("save_error", str(error), name)),
        end=lambda: calls.append(("end",)),
        checkpoint=lambda *args: calls.append(("checkpoint", args)),
        side_notes=side_notes,
        pause=lambda message: calls.append(("pause", message)),
        sync_state=sync_state,
        register_image_viewers=register_image_viewers,
        run_scan=run_scan,
        show_candidate=show_candidate,
        run_result=run_result,
    )


def base_context(**updates):
    context = {
        "file": "broken.png",
        "chunk_name": b"IDAT",
        "chunk_length": 4,
        "data_offset": 16,
        "from_error": "Relics",
        "data_hex": "89504e47",
        "pandora_box": {"key": "value"},
        "libpng_errors": ("libpng error",),
        "tmp_image_paths": [],
        "file_origin": "/tmp/broken.png",
        "current_diff": "old-diff",
        "edit_mode": "Replace",
        "bf_mode": "TwoBytes",
        "brute_crc": True,
        "brute_length": False,
        "old_crc": False,
        "brute_level": 2,
        "crash": 12,
        "debug": True,
        "pause_debug": False,
    }
    context.update(updates)
    return smash_bruteforce.SmashBruteBrawlLegacyContext(**context)


def scan_result(**updates):
    result = {
        "state": bruteforce.BruteForceMatchState(bingo=True, replace_flag=True),
        "old_crc": False,
        "bf_mode": "TwoBytes",
        "full_new_data": b"full",
        "png_bytes": b"png",
        "to_brute": "0011",
        "diff": "new-diff",
        "crash": False,
        "eta_seconds": 42,
    }
    result.update(updates)
    return bruteforce_runtime.SmashBruteBrawlScanResult(**result)


def find_call(calls, name):
    matches = [call for call in calls if call[0] == name]
    assert len(matches) == 1
    return matches[0]


def build_namespace(calls):
    namespace = {
        "Candy": lambda *args: calls.append(("candy", args)) or "candy",
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "DEBUG": False,
        "PRINT": lambda message: calls.append(("emit", message)),
        "GetSpec": lambda *args, **kwargs: calls.append(("get_spec", args, kwargs)) or "loaded-spec",
        "Product": lambda *args: calls.append(("product", args)),
        "Loadingbar": lambda *args: calls.append(("loadingbar", args)),
        "Minibar": lambda **kwargs: calls.append(("minibar", kwargs)),
        "ImageShow": "ImageShow",
        "cv2": "cv2",
        "np": "numpy",
        "Image": "Image",
        "psutil": "psutil",
        "stderr_redirector": lambda stream: stream,
        "time": SimpleNamespace(sleep=lambda seconds: calls.append(("sleep", seconds))),
        "inputimeout": lambda **kwargs: calls.append(("inputimeout", kwargs)) or "yes",
        "Naming": lambda file_origin: ("name.png", "/tmp"),
        "Summarise": lambda message: calls.append(("summarise", message)),
        "TheEnd": lambda: calls.append(("end",)),
        "CheckPoint": lambda *args: calls.append(("checkpoint", args)),
        "SideNotes": [],
        "Pause": lambda message: calls.append(("pause", message)),
        "DATAX": "89504e47",
        "PandoraBox": {"key": "value"},
        "LIBPNG_ERR": ("libpng error",),
        "FILE_Origin": "/tmp/broken.png",
        "DIFF": "old-diff",
        "Brute_LvL": 2,
        "CRASH": False,
        "PAUSEDEBUG": False,
    }
    return namespace


def test_legacy_namespace_entry_builds_bridge_and_syncs_legacy_state():
    calls = []
    namespace = build_namespace(calls)

    def bridge(runtime, context):
        calls.append(("bridge", runtime, context))
        assert runtime.load_spec(
            bruteforce.BruteForceSpecRequest(
                "Spec",
                fields=("Length",),
                struct_indexes=(1,),
                iter_nbr=2,
            )
        ) == "loaded-spec"
        runtime.sync_state("crash", 123, "new-diff")
        return "bridge-result"

    result = smash_bruteforce.run_legacy_smash_brute_brawl_from_namespace(
        namespace,
        "broken.png",
        "IDAT",
        4,
        16,
        "Relics",
        "Replace",
        "TwoBytes",
        True,
        False,
        "old-crc",
        bridge=bridge,
    )

    assert result == "bridge-result"
    assert namespace["TmpImgLst"] == []
    assert namespace["CRASH"] == "crash"
    assert namespace["ETA"] == 123
    assert namespace["DIFF"] == "new-diff"
    assert ("candy", ("Title", "SmashBruteBrawl")) in calls
    assert ("candy", ("Title", "Attempting Bruteforce To Repair Corrupted Chunk Data:")) in calls
    assert (
        "get_spec",
        (b"IDAT", "Spec"),
        {"Fields": ["Length"], "StructIndex": [1], "IterNbr": 2},
    ) in calls

    _name, runtime, context = find_call(calls, "bridge")
    assert runtime.side_notes is namespace["SideNotes"]
    assert context == smash_bruteforce.SmashBruteBrawlLegacyContext(
        file="broken.png",
        chunk_name=b"IDAT",
        chunk_length=4,
        data_offset=16,
        from_error="Relics",
        data_hex="89504e47",
        pandora_box={"key": "value"},
        libpng_errors=("libpng error",),
        tmp_image_paths=namespace["TmpImgLst"],
        file_origin="/tmp/broken.png",
        current_diff="old-diff",
        edit_mode="Replace",
        bf_mode="TwoBytes",
        brute_crc=True,
        brute_length=False,
        old_crc="old-crc",
        brute_level=2,
        crash=False,
        debug=False,
        pause_debug=False,
    )


def test_legacy_namespace_entry_preserves_bytes_chunk_name_error_path():
    calls = []
    namespace = build_namespace(calls)
    namespace["DEBUG"] = True

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy"

    namespace["Candy"] = candy

    def bridge(runtime, context):
        calls.append(("bridge", context.chunk_name))
        return "bridge-result"

    result = smash_bruteforce.run_legacy_smash_brute_brawl_from_namespace(
        namespace,
        "broken.png",
        b"IDAT",
        4,
        16,
        "Relics",
        bridge=bridge,
    )

    assert result == "bridge-result"
    assert ("betterror", "'bytes' object has no attribute 'encode'", "SmashBruteBrawl") in calls
    assert ("bridge", b"IDAT") in calls
    assert any(call[0] == "emit" and "<red:Error:" in call[1] for call in calls)


def test_legacy_bridge_builds_scan_context_syncs_state_and_runs_result():
    calls = []
    context = base_context()
    runtime = build_runtime(calls, scan_result=scan_result())

    result = smash_bruteforce.run_legacy_smash_brute_brawl(runtime, context)

    assert result == "legacy-result"
    assert find_call(calls, "register_image_viewers") == (
        "register_image_viewers",
        "ImageShow",
    )

    _name, scan_runtime, scan_context = find_call(calls, "run_scan")
    assert scan_runtime.load_spec("request") == "spec"
    assert scan_runtime.side_notes is runtime.side_notes
    assert scan_context == bruteforce_runtime.SmashBruteBrawlContext(
        file="broken.png",
        chunk_name=b"IDAT",
        chunk_length=4,
        data_offset=16,
        from_error="Relics",
        data_hex="89504e47",
        pandora_box={"key": "value"},
        edit_mode="Replace",
        bf_mode="TwoBytes",
        brute_crc=True,
        brute_length=False,
        old_crc=False,
        brute_level=2,
        crash=12,
        debug=True,
        pause_debug=False,
    )

    assert find_call(calls, "sync_state") == ("sync_state", False, 42, "new-diff")

    _name, result_runtime, result_context = find_call(calls, "run_result")
    assert result_runtime.side_notes is runtime.side_notes
    assert result_context == smash_bruteforce.bruteforce_result.BruteForceResultContext(
        state=bruteforce.BruteForceMatchState(bingo=True, replace_flag=True),
        old_crc=False,
        file="broken.png",
        chunk_name=b"IDAT",
        full_new_data_hex="66756c6c",
        png_bytes_hex="706e67",
        data_offset=16,
        chunk_length=4,
        to_brute="0011",
        edit_mode="Replace",
        bf_mode="TwoBytes",
        brute_crc=True,
        brute_length=False,
        from_error="Relics",
        diff="new-diff",
        tmp_image_paths=(),
    )


def test_legacy_bridge_wires_viewer_runtime_and_preserves_existing_diff_fallback():
    calls = []
    context = base_context(tmp_image_paths=["/tmp/saved.png"])

    def run_scan(scan_runtime, scan_context):
        viewer_result = scan_runtime.show_candidate(
            b"png",
            b"candidate",
            9,
            b"debug",
        )
        calls.append(("viewer_result", viewer_result))
        return scan_result(diff="")

    runtime = build_runtime(calls, scan_result=scan_result())
    runtime = smash_bruteforce.SmashBruteBrawlLegacyRuntime(
        **{
            **runtime.__dict__,
            "run_scan": run_scan,
        }
    )

    smash_bruteforce.run_legacy_smash_brute_brawl(runtime, context)

    _name, viewer_runtime, png_bytes, candidate_bytes, loop_index, debug_bytes = find_call(
        calls,
        "show_candidate",
    )
    assert viewer_runtime.data_hex == "89504e47"
    assert viewer_runtime.data_offset == 16
    assert viewer_runtime.libpng_errors == ("libpng error",)
    assert viewer_runtime.tmp_image_paths is context.tmp_image_paths
    assert viewer_runtime.file_origin == "/tmp/broken.png"
    assert viewer_runtime.cv2 == "cv2"
    assert viewer_runtime.numpy == "numpy"
    assert viewer_runtime.image == "Image"
    assert viewer_runtime.psutil == "psutil"
    assert viewer_runtime.debug is True
    assert png_bytes == b"png"
    assert candidate_bytes == b"candidate"
    assert loop_index == 9
    assert debug_bytes == b"debug"

    assert find_call(calls, "sync_state") == ("sync_state", False, 42, None)
    _name, _runtime, result_context = find_call(calls, "run_result")
    assert result_context.diff == "old-diff"
    assert result_context.tmp_image_paths == ("/tmp/saved.png",)


def main():
    checks = [
        ("Namespace bridge", test_legacy_namespace_entry_builds_bridge_and_syncs_legacy_state),
        ("Namespace bytes chunk", test_legacy_namespace_entry_preserves_bytes_chunk_name_error_path),
        ("Bridge scan/result", test_legacy_bridge_builds_scan_context_syncs_state_and_runs_result),
        ("Bridge viewer/fallback", test_legacy_bridge_wires_viewer_runtime_and_preserves_existing_diff_fallback),
    ]

    print("Running smash bruteforce bridge tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"smash bruteforce bridge tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
