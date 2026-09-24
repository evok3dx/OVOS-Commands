"""OVOS voice interface for filename search."""

from pathlib import Path

from ovos_workshop.decorators import intent_handler
from ovos_workshop.skills.ovos import OVOSSkill

from .search import search_filenames
from .results import show_results


DEFAULT_FOLDERS = ["~/Documents", "~/Downloads", "~/Desktop"]


class JarvisFileSearchSkill(OVOSSkill):
    def initialize(self):
        self.add_event("jarvis.file.search", self.handle_routed_search)

    def handle_routed_search(self, message):
        query = message.data.get("query")
        if isinstance(query, str) and 0 < len(query.strip()) <= 200:
            self._search(query, documents_only=message.data.get("documents_only") is True)

    @intent_handler("search.file.intent")
    def handle_search(self, message):
        self._search(message.data.get("query"))

    @intent_handler("search.documentation.intent")
    def handle_documentation_search(self, message):
        self._search(str(message.data.get("query") or "").strip() + " documentation")

    @intent_handler("search.document.intent")
    def handle_document_search(self, message):
        self._search(str(message.data.get("query") or "").strip() + " document")

    @intent_handler("search.documents.intent")
    def handle_documents_search(self, message):
        self._search(message.data.get("query"), documents_only=True)

    @intent_handler("search.file.prompt.intent")
    def handle_search_prompt(self, message):
        query = self.get_response("which.filename", num_retries=0)
        if query:
            self._search(query)

    def _search(self, requested_query, documents_only=False):
        query = str(requested_query or "").strip()
        if not query:
            self.speak("Tell me a filename to search for.")
            return

        folders = (["~/Documents"] if documents_only else
                   self.settings.get("folders", DEFAULT_FOLDERS))
        if not isinstance(folders, list):
            self.speak("File search folders need to be configured as a list.")
            return
        configured = [Path(folder).expanduser() for folder in folders
                      if isinstance(folder, str) and folder.strip()]
        if not configured:
            self.speak("No file search folders are configured.")
            return

        self.speak("Searching.")
        matches, truncated = search_filenames(
            query, configured, limit=self.settings.get("max_results", 20),
            max_entries=self.settings.get("max_entries", 50000),
            timeout=self.settings.get("timeout_seconds", 8.0))
        shown = show_results(query, matches, truncated)
        self.log.info("File search found %d matches; window opened=%s; partial=%s",
                      len(matches), shown, truncated)
        if not shown:
            self.speak("I couldn't show the results.")
