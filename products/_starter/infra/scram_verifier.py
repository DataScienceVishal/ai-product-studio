"""Print the SCRAM-SHA-256 verifier for a password, in the form Postgres stores (RFC 5802 and RFC 7677).

    python3 -I scram_verifier.py PG_APP_PASSWORD     # the NAME of an environment variable, never the password

db-setup.sql sends this verifier in ALTER ROLE ... PASSWORD instead of the password itself. Postgres stores a
verifier as given, so the plaintext never reaches the server, and a failed statement can't log it. The
password is read from the environment, so it never appears on a command line either.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import sys

ITERATIONS = 4096  # Postgres's default (scram_iterations)


def verifier(password: str, salt: bytes | None = None, iterations: int = ITERATIONS) -> str:
    if not password:
        raise ValueError("empty password")
    if not password.isascii() or not password.isprintable():
        # Postgres runs SASLprep on non-ASCII passwords; the derived ones are ASCII, so refuse anything else.
        raise ValueError("password must be printable ASCII")
    salt = salt or os.urandom(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    client_key = hmac.new(salted, b"Client Key", hashlib.sha256).digest()
    server_key = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    stored_key = hashlib.sha256(client_key).digest()
    b64 = lambda raw: base64.b64encode(raw).decode()  # noqa: E731
    return f"SCRAM-SHA-256${iterations}:{b64(salt)}${b64(stored_key)}:{b64(server_key)}"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: scram_verifier.py ENV_VAR_NAME", file=sys.stderr)
        return 2
    try:
        print(verifier(os.environ.get(sys.argv[1], "")))
    except ValueError as error:
        print(f"scram_verifier: {sys.argv[1]}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
