"""Unit tests for the SEC/filing downloader.

These tests cover the concrete bugs that were fixed:
  * downloads are organized by filing type (data/raw/<TYPE>/) so the extractors
    can find their inputs;
  * Google Drive's large-file confirmation interstitial is handled;
  * an HTML error page is never silently kept as a ".pdf".

They intentionally avoid any real network access and any heavy dependency
(torch/docling/pdfplumber), so they run fast and deterministically in CI.
"""

import sys
from pathlib import Path

import pytest

# Make ``src`` importable without installing the package.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from downloaders.sec_downloader import SECDownloader  # noqa: E402


class FakeResponse:
    """Minimal stand-in for a ``requests`` response object."""

    def __init__(self, body: bytes, *, headers=None, cookies=None, text=""):
        self._body = body
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.text = text

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]


class FakeSession:
    """Returns queued responses in order for successive ``get`` calls."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self._responses.pop(0)


PDF_BYTES = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\nfake pdf body"
HTML_BYTES = b"<!DOCTYPE html><html><body>Virus scan warning</body></html>"


def test_is_pdf_true_for_pdf_magic(tmp_path):
    f = tmp_path / "a.pdf"
    f.write_bytes(PDF_BYTES)
    assert SECDownloader._is_pdf(f) is True


def test_is_pdf_false_for_html(tmp_path):
    f = tmp_path / "a.pdf"
    f.write_bytes(HTML_BYTES)
    assert SECDownloader._is_pdf(f) is False


def test_gdrive_token_from_cookie():
    resp = FakeResponse(b"", cookies={"download_warning_abc": "tok123"})
    assert SECDownloader._extract_gdrive_confirm_token(resp) == "tok123"


def test_gdrive_token_from_html_form():
    html = '<form><input type="hidden" name="confirm" value="tok999"></form>'
    resp = FakeResponse(b"", headers={"Content-Type": "text/html"}, text=html)
    assert SECDownloader._extract_gdrive_confirm_token(resp) == "tok999"


def test_gdrive_token_absent_for_plain_pdf():
    resp = FakeResponse(PDF_BYTES, headers={"Content-Type": "application/pdf"})
    assert SECDownloader._extract_gdrive_confirm_token(resp) is None


def test_download_file_keeps_valid_pdf(tmp_path, monkeypatch):
    dl = SECDownloader(output_dir=str(tmp_path))
    session = FakeSession([FakeResponse(PDF_BYTES,
                                        headers={"Content-Type": "application/pdf"})])
    monkeypatch.setattr("downloaders.sec_downloader.requests.Session",
                        lambda: session)

    ok = dl.download_file("https://example.com/file.pdf", tmp_path, "out.pdf")

    assert ok is True
    assert (tmp_path / "out.pdf").read_bytes() == PDF_BYTES


def test_download_file_discards_html_error_page(tmp_path, monkeypatch):
    dl = SECDownloader(output_dir=str(tmp_path))
    session = FakeSession([FakeResponse(HTML_BYTES,
                                        headers={"Content-Type": "text/html"})])
    monkeypatch.setattr("downloaders.sec_downloader.requests.Session",
                        lambda: session)

    ok = dl.download_file("https://example.com/file.pdf", tmp_path, "out.pdf")

    assert ok is False
    # The bogus HTML must not be left behind masquerading as a PDF.
    assert not (tmp_path / "out.pdf").exists()


def test_download_file_follows_gdrive_confirmation(tmp_path, monkeypatch):
    dl = SECDownloader(output_dir=str(tmp_path))
    interstitial = FakeResponse(
        HTML_BYTES,
        headers={"Content-Type": "text/html"},
        cookies={"download_warning_x": "tokabc"},
    )
    real_pdf = FakeResponse(PDF_BYTES, headers={"Content-Type": "application/pdf"})
    session = FakeSession([interstitial, real_pdf])
    monkeypatch.setattr("downloaders.sec_downloader.requests.Session",
                        lambda: session)

    ok = dl.download_file(
        "https://drive.google.com/uc?export=download&id=XYZ", tmp_path, "out.pdf"
    )

    assert ok is True
    assert (tmp_path / "out.pdf").read_bytes() == PDF_BYTES
    # The confirm token must have been sent on the second request.
    assert session.calls[1][1]["params"] == {"confirm": "tokabc"}


def test_download_filings_organizes_by_filing_type(tmp_path, monkeypatch):
    """Downloads must land in data/raw/<FILING_TYPE>/ to match the extractors."""
    dl = SECDownloader(output_dir=str(tmp_path))
    written = []

    def fake_download_file(url, output_path, filename):
        target = Path(output_path) / filename
        target.write_bytes(PDF_BYTES)
        written.append(target)
        return True

    monkeypatch.setattr(dl, "download_file", fake_download_file)
    # Both known filings resolve to real URLs.
    dl.download_filings(["META"], [2024], ["10-K", "10-Q"])

    produced = {p.relative_to(tmp_path).as_posix() for p in written}
    assert "10-K/2024_meta_10-k.pdf" in produced
    assert "10-Q/2024_meta_10-q.pdf" in produced
