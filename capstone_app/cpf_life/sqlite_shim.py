"""Swap in pysqlite3 (a modern SQLite build) in place of the stdlib sqlite3
module, if available.

Chroma requires SQLite >= 3.35. Streamlit Community Cloud's Linux base image
ships an older system SQLite that the stdlib sqlite3 module links against,
which makes `import chromadb` fail there with a RuntimeError. The standard
fix is to install `pysqlite3-binary` (a self-contained modern SQLite build)
and alias it over `sqlite3` in sys.modules before anything imports chromadb.

No macOS wheels exist for pysqlite3-binary, so this is a no-op on your local
Mac (whose system SQLite is already new enough) and only does anything on
Streamlit Cloud's Linux environment, where requirements.txt installs it via
a `sys_platform == "linux"` marker.

Import this module first, before any `import chromadb` or `from
langchain_chroma import Chroma` — e.g. at the very top of any page/script
that touches the vector store.
"""
import sys

try:
    __import__("pysqlite3")
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass
