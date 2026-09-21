import contextlib
import socket
import ssl
import subprocess
import threading

import certifi
import pytest

from h2ogpte_mcp_server.ssl_utils import build_ssl_context


def _make_ca(tmp_path, name):
    """Write a self-signed CA certificate and return (cert, key) paths."""
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
    return cert, key


def _make_server_cert(tmp_path, ca_cert, ca_key, name="localhost"):
    """Issue a localhost server certificate from the given CA."""
    key = tmp_path / f"{name}-server.key"
    csr = tmp_path / f"{name}-server.csr"
    cert = tmp_path / f"{name}-server.pem"
    ext = tmp_path / f"{name}-server.ext"
    ext.write_text(
        "basicConstraints=CA:FALSE\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n"
    )
    subprocess.run(
        [
            "openssl",
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-subj",
            f"/CN={name}",
            "-keyout",
            str(key),
            "-out",
            str(csr),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            str(csr),
            "-CA",
            str(ca_cert),
            "-CAkey",
            str(ca_key),
            "-CAcreateserial",
            "-days",
            "1",
            "-extfile",
            str(ext),
            "-out",
            str(cert),
        ],
        check=True,
        capture_output=True,
    )
    return cert, key


def _hashed_ca_dir(tmp_path, ca_cert, name="cadir"):
    """Lay out a CA certificate the way OpenSSL expects a capath directory."""
    ca_dir = tmp_path / name
    ca_dir.mkdir()
    copied = ca_dir / ca_cert.name
    copied.write_bytes(ca_cert.read_bytes())
    digest = subprocess.run(
        ["openssl", "x509", "-hash", "-noout", "-in", str(copied)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (ca_dir / f"{digest}.0").symlink_to(copied.name)
    return ca_dir


@contextlib.contextmanager
def _tls_server(cert, key):
    """Serve TLS on a high port and yield that port."""
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certfile=str(cert), keyfile=str(key))

    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    for port in range(18443, 18500):
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            continue
        break
    else:
        listener.close()
        raise RuntimeError("no free port in 18443-18499 for the test TLS server")
    listener.listen(5)

    def serve():
        while True:
            try:
                connection, _ = listener.accept()
            except OSError:
                return
            connection.settimeout(5)
            try:
                with server_context.wrap_socket(connection, server_side=True) as tls:
                    tls.sendall(b"ok")
            except (ssl.SSLError, OSError):
                # A client that rejects our certificate is an expected outcome.
                pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        listener.close()
        thread.join(timeout=5)


def _handshake(context, port, hostname="localhost"):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=hostname) as tls:
            return tls.getpeercert()


def _ca_count(context):
    return len(context.get_ca_certs())


def _common_names(context):
    return [
        dict(x[0] for x in c["subject"]).get("commonName")
        for c in context.get_ca_certs()
    ]


def _certifi_count():
    return _ca_count(ssl.create_default_context(cafile=certifi.where()))


def test_no_bundle_configured_is_plain_certifi():
    context = build_ssl_context(None, env={})

    assert _ca_count(context) == _certifi_count()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_private_ca_is_added_on_top_of_certifi(tmp_path):
    ca, _ = _make_ca(tmp_path, "internal-ca")

    context = build_ssl_context(str(ca), env={})

    # H2OGPTE_CA_BUNDLE is additive, so the public roots stay trusted and a
    # bundle holding only the internal CA cannot silently break public TLS.
    assert _ca_count(context) == _certifi_count() + 1
    assert "internal-ca" in _common_names(context)


def test_requests_ca_bundle_is_added_on_top_of_certifi(tmp_path):
    ca, _ = _make_ca(tmp_path, "requests-ca")

    context = build_ssl_context(None, env={"REQUESTS_CA_BUNDLE": str(ca)})

    # httpx never reads REQUESTS_CA_BUNDLE, so adding it inverts nothing.
    assert _ca_count(context) == _certifi_count() + 1
    assert "requests-ca" in _common_names(context)


def test_ssl_cert_file_replaces_the_trust_store(tmp_path):
    ca, _ = _make_ca(tmp_path, "file-ca")

    context = build_ssl_context(None, env={"SSL_CERT_FILE": str(ca)})

    # httpx seeds its context with ssl.create_default_context(cafile=...),
    # which does not load the default roots. Adding the bundle to certifi
    # instead would hand back every public root an operator meant to drop.
    assert _common_names(context) == ["file-ca"]
    assert _ca_count(context) == 1


