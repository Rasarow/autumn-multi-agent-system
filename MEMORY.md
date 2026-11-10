# Memory contract
Working memory is the bounded LangGraph state for one request. It is discarded after completion.
Session memory contains the last three approved question and result pairs, loaded by exact session key.
Persistent semantic memory is a dated, source-hashed section store with FTS5 lexical retrieval.
Episodic memory stores outcomes with session scope, status, and timestamp. Rejected answers are never recalled.
Procedural memory consists of the prompts, skill files, and role contracts under version control.
Reingestion replaces the source index atomically. A valid_to date is exclusive.
The forget command deletes a session's episodes. Production deployments require authenticated user-to-session binding,
retention enforcement, database encryption, and filesystem access controls. The prototype is single-user.
