# Tool contracts
search_documents(query, as_of, limit) searches only the SQLite source index, filters validity dates,
escapes FTS query terms, and returns at most four section records with identifiers and hashes.
read_section(identifier, as_of) retrieves one source record. Identifiers match [A-Z0-9_-]{1,48}.
It accepts no paths or URLs and rejects unknown and expired records.
ingest accepts only administrator-supplied local Markdown fixtures, rejects symlinks and files above 100 KB.
No shell, browser, arbitrary HTTP, email, or document mutation tool is available to an agent.
