"""Retrieval-augmented Q&A over the briefing corpus.

The daily pipeline already accumulates one analysed briefing per weekday in
Postgres. This package turns that corpus into something queryable: each
briefing is chunked and embedded as it is stored, and the /ask endpoint
embeds a question, retrieves the most relevant past chunks, and answers with
inline date citations. It slots in alongside ingestion -> features ->
analysis -> api without changing any of them.
"""
