"""Central vocabulary and action mappings for Jarvis commands."""

BROWSER_NAVIGATION_ACTIONS = {
    "scroll down": "scroll_down",
    "school down": "scroll_down",
    "roll down": "scroll_down",
    "scroll the page down": "scroll_down",
    "crawl down": "scroll_down",
    "move down": "scroll_down",
    "go down": "scroll_down",
    "scroll lower": "scroll_down",
    "scroll down a little": "scroll_down",
    "scroll up": "scroll_up",
    "school up": "scroll_up",
    "roll up": "scroll_up",
    "scroll the page up": "scroll_up",
    "crawl up": "scroll_up",
    "move up": "scroll_up",
    "go up": "scroll_up",
    "scroll higher": "scroll_up",
    "scroll up a little": "scroll_up",
    "page down": "page_down",
    "page town": "page_down",
    "next screen": "page_down",
    "one page down": "page_down",
    "pagedown": "page_down",
    "next page": "page_down",
    "page up": "page_up",
    "previous screen": "page_up",
    "one page up": "page_up",
    "pageup": "page_up",
    "previous page": "page_up",
    "go to the top": "top",
    "go to the top of the page": "top",
    "go top of the page": "top",
    "go to top of the page": "top",
    "go to top of page": "top",
    "go top of page": "top",
    "up on the page": "top",
    "move to the top": "top",
    "scroll to the top": "top",
    "top of the page": "top",
    "top of page": "top",
    "go to the bottom": "bottom",
    "go to the bottom of the page": "bottom",
    "go bottom of the page": "bottom",
    "go to bottom of the page": "bottom",
    "go to bottom of page": "bottom",
    "go bottom of page": "bottom",
    "down on the page": "bottom",
    "move to the bottom": "bottom",
    "scroll to the bottom": "bottom",
    "scroll to the bottom of the page": "bottom",
    "bottom of the page": "bottom",
    "bottom of page": "bottom",
    "go back": "back",
    "back a page": "back",
    "previous page in brave": "back",
    "go forward": "forward",
    "forward a page": "forward",
    "open a new tab": "new_tab",
    "welcome to the new tab": "new_tab",
    "new tab": "new_tab",
    "close this tab": "close_tab",
    "close the tab": "close_tab",
    "close tab": "close_tab",
    "close up": "close_tab",
    "refresh the page": "refresh",
    "refresh page": "refresh",
    "reload the page": "refresh",
    "focus address bar": "address",
    "focus the address bar": "address",
    "go to the address bar": "address",
    "go to address bar": "address",
    "focus on the address bar": "address",
}

BRAVE_SEARCH_PROMPTS = (
    "search brave",
    "such brave",
    "it's brave",
    "its brave",
    "search break",
    "such break",
    "search in brave",
    "search with brave",
    "brave search",
)

FIREFOX_SEARCH_PROMPTS = (
    "search firefox",
    "search fire fox",
    "search in firefox",
    "search with firefox",
    "firefox search",
    "fire fox search",
    "stage five fox",
    "stage 5 fox",
    "stage five folks",
    "stage 5 folks",
)

YOUTUBE_SEARCH_PROMPTS = (
    "search youtube",
    "search you tube",
    "search on youtube",
    "search in youtube",
    "youtube search",
    "you tube search",
)

YOUTUBE_SHORTS_PROMPTS = (
    "go to youtube shorts",
    "open youtube shorts",
    "youtube shorts",
    "show youtube shorts",
    "go to youtube reels",
    "open youtube reels",
    "youtube reels",
    "show youtube reels",
)

