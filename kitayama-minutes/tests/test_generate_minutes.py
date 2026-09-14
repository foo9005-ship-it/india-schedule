#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_minutes.py の MERGE_RUNS 解決ロジック、および同梱した vendor/merge_runs.py の
健全性を確認するテスト。実際のdocx生成のエンドツーエンド確認は手動で実施済み
（README参照）。

実行:
    cd kitayama-minutes
    python3 -m unittest tests.test_generate_minutes -v
"""

import subprocess
import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).parent.parent / "src"
SKILL_MERGE_RUNS = Path("/mnt/skills/public/docx/scripts/merge_runs.py")


class TestVendoredMergeRuns(unittest.TestCase):
    def test_vendor_merge_runs_exists(self):
        self.assertTrue((SRC_DIR / "vendor" / "merge_runs.py").exists())

    def test_vendor_office_helpers_exists(self):
        self.assertTrue((SRC_DIR / "vendor" / "office" / "helpers" / "__init__.py").exists())

    def test_vendor_merge_runs_compiles(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(SRC_DIR / "vendor" / "merge_runs.py")],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())


class TestMergeRunsPathResolution(unittest.TestCase):
    def test_merge_runs_resolves_to_an_existing_file(self):
        sys.path.insert(0, str(SRC_DIR))
        import generate_minutes as gm

        self.assertTrue(Path(gm.MERGE_RUNS).exists())

    def test_falls_back_to_vendor_when_skill_path_missing(self):
        # Lambda等、docxスキルが存在しない環境をシミュレートするテスト。
        # このClaude Code環境ではスキル側が優先されるため、スキル側が存在しない
        # 場合にのみvendor版へのフォールバックを検証する。
        if SKILL_MERGE_RUNS.exists():
            self.skipTest("このテスト環境ではdocxスキルが利用可能なため対象外")
        sys.path.insert(0, str(SRC_DIR))
        import generate_minutes as gm

        self.assertEqual(Path(gm.MERGE_RUNS).resolve(), (SRC_DIR / "vendor" / "merge_runs.py").resolve())


if __name__ == "__main__":
    unittest.main()
