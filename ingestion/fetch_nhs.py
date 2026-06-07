"""
fetch_nhs.py – Download NHS A&E monthly CSV files from NHS England.

The NHS England statistics site uses a two-level structure:
  Landing page  →  year sub-pages  →  individual CSV files

The scraper:
  1. Fetches the main landing page and finds links to year-specific sub-pages
     (URLs matching the ae-attendances-and-emergency-admissions pattern).
  2. Fetches each sub-page and collects .csv download links.
  3. Downloads any CSV not already present in data/raw/.

Re-running is safe: files that already exist are skipped (idempotent).
"""

import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import NHS_BASE_URL, RAW_DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# HTTP request settings
_SESSION_HEADERS = {
    "User-Agent": (
        "PulseBoard/1.0 (NHS A&E research pipeline; "
        "contact: admin@example.com)"
    )
}
_DOWNLOAD_DELAY_S = 0.3   # polite delay between requests/downloads
_REQUEST_TIMEOUT  = 30    # seconds

# Regex to recognise year-specific A&E sub-page hrefs
# Matches patterns like:
#   /statistics/.../ae-attendances-and-emergency-admissions-2025-26/
#   /statistics/.../weekly-ae-sitreps-2015-16/
#   /statistics/.../ae-attendances-and-emergency-admissions-2015-16-monthly-3/
_YEAR_PAGE_RE = re.compile(
    r"ae-waiting-times-and-activity/"
    r"(?:statistical-work-areasae-waiting-times-and-activityae-attendances-and-emergency-admissions-"
    r"|statistical-work-areasae-waiting-times-and-activityweekly-ae-sitreps-"
    r"|ae-attendances-and-emergency-admissions-"
    r"|weekly-ae-sitreps-)"
    r"\d{4}-\d{2,4}",
    re.IGNORECASE,
)


def _make_session() -> requests.Session:
    """Return a requests.Session pre-configured with project headers."""
    s = requests.Session()
    s.headers.update(_SESSION_HEADERS)
    return s


def _find_year_subpage_links(html: str, base_url: str) -> list[str]:
    """
    Parse *html* (the landing page) and return absolute URLs of year-specific
    A&E sub-pages.

    Parameters
    ----------
    html:     Raw HTML of the NHS A&E statistics landing page.
    base_url: Base URL used to resolve relative hrefs.

    Returns
    -------
    Deduplicated list of absolute sub-page URLs.
    """
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for tag in soup.find_all("a", href=True):
        href: str = tag["href"].strip()
        if _YEAR_PAGE_RE.search(href):
            absolute = urljoin(base_url, href)
            urls.append(absolute)

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def _find_csv_links(html: str, base_url: str) -> list[str]:
    """
    Parse *html* and return a list of absolute URLs whose href ends with
    '.csv' (case-insensitive).

    Parameters
    ----------
    html:     Raw HTML of a year-specific A&E statistics page.
    base_url: Base URL used to resolve relative hrefs.

    Returns
    -------
    Deduplicated list of absolute CSV URLs.
    """
    soup = BeautifulSoup(html, "lxml")
    urls: list[str] = []
    for tag in soup.find_all("a", href=True):
        href: str = tag["href"].strip()
        if href.lower().endswith(".csv"):
            absolute = urljoin(base_url, href)
            urls.append(absolute)

    seen: set[str] = set()
    unique: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def _local_path_for(url: str) -> Path:
    """
    Derive a local file path under RAW_DATA_DIR from a CSV URL.

    The filename is taken from the URL path so that re-running produces the
    same path (idempotency key).
    """
    filename = Path(urlparse(url).path).name
    return RAW_DATA_DIR / filename


def _download_file(session: requests.Session, url: str, dest: Path) -> None:
    """
    Stream-download *url* to *dest*, creating parent directories as needed.

    Raises
    ------
    requests.HTTPError if the server returns a non-2xx status code.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = session.get(url, timeout=_REQUEST_TIMEOUT, stream=True)
    response.raise_for_status()
    with dest.open("wb") as fh:
        for chunk in response.iter_content(chunk_size=65_536):
            fh.write(chunk)


def _collect_all_csv_urls(session: requests.Session, base_url: str) -> list[str]:
    """
    Two-level crawl: landing page → year sub-pages → CSV links.

    Parameters
    ----------
    session:  Configured requests.Session.
    base_url: NHS A&E statistics landing page URL.

    Returns
    -------
    Deduplicated list of all .csv URLs found across all year sub-pages.
    """
    log.info("Fetching NHS A&E statistics landing page: %s", base_url)
    resp = session.get(base_url, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()

    year_pages = _find_year_subpage_links(resp.text, base_url)
    log.info("Found %d year sub-page(s).", len(year_pages))

    all_csv_urls: list[str] = []
    seen_urls: set[str] = set()

    for page_url in year_pages:
        log.info("  Scanning: %s", page_url)
        try:
            page_resp = session.get(page_url, timeout=_REQUEST_TIMEOUT)
            page_resp.raise_for_status()
        except requests.RequestException as exc:
            log.warning("    Could not fetch %s: %s", page_url, exc)
            continue

        csv_links = _find_csv_links(page_resp.text, page_url)
        new = [u for u in csv_links if u not in seen_urls]
        seen_urls.update(new)
        all_csv_urls.extend(new)
        log.info("    → %d CSV link(s) found.", len(csv_links))
        time.sleep(_DOWNLOAD_DELAY_S)

    return all_csv_urls


def fetch_all_csvs(base_url: str = NHS_BASE_URL) -> list[Path]:
    """
    Crawl the NHS A&E statistics site, download any new CSV files, and
    return a list of local file paths for all discovered CSVs.

    The function is idempotent: calling it twice will not re-download files
    that already exist in ``RAW_DATA_DIR``.

    Parameters
    ----------
    base_url: NHS A&E statistics landing page URL.  Defaults to the value
              in config.NHS_BASE_URL.

    Returns
    -------
    List of ``pathlib.Path`` objects pointing to the local CSV files
    (both newly downloaded and pre-existing).
    """
    session = _make_session()

    csv_urls = _collect_all_csv_urls(session, base_url)
    log.info("Total CSV URLs discovered: %d", len(csv_urls))

    local_paths: list[Path] = []
    downloaded = 0
    skipped = 0

    for url in csv_urls:
        dest = _local_path_for(url)
        if dest.exists():
            log.debug("Skipping (already downloaded): %s", dest.name)
            skipped += 1
        else:
            log.info("Downloading: %s", dest.name)
            try:
                _download_file(session, url, dest)
                downloaded += 1
                time.sleep(_DOWNLOAD_DELAY_S)
            except requests.RequestException as exc:
                log.warning("Failed to download %s: %s", url, exc)
                continue
        local_paths.append(dest)

    log.info(
        "Complete. %d downloaded, %d already existed, %d total.",
        downloaded,
        skipped,
        len(local_paths),
    )
    return local_paths


if __name__ == "__main__":
    paths = fetch_all_csvs()
    print(f"\n{len(paths)} CSV file(s) ready in {RAW_DATA_DIR}")
