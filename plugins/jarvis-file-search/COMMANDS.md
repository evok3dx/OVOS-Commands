# File Search voice command list

These are the native OVOS intent templates included in version 0.2.0.
Replace `{query}` with filename words you want to find. Matching is
case-insensitive. A phrase like “Alex documentation” requires both words in
one filename. The optional Qwen route may understand other wording when it
responds within its time limit; it has no fixed list of extra phrases.

The tray Commands tab belongs to the separate Jarvis dispatcher/GUI. This
skill does not add buttons or entries to that tab. Its native voice phrases
work without the tray, and installing the Qwen action does not populate it.
## Search filenames in configured folders

- `find file {query}`
- `find {query}`
- `find the {query}`
- `find the file {query}`
- `find document {query}`
- `find the document {query}`
- `search files for {query}`
- `search for file {query}`
- `search for the file {query}`
- `search my files for {query}`
- `can you search my files for {query}`
- `could you search my files for {query}`
- `please search my files for {query}`
- `look for file {query}`
- `look for the file {query}`
- `look for the file called {query}`
- `look for this file called {query}`
- `look for {query} file`
- `find my file {query}`

## Search filenames requiring the word document

- `find {query} document`
- `find the {query} document`
- `search for {query} document`
- `search for the {query} document`
- `look for {query} document`
- `look for the {query} document`

## Search filenames requiring the word documentation

- `find {query} documentation`
- `find the {query} documentation`
- `search for {query} documentation`
- `search for the {query} documentation`
- `look for {query} documentation`
- `look for the {query} documentation`

## Search ~/Documents only

- `look in my documents for {query}`
- `looking in my documents for {query}`
- `looking my documents for {query}`
- `look inside my documents for {query}`
- `looking through my documents for {query}`
- `look in documents for {query}`
- `look through my documents for {query}`
- `search my documents for {query}`
- `can you search my documents for {query}`
- `search documents for {query}`

## Ask for the filename, then search

- `look for this file`
- `look for a file`
- `find a file`
- `search my files`
