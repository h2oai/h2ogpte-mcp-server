import os
import ssl
import sys
from typing import Iterable, List, Mapping, Optional, Tuple

import certifi

# Env vars that name an extra CA bundle, in the order they are consulted after
# the explicit H2OGPTE_CA_BUNDLE setting. SSL_CERT_FILE/SSL_CERT_DIR are what
# httpx itself reads; REQUESTS_CA_BUNDLE is the requests-flavored spelling that
# enterprise images commonly set alongside it.
CA_BUNDLE_ENV_VARS = ("SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE")


def _candidates(
    ca_bundle: Optional[str], env: Mapping[str, str]
) -> List[Tuple[str, str]]:
    """Return (source, path) pairs to add, in order, without duplicates."""
    found: List[Tuple[str, str]] = []
    seen = set()
    for source, value in [("H2OGPTE_CA_BUNDLE", ca_bundle)] + [
        (name, env.get(name)) for name in CA_BUNDLE_ENV_VARS
    ]:
        path = (value or "").strip()
        if not path or path in seen:
            continue
        seen.add(path)
        found.append((source, path))
    return found


def build_ssl_context(
    ca_bundle: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    extra_paths: Optional[Iterable[str]] = None,
) -> ssl.SSLContext:
    """Build the TLS context used to reach the h2oGPTe server.

    An h2oGPTe deployment behind a private (internal) CA serves a certificate
    that certifi's public roots do not chain to, so the default httpx context
    rejects it and the server dies at startup with CERTIFICATE_VERIFY_FAILED.

    This context starts from certifi and *adds* every configured CA bundle to
    it, rather than letting httpx's SSL_CERT_FILE handling replace the trust
    store wholesale. Two consequences matter in practice:

    * a bundle holding only the internal CA still leaves public certificates
      verifiable, so a deployment on a public certificate keeps working after
      an administrator configures an internal bundle for other services;
    * a path that does not exist, or is not a readable PEM bundle, is reported
      and skipped instead of aborting the process. Under httpx's own handling
      that path is passed straight to ``ssl.create_default_context(cafile=...)``
      and a stale value takes the whole server down.

    Warnings go to stderr: this is a stdio MCP server, and stdout carries the
    protocol.
    """
    env = os.environ if env is None else env
    context = ssl.create_default_context(cafile=certifi.where())

    candidates = _candidates(ca_bundle, env)
    candidates += [("extra", p) for p in (extra_paths or []) if p]

    for source, path in candidates:
        is_dir = os.path.isdir(path)
        if not is_dir and not os.path.isfile(path):
            print(
                f"Warning: CA bundle from {source} not found, ignoring: {path}",
                file=sys.stderr,
            )
            continue
        try:
            if is_dir:
                context.load_verify_locations(capath=path)
            else:
                context.load_verify_locations(cafile=path)
        except (ssl.SSLError, OSError) as e:
            print(
                f"Warning: could not load CA bundle from {source} ({path}): {e}",
                file=sys.stderr,
            )
            continue
        print(f"Trusting additional CA bundle from {source}: {path}", file=sys.stderr)

    return context
