import ssl
import subprocess

import certifi
import pytest

from h2ogpte_mcp_server.ssl_utils import build_ssl_context


def _make_ca(tmp_path, name):
    """Write a self-signed CA certificate and return its path."""
    key = tmp_path / f"{name}.key"
    cert = tmp_path / f"{name}.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            f"/CN={name}",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    return cert


def _ca_count(context):
    return len(context.get_ca_certs())


def test_missing_path_is_skipped_not_fatal(tmp_path, capsys):
    # Regression: httpx hands SSL_CERT_FILE straight to
    # ssl.create_default_context(cafile=...), so a stale path raises
    # FileNotFoundError and the whole MCP server fails to start.
    context = build_ssl_context(str(tmp_path / "nope.pem"), env={})

    assert isinstance(context, ssl.SSLContext)
    assert _ca_count(context) == _ca_count(
        ssl.create_default_context(cafile=certifi.where())
    )
    assert "not found" in capsys.readouterr().err


def test_unreadable_bundle_is_skipped_not_fatal(tmp_path, capsys):
    junk = tmp_path / "junk.pem"
    junk.write_text("this is not a certificate\n")

    context = build_ssl_context(str(junk), env={})

    assert isinstance(context, ssl.SSLContext)
    assert "could not load" in capsys.readouterr().err


def test_private_ca_is_added_on_top_of_certifi(tmp_path):
    ca = _make_ca(tmp_path, "internal-ca")
    baseline = _ca_count(ssl.create_default_context(cafile=certifi.where()))

    context = build_ssl_context(str(ca), env={})

    # Additive, not a replacement: the public roots stay trusted, so a bundle
    # holding only the internal CA cannot silently break public TLS.
    assert _ca_count(context) == baseline + 1
    subjects = [dict(x[0] for x in c["subject"]) for c in context.get_ca_certs()]
    assert {"commonName": "internal-ca"} in subjects


@pytest.mark.parametrize(
    "env_var", ["SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE"]
)
def test_bundle_is_picked_up_from_the_environment(tmp_path, env_var):
    ca = _make_ca(tmp_path, "env-ca")
    baseline = _ca_count(ssl.create_default_context(cafile=certifi.where()))

    # SSL_CERT_DIR names a hashed directory rather than a file; the container
    # mount in the field is a file, so only the file spellings get a real
    # bundle here and the dir spelling is exercised as a bad-value skip.
    value = str(ca) if env_var != "SSL_CERT_DIR" else str(tmp_path / "missing-dir")
    context = build_ssl_context(None, env={env_var: value})

    expected = baseline + (1 if env_var != "SSL_CERT_DIR" else 0)
    assert _ca_count(context) == expected


def test_setting_and_env_naming_the_same_file_loads_it_once(tmp_path):
    ca = _make_ca(tmp_path, "dup-ca")
    baseline = _ca_count(ssl.create_default_context(cafile=certifi.where()))

    context = build_ssl_context(str(ca), env={"SSL_CERT_FILE": str(ca)})

    # The platform sets SSL_CERT_FILE and an admin may set H2OGPTE_CA_BUNDLE to
    # the same path; loading it twice is harmless but the dedup keeps the
    # startup log honest.
    assert _ca_count(context) == baseline + 1


def test_no_bundle_configured_is_plain_certifi(tmp_path):
    context = build_ssl_context(None, env={})

    assert _ca_count(context) == _ca_count(
        ssl.create_default_context(cafile=certifi.where())
    )
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
