"""Credit Scoring System (CSS) — application credit scoring domain package.

See ``specs/013-css-chapter5-mart-and-scoring/spec.md`` for the chapter 5
feature spec. Glossary: ``credit/CONTEXT.md``.
"""

from credit.application_mart import ApplicationMartResult, build_application_mart

__version__ = "0.1.0"

__all__ = [
    "ApplicationMartResult",
    "__version__",
    "build_application_mart",
]
