import pytest

from app.security import compute_signature, is_valid_signature, tokens_match

SECRET = "app-secret"
BODY = b'{"object":"whatsapp_business_account"}'


def test_signature_has_the_expected_format() -> None:
    signature = compute_signature(BODY, SECRET)

    assert signature.startswith("sha256=")
    assert len(signature) == len("sha256=") + 64


def test_valid_signature_is_accepted() -> None:
    assert is_valid_signature(BODY, compute_signature(BODY, SECRET), SECRET)


def test_known_signature_vector() -> None:
    # HMAC-SHA256("body", "secret") calculé indépendamment
    assert compute_signature(b"body", "secret") == (
        "sha256=dc46983557fea127b43af721467eb9b3fde2338fe3e14f51952aa8478c13d355"
    )


@pytest.mark.parametrize(
    "header",
    [None, "", "sha256=", "sha256=deadbeef", "md5=abc", "é" * 10],
)
def test_invalid_headers_are_rejected(header: str | None) -> None:
    assert not is_valid_signature(BODY, header, SECRET)


def test_signature_from_another_secret_is_rejected() -> None:
    assert not is_valid_signature(BODY, compute_signature(BODY, "autre-secret"), SECRET)


def test_tampered_body_is_rejected() -> None:
    signature = compute_signature(BODY, SECRET)

    assert not is_valid_signature(BODY + b" ", signature, SECRET)


def test_empty_secret_never_validates() -> None:
    assert not is_valid_signature(BODY, compute_signature(BODY, ""), "")


def test_tokens_match() -> None:
    assert tokens_match("abc", "abc")
    assert not tokens_match("abd", "abc")
    assert not tokens_match(None, "abc")


def test_empty_expected_token_is_never_valid() -> None:
    assert not tokens_match("", "")
    assert not tokens_match(None, "")


def test_non_ascii_tokens_do_not_crash() -> None:
    assert not tokens_match("é", "e")
