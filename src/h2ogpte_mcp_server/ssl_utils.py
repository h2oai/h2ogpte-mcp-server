import os
import ssl
import sys
from typing import Iterable, List, Mapping, Optional, Tuple

import certifi

# Env vars httpx reads itself. They *replace* the trust store: httpx builds its
# context with ssl.create_default_context(cafile=...) or (capath=...), and that
# form of the call does not load the default roots, so an operator who points
# either variable at an internal CA has deliberately narrowed trust to it.
# SSL_CERT_FILE is consulted before SSL_CERT_DIR, the order httpx uses.
TRUST_STORE_ENV_VARS = ("SSL_CERT_FILE", "SSL_CERT_DIR")

# The requests-flavored spelling, which enterprise images commonly set alongside
# the two above. httpx never reads it, so adding it to the trust store extends
# what would otherwise be trusted instead of inverting anyone's configuration.
ADDITIONAL_CA_BUNDLE_ENV_VARS = ("REQUESTS_CA_BUNDLE",)


def _warn(message: str) -> None:
    # Warnings go to stderr: this is a stdio MCP server, stdout carries the
    # protocol.
    print(f"Warning: {message}", file=sys.stderr)


def _clean(value: Optional[str]) -> str:
    return (value or "").strip()


def _new_context(**kwargs) -> ssl.SSLContext:
    # TLS 1.2 is already the floor on supported runtimes; pin it so a future
    # default cannot quietly lower it (#12739).
    context = ssl.create_default_context(**kwargs)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def _seed_context(env: Mapping[str, str]) -> Tuple[ssl.SSLContext, Optional[str]]:
    """Create the base context, preserving httpx's SSL_CERT_* replace semantics.

    Returns the context and the path it was seeded from, if any. A bundle named
    by SSL_CERT_FILE or SSL_CERT_DIR becomes the whole trust store, exactly as
    httpx would have it, so a deployment that pinned trust to an internal-only
    CA is not quietly handed every public root back. A value that does not
    resolve is reported and skipped rather than aborting the process, which is
    what httpx does with a stale path.
    """
    for name in TRUST_STORE_ENV_VARS:
        path = _clean(env.get(name))
        if not path:
            continue
        is_dir = os.path.isdir(path)
        if not is_dir and not os.path.isfile(path):
            _warn(f"CA bundle from {name} not found, ignoring: {path}")
            continue
        try:
            if is_dir:
                context = _new_context(capath=path)
            else:
                context = _new_context(cafile=path)
        except (ssl.SSLError, OSError) as e:
            _warn(f"could not load CA bundle from {name} ({path}): {e}")
            continue
        print(
            f"Trusting only the CA bundle from {name}, which replaces the "
            f"default roots: {path}",
            file=sys.stderr,
        )
        return context, path
    return _new_context(cafile=certifi.where()), None


def build_ssl_context(
    ca_bundle: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    extra_paths: Optional[Iterable[str]] = None,
) -> ssl.SSLContext:
    """Build the TLS context used to reach the h2oGPTe server.

    An h2oGPTe deployment behind a private (internal) CA serves a certificate
    that certifi's public roots do not chain to, so the default httpx context
    rejects it and the server dies at startup with CERTIFICATE_VERIFY_FAILED.

    The context starts from whichever trust store applies (SSL_CERT_FILE or
    SSL_CERT_DIR when set, certifi otherwise, see ``_seed_context``) and *adds*
    H2OGPTE_CA_BUNDLE and REQUESTS_CA_BUNDLE on top of it, so a bundle holding
    only the internal CA still leaves public certificates verifiable.

    H2OGPTE_CA_BUNDLE is an explicit choice, so a path that does not exist, or
    is not a readable PEM bundle, raises: falling back to certifi would start
    the server in precisely the state the setting was added to fix, and every
    later request would fail with an opaque CERTIFICATE_VERIFY_FAILED. An
    inherited environment variable is reported and skipped instead, because a
    stale value in a shared image should not take a working server down.
    """
    env = os.environ if env is None else env
    context, seed_path = _seed_context(env)

    # (source, path, required). Only the explicit setting is required: the rest
    # are inherited from the environment or passed by callers as a convenience.
    additions: List[Tuple[str, str, bool]] = [
        ("H2OGPTE_CA_BUNDLE", _clean(ca_bundle), True)
    ]
    additions += [
        (name, _clean(env.get(name)), False) for name in ADDITIONAL_CA_BUNDLE_ENV_VARS
    ]
    additions += [("extra_paths", _clean(p), False) for p in (extra_paths or [])]

    seen = {seed_path} if seed_path else set()
    for source, path, required in additions:
        if not path or path in seen:
            continue
        seen.add(path)

        is_dir = os.path.isdir(path)
        if not is_dir and not os.path.isfile(path):
            if required:
                raise ValueError(
                    f"CA bundle from {source} not found: {path}. Correct the "
                    f"path or unset {source}."
                )
            _warn(f"CA bundle from {source} not found, ignoring: {path}")
            continue
        try:
            if is_dir:
                context.load_verify_locations(capath=path)
            else:
                context.load_verify_locations(cafile=path)
        except (ssl.SSLError, OSError) as e:
            if required:
                raise ValueError(
                    f"CA bundle from {source} could not be loaded ({path}): "
                    f"{e}. It must be a PEM bundle or a hashed CA directory."
                ) from e
            _warn(f"could not load CA bundle from {source} ({path}): {e}")
            continue
        print(f"Trusting additional CA bundle from {source}: {path}", file=sys.stderr)

    return context