def test_ssl_cert_dir_replaces_the_trust_store(tmp_path):
    ca, ca_key = _make_ca(tmp_path, "dir-ca")
    ca_dir = _hashed_ca_dir(tmp_path, ca)
    server_cert, server_key = _make_server_cert(tmp_path, ca, ca_key)

    context = build_ssl_context(None, env={"SSL_CERT_DIR": str(ca_dir)})

    # get_ca_certs() cannot observe capath certificates, OpenSSL reads a hashed
    # directory lazily, so assert on what IS loaded eagerly: a replaced store
    # holds nothing, while adding the directory to certifi would hold every
    # public root. The handshake then proves the directory is really in use.
    assert context.get_ca_certs() == []
    assert context.cert_store_stats()["x509"] == 0

    with _tls_server(server_cert, server_key) as port:
        assert _handshake(context, port)["subject"]
        with pytest.raises(ssl.SSLCertVerificationError):
            _handshake(ssl.create_default_context(cafile=certifi.where()), port)


def test_ssl_cert_file_wins_over_ssl_cert_dir(tmp_path):
    file_ca, _ = _make_ca(tmp_path, "precedence-file-ca")
    dir_ca, _ = _make_ca(tmp_path, "precedence-dir-ca")
    ca_dir = _hashed_ca_dir(tmp_path, dir_ca)

    context = build_ssl_context(
        None, env={"SSL_CERT_FILE": str(file_ca), "SSL_CERT_DIR": str(ca_dir)}
    )

    # httpx consults SSL_CERT_FILE first and ignores SSL_CERT_DIR entirely when
    # both are set; a capath seed would leave get_ca_certs() empty.
    assert _common_names(context) == ["precedence-file-ca"]


def test_explicit_bundle_adds_to_a_replaced_store(tmp_path):
    env_ca, _ = _make_ca(tmp_path, "env-ca")
    explicit_ca, _ = _make_ca(tmp_path, "explicit-ca")

    context = build_ssl_context(str(explicit_ca), env={"SSL_CERT_FILE": str(env_ca)})

    assert sorted(_common_names(context)) == ["env-ca", "explicit-ca"]


def test_setting_and_env_naming_the_same_file_loads_it_once(tmp_path, capsys):
    ca, _ = _make_ca(tmp_path, "dup-ca")

    context = build_ssl_context(str(ca), env={"SSL_CERT_FILE": str(ca)})

    # The platform sets SSL_CERT_FILE and an admin may set H2OGPTE_CA_BUNDLE to
    # the same path; loading it twice is harmless but the dedup keeps the
    # startup log honest.
    assert _common_names(context) == ["dup-ca"]
    assert "Trusting additional CA bundle" not in capsys.readouterr().err


def test_missing_explicit_bundle_is_fatal(tmp_path):
    # Falling back to certifi here would start the server in exactly the state
    # H2OGPTE_CA_BUNDLE was set to fix, and every request would then fail with
    # an opaque CERTIFICATE_VERIFY_FAILED.
    with pytest.raises(ValueError, match="H2OGPTE_CA_BUNDLE not found"):
        build_ssl_context(str(tmp_path / "nope.pem"), env={})


def test_unreadable_explicit_bundle_is_fatal(tmp_path):
    junk = tmp_path / "junk.pem"
    junk.write_text("this is not a certificate\n")

    with pytest.raises(ValueError, match="H2OGPTE_CA_BUNDLE could not be loaded"):
        build_ssl_context(str(junk), env={})


@pytest.mark.parametrize(
    "env_var", ["SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE"]
)
def test_missing_inherited_bundle_is_skipped_not_fatal(tmp_path, capsys, env_var):
    # A stale value in a shared image must not take an otherwise working server
    # down, which is what httpx does with SSL_CERT_FILE.
    context = build_ssl_context(None, env={env_var: str(tmp_path / "nope.pem")})

    assert _ca_count(context) == _certifi_count()
    assert "not found" in capsys.readouterr().err


@pytest.mark.parametrize("env_var", ["SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"])
def test_unreadable_inherited_bundle_is_skipped_not_fatal(tmp_path, capsys, env_var):
    junk = tmp_path / "junk.pem"
    junk.write_text("this is not a certificate\n")

    context = build_ssl_context(None, env={env_var: str(junk)})

    assert _ca_count(context) == _certifi_count()
    assert "could not load" in capsys.readouterr().err
