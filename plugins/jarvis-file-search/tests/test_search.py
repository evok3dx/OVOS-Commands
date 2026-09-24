import tempfile
import signal
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

from jarvis_file_search.search import search_filenames
from jarvis_file_search.results import show_results, run_window


class SearchTests(unittest.TestCase):
    def test_matches_filename_but_not_document_content(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "Xara Proposal.docx").write_bytes(b"not a real docx")
            (root / "other.txt").write_text("Xara Proposal")
            found, truncated = search_filenames("xara proposal", [root])
            self.assertEqual([x.path.name for x in found], ["Xara Proposal.docx"])
            self.assertFalse(truncated)

    def test_documentation_query_requires_both_words(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "Alex notes.txt").write_text("")
            (root / "Alex documentation.pdf").write_bytes(b"")
            found, _ = search_filenames("Alex documentation", [root])
            self.assertEqual([item.path.name for item in found],
                             ["Alex documentation.pdf"])

    def test_skips_hidden_and_symlinked_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".secret Xara.txt").write_text("hidden")
            secret = root / ".private"
            secret.mkdir()
            (secret / "Xara hidden.txt").write_text("hidden")
            external = root / "outside"
            external.mkdir()
            (external / "Xara outside.txt").write_text("outside")
            (root / "linked").symlink_to(external, target_is_directory=True)
            (root / "Xara link.txt").symlink_to(external / "Xara outside.txt")
            found, _ = search_filenames("Xara", [root])
            self.assertEqual([x.path.name for x in found], ["Xara outside.txt"])

    def test_entry_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for index in range(4):
                (root / f"Xara {index}.txt").write_text("")
            found, truncated = search_filenames("Xara", [root], max_entries=2)
            self.assertEqual(len(found), 2)
            self.assertTrue(truncated)

    def test_result_window_opens_only_selected_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / "Hermes documentation.txt"
            file.write_text("private document contents")
            matches, _ = search_filenames("Hermes", [root])
            with patch.dict("jarvis_file_search.results.os.environ", {"DISPLAY": ":0"}), \
                 patch("jarvis_file_search.results.which", side_effect=lambda s: "/usr/bin/" + s), \
                 patch("jarvis_file_search.results.Path.home", return_value=root), \
                 patch("jarvis_file_search.results.subprocess.Popen") as launch:
                launch.return_value.pid = 12345
                self.assertTrue(show_results("Hermes", matches))
            args = launch.call_args.args[0]
            self.assertIn(str(file), args)
            self.assertNotIn("private document contents", args)
            self.assertNotIn("xdg-open", args)

            with patch.dict("jarvis_file_search.results.os.environ", {"DISPLAY": ":0"}), \
                 patch("jarvis_file_search.results.which", side_effect=lambda s: "/usr/bin/" + s), \
                 patch("jarvis_file_search.results.Path.home", return_value=root), \
                 patch("jarvis_file_search.results._is_our_window", return_value=True), \
                 patch("jarvis_file_search.results.os.killpg") as close_previous, \
                 patch("jarvis_file_search.results.subprocess.Popen") as launch:
                launch.return_value.pid = 23456
                self.assertTrue(show_results("Alex", matches))
                close_previous.assert_called_once_with(12345, signal.SIGTERM)

            with patch("jarvis_file_search.results.which", side_effect=lambda s: "/usr/bin/" + s), \
                 patch("jarvis_file_search.results.subprocess.run",
                       return_value=CompletedProcess([], 0, "1. Hermes documentation.txt\n")) as dialog, \
                 patch("jarvis_file_search.results.subprocess.Popen") as open_file:
                self.assertTrue(run_window("Hermes", [file]))
            self.assertIn("1. Hermes documentation.txt", dialog.call_args.args[0])
            self.assertEqual(open_file.call_args.args[0], ["/usr/bin/xdg-open", str(file)])

            with patch("jarvis_file_search.results.which", side_effect=lambda s: "/usr/bin/" + s), \
                 patch("jarvis_file_search.results.subprocess.run",
                       return_value=CompletedProcess([], 1, "")), \
                 patch("jarvis_file_search.results.subprocess.Popen") as open_file:
                self.assertFalse(run_window("Hermes", [file]))
                open_file.assert_not_called()

    def test_skips_compiled_python_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "Hermes.pyc").write_bytes(b"bytecode")
            cached = root / "__pycache__"
            cached.mkdir()
            (cached / "Hermes.py").write_text("source")
            matches, _ = search_filenames("Hermes", [root])
            self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
