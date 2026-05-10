import os
import sys
import json

# Ensure server/src is on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_PATH = os.path.join(ROOT, "server", "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from services.analyze_repo import (
    build_file_tree,
    analyze_repository,
    file_type_stats,
    classify_folder_patterns,
    to_json,
)


def test_build_file_tree_nested_and_root():
    paths = [
        "main.py",
        "src/auth/login.py",
        "src/models/user.py",
        "tests/test_auth.py",
        "README.md",
    ]
    res = build_file_tree(paths)
    assert res["total_files"] == 5
    fs = res["folder_structure"]
    assert "src" in fs
    assert "auth" in fs["src"]
    assert fs["src"]["auth"] == ["login.py"]
    assert fs["root"]


def test_duplicates_and_windows_paths():
    paths = [
        "src\\auth\\login.py",
        "src/auth/login.py",
        "src//auth//logout.py",
        "main.py",
        "main.py",
    ]
    res = build_file_tree(paths)
    assert res["total_files"] == 3


def test_file_type_stats_and_no_extension():
    paths = [
        "a.py",
        "b.json",
        "README",
        ".gitignore",
        "dir/nested/file.txt",
        "dir/nested/file",
    ]
    stats = file_type_stats(paths)
    assert stats.get(".py") == 1
    assert stats.get(".json") == 1
    assert stats.get(".txt") == 1
    assert stats.get("no_extension") == 3


def test_classify_folder_patterns():
    paths = [
        "src/auth/login.py",
        "lib/src/utils/tool.js",
        "tests/test_one.py",
        "components/button/index.js",
    ]
    tree = build_file_tree(paths)["folder_structure"]
    patterns = classify_folder_patterns(tree)
    assert "src" in patterns["patterns_detected"]
    assert "tests" in patterns["patterns_detected"]


def test_analyze_repository_output():
    paths = ["main.py", "src/auth/login.py", "package.json"]
    summary = analyze_repository(paths)
    assert summary["total_files"] == 3
    assert "file_types" in summary
    assert "patterns" in summary


def test_to_json_roundtrip():
    data = {"a": 1, "b": [1, 2, 3]}
    s = to_json(data)
    parsed = json.loads(s)
    assert parsed == data