HERMES_COMPOSER_ACTIONS = {
    "focus hermes composer": "focus_composer",
    "go to hermes composer": "focus_composer",
    "focus the hermes composer": "focus_composer",
    "focus composer in hermes": "focus_composer",
    "open hermes model picker": "model_picker",
    "show hermes model picker": "model_picker",
    "choose hermes model": "model_picker",
    "change hermes model": "model_picker",
    "new line in hermes": "insert_newline",
    "insert new line in hermes": "insert_newline",
    "insert newline in hermes": "insert_newline",
    "add a new line in hermes": "insert_newline",
    "queue hermes message": "queue_message",
    "queue message in hermes": "queue_message",
    "add hermes message to queue": "queue_message",
    "send next hermes message": "send_queued",
    "send next queued hermes turn": "send_queued",
    "send hermes queue": "send_queued",
    "open hermes commands": "command_palette",
    "show hermes commands": "command_palette",
    "open hermes slash commands": "command_palette",
    "show hermes command palette": "command_palette",
    "reference file in hermes": "reference",
    "reference files in hermes": "reference",
    "attach file in hermes": "reference",
    "add file to hermes": "reference",
    "cancel hermes run": "cancel",
    "stop hermes run": "cancel",
    "close hermes popup": "cancel",
}

def register_skill_vocabulary(self, include_custom=True):
    """Register all dispatcher vocabulary without changing intent behaviour."""
    agents_enabled = bool(
        getattr(self, "_jarvis_profile", {})
        .get("private_extensions", {})
        .get("agents", False)
    )
    aliases = {
        "CodexKeyword": [
            "cortex agent",
            "clerics agent",
            "codex-agent",
            "kurdex agent",
            "colex agent",
            "codecs agent",
            "clod agent",
        ],
        "ClaudeKeyword": [
            "claude",
            "cloud",
            "clawed",
            "called",
            "clawed agent"
        ],
        "HermesKeyword": [
            "hermes",
            "hermas",
            "omos",
            "hermes desktop",
            "hermes app",
        ],
        "OpenCodexCommand": [
            "opencodex agent",
            "opencodecs agent",
            "open colex agent",
            "open code as agent"
        ],
        "FocusCodexCommand": [
            "focus code as agent",
            "focus codecs agent"
        ],
        "OpenKeyword": [
            "open up",
            "pull up",
            "bring up",
            "launch",
            "show",
            "show me"
        ],
        "FocusKeyword": [
            "focus on",
            "switch to",
            "go to",
            "bring forward",
            "return to"
        ],
        "MinimizeKeyword": [
            "minimise",
            "hide",
            "put away",
            "move aside"
        ],
        "CloseKeyword": [
            "dismiss",
            "close window",
            "dismiss window"
        ],
        "MessageKeyword": [
            "message",
            "ask",
            "tell",
            "talk to",
            "write to",
            "write this to",
            "write the following to",
            "type into",
            "type this into",
            "type the following into",
            "speak to",
            "speak with",
            "welcome to",
            "send to",
            "send this to",
            "send that to",
            "give a task to"
        ],
        "WriteKeyword": ["write"],
        "TypeKeyword": ["type"],
        "SpeakKeyword": ["speak"],
        "TalkKeyword": ["talk"],
    }

    if not agents_enabled:
        for entity in ("CodexKeyword", "OpenCodexCommand", "FocusCodexCommand"):
            aliases.pop(entity, None)
        aliases["ClaudeKeyword"] = ["claude", "cloud", "clawed", "called"]

    for entity, phrases in aliases.items():
        for phrase in phrases:
            self.register_vocabulary(phrase, entity)

    for phrase in ("mute mic", "mute microphone"):
        self.register_vocabulary(
            phrase,
            "MuteSystemMicrophoneCommand"
        )

    for phrase in (
        "mute system",
        "mute the system",
        "mute everything",
        "mute all system audio",
    ):
        self.register_vocabulary(
            phrase,
            "MuteSystemAudioCommand"
        )

    for phrase in ("mute jarvis", "stop jarvis listening"):
        self.register_vocabulary(
            phrase,
            "MuteJarvisCommand"
        )

    system_controls = {
        "PressEnterCommand": [
            "press enter", "press return", "press send",
            "hit enter", "hit return", "enter", "send it", "submit it",
        ],
        "InsertNewLineCommand": [
            "new line", "newline", "insert new line", "add a new line",
        ],
        "PressEscapeCommand": [
            "press escape", "press esc", "hit escape", "escape key",
        ],
        "PlayMediaCommand": [
            "play media", "play the media", "resume playback", "unpause playback",
            "resume media", "play music", "play the music", "resume music",
            "resume the music", "resume song", "resume the song", "resume track",
            "resume the track", "continue music", "continue the music",
            "continue song", "continue the song", "continue track",
            "continue the track", "carry on with the music", "carry on playing",
            "start the music again", "unpause music", "unpause the music",
        ],
        "PauseMediaCommand": [
            "pause media", "pause the media", "pause playback", "pause music",
            "pause the music", "pause song", "pause the song", "pause track",
            "pause the track", "pause video", "pause the video", "pause this",
            "pause this song", "pause this track", "pause this video",
            "hold the music", "hold this song", "hold this track",
            "pause what is playing", "pose music", "pose the music",
            "hose music", "hose the music",
        ],
        "StopMediaCommand": [
            "stop media", "stop the media", "stop playback", "stop music",
            "stop the music", "stop playing", "stop song", "stop the song",
            "stop track", "stop the track", "stop video", "stop the video",
            "stop this song", "stop this track", "stop this video",
            "stop what is playing", "turn off the music",
        ],
        "NextMediaCommand": [
            "next track", "next song", "next video", "skip track",
            "skip this track", "skip song", "skip this song", "skip this video",
            "skip the song", "skip the track", "skip the video",
            "play next track", "play next song", "play the next track",
            "play the next song", "go to next track", "go to the next track",
            "go to next song", "go to the next song", "move to the next track",
            "move to the next song",
        ],
        "PreviousMediaCommand": [
            "previous track", "previous song", "previous video", "back track",
            "back a track", "back one track", "back one song", "go back a track",
            "go back one track", "go back one song", "go back one video",
            "go back to previous track", "go back to the previous track",
            "go back to previous song", "go back to the previous song",
            "play previous track", "play previous song", "play the previous track",
            "play the previous song", "skip back a track", "skip back one track",
            "skip back one song",
        ],
        "CapsLockOnCommand": [
            "caps lock on", "turn caps lock on",
            "enable caps lock", "switch caps lock on",
        ],
        "CapsLockOffCommand": [
            "caps lock off", "turn caps lock off",
            "disable caps lock", "switch caps lock off",
        ],
    }
    for entity, phrases in system_controls.items():
        for phrase in phrases:
            self.register_vocabulary(phrase, entity)

    self._hermes_composer_actions = HERMES_COMPOSER_ACTIONS
    for phrase in self._hermes_composer_actions:
        self.register_vocabulary(phrase, "HermesComposerCommand")

    # Natural desktop application controls resolved by the active profile.
    profile = getattr(self, "_jarvis_profile", None)
    if profile is None:
        from .profile import load_profile
        profile = load_profile(logger=getattr(self, "log", None))
        self._jarvis_profile = profile

    applications = profile["applications"]
    self._desktop_app_aliases = {
        category: list(definition["aliases"])
        for category, definition in applications.items()
    }
    self._desktop_app_integrations = {
        category: definition["integration"]
        for category, definition in applications.items()
    }
    self._desktop_app_display_names = {
        category: definition["display_name"]
        for category, definition in applications.items()
    }

    desktop_actions = {
        "OpenDesktopAppCommand": [
            "open", "launch", "start"
        ],
        "FocusDesktopAppCommand": [
            "focus", "show", "go to",
            "bring up", "switch to"
        ],
        "MinimizeDesktopAppCommand": [
            "minimize", "minimise", "hide", "put away"
        ],
        "CloseDesktopAppCommand": [
            "close", "quit", "exit"
        ],
        "MaximizeDesktopAppCommand": [
            "maximize", "maximise", "make full screen", "make fullscreen"
        ],
    }

    for entity, verbs in desktop_actions.items():
        for app_aliases in self._desktop_app_aliases.values():
            for app_alias in app_aliases:
                for verb in verbs:
                    self.register_vocabulary(
                        f"{verb} {app_alias}",
                        entity
                    )

    # Practical misses from the v4 corpus: apply focus wording uniformly.
    for aliases in self._desktop_app_aliases.values():
        for alias in aliases:
            for phrase in (f"show me {alias}", f"show me the {alias} window"):
                self.register_vocabulary(phrase, "FocusDesktopAppCommand")

    website_commands = {
        "OpenChatGPTWebsiteCommand": (
            "open the chat website", "open chat website",
            "open the chatgpt website", "open chatgpt website",
            "open the gpt website", "open gpt website", "open chatgpt online",
            "open chat online",
        ),
        "OpenClaudeWebsiteCommand": (
            "open the claude website", "open claude website", "open claude online",
        ),
    }
    for entity, phrases in website_commands.items():
        for phrase in phrases:
            self.register_vocabulary(phrase, entity)


    # Visible browser controls.
    self._browser_navigation_actions = BROWSER_NAVIGATION_ACTIONS

    for phrase in self._browser_navigation_actions:
        self.register_vocabulary(
            phrase,
            "BrowserNavigationCommand"
        )


    for phrase in BRAVE_SEARCH_PROMPTS:
        self.register_vocabulary(
            phrase,
            "BraveSearchPromptCommand"
        )

    for phrase in FIREFOX_SEARCH_PROMPTS:
        self.register_vocabulary(
            phrase,
            "FirefoxSearchPromptCommand"
        )

    for phrase in YOUTUBE_SEARCH_PROMPTS:
        self.register_vocabulary(
            phrase,
            "YouTubeSearchPromptCommand"
        )

    for phrase in YOUTUBE_SHORTS_PROMPTS:
        self.register_vocabulary(
            phrase,
            "YouTubeShortsCommand"
        )

    write_text_commands = [
        "write this",
        "type this",
        "write the following",
        "type the following",
        "dictate this",
        "enter this"
    ]

    for phrase in write_text_commands:
        self.register_vocabulary(
            phrase,
            "WriteFocusedTextCommand"
        )

    response_commands = {
        "ReadCodexResponseCommand": [
            "read codex response",
            "read codex answer",
            "read codex reply"
        ],
        "ReadClaudeResponseCommand": [
            "read claude response",
            "read claude answer",
            "read claude reply",
            "read cloud response",
            "read cloud answer",
            "read cloud reply"
        ],
        "ReadLatestResponseCommand": [
            "read it",
            "read it to me",
            "read the response",
            "read the answer",
            "read the reply",
            "read my response",
            "read my answer",
            "read the latest response",
            "read the latest answer",
            "read the last response",
            "read the last answer"
        ]
    }

    if not agents_enabled:
        response_commands = {}

    for entity, phrases in response_commands.items():
        for phrase in phrases:
            self.register_vocabulary(phrase, entity)

    search_commands = [
        "search the web",
        "search codex",
        "web search",
        "research with codex"
    ]

    if not agents_enabled:
        search_commands = []

    for phrase in search_commands:
        self.register_vocabulary(
            phrase,
            "SearchCodexCommand"
        )

    claude_open_commands = [
        "open cloud agent",
        "openclord agent",
        "opencloord agent",
        "openclod agent",
        "openclaud agent",
        "open clawed agent"
    ]

    if not agents_enabled:
        claude_open_commands = []

    for phrase in claude_open_commands:
        self.register_vocabulary(
            phrase,
            "OpenClaudeCommand"
        )

    claude_names = ("claude", "cloud", "clawed", "called")
    claude_new_chat_templates = (
        "new {name} chat",
        "a new {name} chat",
        "open new {name} chat",
        "open a new {name} chat",
        "start new {name} chat",
        "start a new {name} chat",
        "create new {name} chat",
        "create a new {name} chat",
        "new chat with {name}",
        "start a new chat with {name}",
        "open a new chat with {name}",
    )
    for name in claude_names:
        for template in claude_new_chat_templates:
            self.register_vocabulary(
                template.format(name=name),
                "NewClaudeChatCommand",
            )

    claude_agent_command_templates = {
        "NewClaudeAgentCommand": (
            "new {name} agent",
            "start new {name} agent",
            "start a new {name} agent",
            "open new {name} agent",
        ),
        "CreateClaudeSubagentCommand": (
            "create {name} subagent",
            "create a {name} subagent",
            "make a {name} subagent",
            "new {name} subagent",
            "add a {name} subagent",
        ),
        "ShowClaudeAgentsCommand": (
            "show {name} agents",
            "open {name} agents",
            "list {name} agents",
            "manage {name} agents",
        ),
        "ResumeClaudeAgentCommand": (
            "resume {name} agent",
            "continue {name} agent",
            "return to {name} agent",
            "reopen {name} agent",
        ),
    }
    if agents_enabled:
        for entity, templates in claude_agent_command_templates.items():
            for name in claude_names:
                for template in templates:
                    self.register_vocabulary(template.format(name=name), entity)


    natural_date_commands = [
        "read out the date",
        "read the date",
        "read today's date",
        "what's today's date",
        "what is today's date",
        "tell me today's date"
    ]

    for phrase in natural_date_commands:
        self.register_vocabulary(
            phrase,
            "NaturalDateCommand"
        )

    focused_window_commands = {
        "CloseFocusedWindowCommand": [
            "close window",
            "close the window",
            "close this window",
            "close this up",
            "close current window",
            "close app",
            "closed app",
            "close the app",
            "closed the app",
            "close this app",
            "closed this app",
            "close application",
            "close this application"
        ],
        "MinimizeFocusedWindowCommand": [
            "minimize window",
            "minimise window",
            "minimize this window",
            "minimise this window",
            "minimize app",
            "minimise app",
            "hide this window",
            "put this window away"
        ],
        "MaximizeFocusedWindowCommand": [
            "maximize window",
            "maximise window",
            "maximize this window",
            "maximise this window",
            "maximize app",
            "maximise app"
        ],
        "RestoreFocusedWindowCommand": [
            "restore window",
            "restore this window",
            "unmaximize window",
            "unmaximise window",
            "unmaximized window",
            "unmaximised window",
            "return window to normal"
        ]
    }

    for entity, phrases in focused_window_commands.items():
        for phrase in phrases:
            self.register_vocabulary(phrase, entity)
    dictation_commands = {
        "StartSpeechNoteDictationCommand": [
            "start dictation",
            "start writing",
            "begin dictation",
            "begin writing"
        ],
        "PauseSpeechNoteDictationCommand": [
            "pause dictation",
            "pause writing"
        ],
        "ResumeSpeechNoteDictationCommand": [
            "resume dictation",
            "resume writing",
            "continue dictation",
            "continue writing"
        ],
        "StopSpeechNoteDictationCommand": [
            "stop dictation",
            "stop writing",
            "finish dictation",
            "finish writing",
            "end dictation",
            "end writing"
        ]
    }

    for entity, phrases in dictation_commands.items():
        for phrase in phrases:
            self.register_vocabulary(phrase, entity)

    for phrase in (
        "new note",
        "new notes",
        "new node",
        "new nodes",
        "knee nodes",
        "create a new note",
        "create new note",
        "create a new node",
        "create new node",
        "make a new note",
        "make new note",
        "make a new node",
        "make new node",
    ):
        self.register_vocabulary(phrase, "NewNoteCommand")

    for phrase in (
        "read it back",
        "read it back to me",
        "read that back",
        "read what you wrote",
        "repeat what you wrote"
    ):
        self.register_vocabulary(
            phrase,
            "ReadLastTypedTextCommand"
        )
    visible_text_commands = {
        "ReadSelectedTextDoubleSpeedCommand": [
            "read this at double speed",
            "read this double speed",
            "read this at two times speed",
            "read this two times speed",
            "read this at two x",
            "read this two x",
            "read this at 2x",
            "read this 2x",
            "read this and double the speed",
            "read selected text at double speed",
            "read selected text at 2x",
            "read selected text at two times speed"
        ],
        "ReadVisiblePageDoubleSpeedCommand": [
            "read this page at double speed",
            "read this page double speed",
            "read this page at two times speed",
            "read this page two times speed",
            "read this page at two x",
            "read this page two x",
            "read this page at 2x",
            "read page at 2x",
            "read page at double speed",
            "read page at two times speed"
        ],
        "ReadSelectedTextCommand": [
            "read this",
            "read selected text",
            "read the selected text",
            "read this selection",
            "read the selection"
        ],
        "ReadVisiblePageCommand": [
            "read page",
            "read this page",
            "read the page",
            "read current page",
            "read the complete page",
            "please read the complete page",
            "read the whole page",
            "please read the whole page",
            "read this webpage",
            "read the webpage",
            "read window",
            "read this window",
            "read current window",
            "read app",
            "read this app",
            "read application",
            "read this application",
            "read screen",
            "read this screen",
            "read content",
            "read this content",
            "read full page",
            "read the full page",
            "read the entire page",
            "read everything on the page"
        ]
    }

    for entity, phrases in visible_text_commands.items():
        for phrase in phrases:
            self.register_vocabulary(phrase, entity)

    text_editing_commands = {
        "SelectAllTextCommand": [
            "select all", "select all text", "select the text", "select everything"
        ],
        "DeleteSelectedTextCommand": [
            "delete text", "delete the text",
            "delete selected text", "delete the selected text"
        ],
        "ClearFocusedTextCommand": [
            "clear text", "clear the text", "clear all text",
            "clear page", "clear the page", "clear this page"
        ],
        "UndoTextEditCommand": [
            "undo", "undo that", "undo the last change"
        ],
        "RedoTextEditCommand": [
            "redo", "redo that", "redo the last change"
        ],
        "CopySelectedTextCommand": [
            "copy", "copy text", "copy the text", "copy selected text"
        ],
        "CutSelectedTextCommand": [
            "cut", "cut text", "cut the text", "cut selected text"
        ],
        "PasteTextCommand": [
            "paste", "paste text", "paste the text", "paste here"
        ],
        "SaveDocumentCommand": [
            "save", "save this", "save document", "save the document"
        ],
        "SearchFocusedContentCommand": [
            "search page", "search this page", "search the page",
            "find on page", "find on this page", "search document",
            "search this document", "find in this document",
            "search this note", "find in this note",
            "search this node", "find in this node"
        ],
        "PressTabCommand": [
            "press tab", "tab", "next field", "next box",
            "go to next field", "go to the next field",
            "move to next field", "move to the next field"
        ],
        "PressShiftTabCommand": [
            "press shift tab", "shift tab", "previous field", "previous box",
            "go to previous field", "go to the previous field",
            "move to previous field", "move to the previous field"
        ]
    }

    for entity, phrases in text_editing_commands.items():
        for phrase in phrases:
            self.register_vocabulary(phrase, entity)

    for phrase in (
        "search notes", "search note", "search a note",
        "search my notes", "search my note",
        "search nodes", "search node", "search a node",
        "search my nodes", "search my node",
        "search standard notes", "search standard note",
        "search standard nodes", "search standard node",
        "find a note", "find note", "find a node", "find node",
        "look up a note", "look up notes", "look up my notes",
        "look up a node", "look up nodes", "look up my nodes",
        "look for a note", "look for notes",
        "look for a node", "look for nodes",
    ):
        self.register_vocabulary(phrase, "SearchNotesCommand")

    for phrase in (
        "new email", "create new email", "create an email",
        "compose email", "compose an email", "write a new email",
        "write an email",
    ):
        self.register_vocabulary(phrase, "NewEmailCommand")

    for phrase in (
        "search mail", "search my mail", "search email", "search my email",
        "find an email", "find email", "look up an email", "look through my mail",
    ):
        self.register_vocabulary(phrase, "SearchMailCommand")

    for phrase in (
        "join meeting", "join the meeting", "join zoom meeting",
        "join the zoom meeting", "join copied meeting",
        "join copied zoom meeting",
    ):
        self.register_vocabulary(phrase, "JoinZoomMeetingCommand")

    if include_custom:
        from .custom_commands import (
            collect_builtin_phrases,
            register_custom_vocabulary,
        )

        builtin_phrases = collect_builtin_phrases(self._jarvis_profile)
        register_custom_vocabulary(self, builtin_phrases)
