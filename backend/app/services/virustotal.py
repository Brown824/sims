"""
SIMS VirusTotal Service
Async URL threat intelligence using VirusTotal API v3.

Free tier limits: 4 requests/min, 500/day.
Mitigation: Cache results by URL hash in DB (Phase 4).

Flow:
  extract_urls(sms_text)
  → [if URLs found] POST to VT API
  → Parse response: positives / total engines
  → Return URLScanResult list
"""

import hashlib
import asyncio
from typing import List, Optional
from pydantic import BaseModel
from loguru import logger
import httpx

from app.db.database import get_cached_url, cache_url_result


# ── Data Models ───────────────────────────────────────────────────────────────

class URLScanResult(BaseModel):
    url: str
    url_hash: str              # SHA256 — used as cache key
    is_malicious: bool
    malicious_count: int = 0   # VT engines that flagged it
    total_engines: int = 0     # Total VT engines checked
    error: Optional[str] = None


# ── VirusTotal Client ─────────────────────────────────────────────────────────

class VirusTotalClient:
    """
    Async VirusTotal API v3 client with rate limiting and caching hooks.
    Phase 1: Full interface + error handling.
    Phase 4: DB caching wired in.
    """

    VT_URL_SCAN_ENDPOINT = "https://www.virustotal.com/api/v3/urls"
    VT_URL_REPORT_ENDPOINT = "https://www.virustotal.com/api/v3/urls/{id}"

    def __init__(self, api_key: str, requests_per_minute: int = 4):
        self.api_key = api_key
        self._rate_limit = requests_per_minute
        self._request_timestamps: List[float] = []

    @staticmethod
    def url_to_hash(url: str) -> str:
        """SHA256 of the URL — used as VirusTotal URL ID and DB cache key."""
        import base64
        # VT uses URL-safe base64 of the URL (without padding)
        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
        return url_id

    @staticmethod
    def url_sha256(url: str) -> str:
        """Plain SHA256 for DB cache key."""
        return hashlib.sha256(url.encode()).hexdigest()

    async def _enforce_rate_limit(self) -> None:
        """Ensure we don't exceed VT free tier (4 req/min)."""
        import time
        now = time.time()
        # Remove timestamps older than 60 seconds
        self._request_timestamps = [t for t in self._request_timestamps if now - t < 60]
        if len(self._request_timestamps) >= self._rate_limit:
            wait_time = 60 - (now - self._request_timestamps[0]) + 0.5
            logger.warning(f"VT rate limit reached. Waiting {wait_time:.1f}s ...")
            await asyncio.sleep(wait_time)

    async def scan_url(self, url: str) -> URLScanResult:
        """
        Submit a URL to VirusTotal for scanning.
        Returns URLScanResult with malicious verdict.

        Phase 4: Check DB cache first before making API call.
        """
        import time
        url_hash = self.url_to_hash(url)
        sha256 = self.url_sha256(url)

        # Check DB cache first
        try:
            cached = await get_cached_url(sha256)
            if cached:
                return URLScanResult(
                    url=url,
                    url_hash=sha256,
                    is_malicious=bool(cached["is_malicious"]),
                    malicious_count=cached["malicious_count"],
                    total_engines=cached["total_engines"],
                )
        except Exception:
            pass  # Cache miss or DB error — continue to API

        if not self.api_key or self.api_key == "your_virustotal_api_key_here":
            logger.warning("VirusTotal API key not configured — skipping URL scan.")
            return URLScanResult(
                url=url,
                url_hash=sha256,
                is_malicious=False,
                error="VT_API_KEY_NOT_CONFIGURED",
            )

        await self._enforce_rate_limit()

        headers = {
            "x-apikey": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Step 1: Submit URL for analysis
                self._request_timestamps.append(time.time())
                submit_resp = await client.post(
                    self.VT_URL_SCAN_ENDPOINT,
                    headers=headers,
                    data={"url": url},
                )
                submit_resp.raise_for_status()
                analysis_id = submit_resp.json()["data"]["id"]

                # Step 2: Get analysis report
                report_resp = await client.get(
                    f"https://www.virustotal.com/api/v3/analyses/{analysis_id}",
                    headers={"x-apikey": self.api_key},
                )
                report_resp.raise_for_status()
                stats = report_resp.json()["data"]["attributes"]["stats"]

                malicious = stats.get("malicious", 0)
                suspicious = stats.get("suspicious", 0)
                total = sum(stats.values())
                flagged = malicious + suspicious

                result = URLScanResult(
                    url=url,
                    url_hash=sha256,
                    is_malicious=flagged > 0,
                    malicious_count=flagged,
                    total_engines=total,
                )
                logger.info(
                    f"VT scan: {url[:60]}... → "
                    f"{'🚨 MALICIOUS' if result.is_malicious else '✅ CLEAN'} "
                    f"({flagged}/{total} engines)"
                )
                # Save to cache
                try:
                    await cache_url_result(
                        url_hash=sha256,
                        url=url,
                        is_malicious=result.is_malicious,
                        malicious_count=result.malicious_count,
                        total_engines=result.total_engines,
                    )
                except Exception:
                    pass
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"VT HTTP error for {url}: {e.response.status_code}")
            return URLScanResult(
                url=url,
                url_hash=sha256,
                is_malicious=False,
                error=f"HTTP_{e.response.status_code}",
            )
        except Exception as e:
            logger.error(f"VT scan failed for {url}: {e}")
            return URLScanResult(
                url=url,
                url_hash=sha256,
                is_malicious=False,
                error=str(e),
            )

    async def scan_urls(self, urls: List[str]) -> List[URLScanResult]:
        """
        Scan multiple URLs concurrently (respecting rate limits).
        Runs all scans in parallel with asyncio.gather.
        """
        if not urls:
            return []
        tasks = [self.scan_url(url) for url in urls]
        return await asyncio.gather(*tasks)


# ── Singleton ─────────────────────────────────────────────────────────────────

_vt_client: Optional[VirusTotalClient] = None


def get_vt_client() -> VirusTotalClient:
    """FastAPI dependency — returns the global VirusTotal client."""
    global _vt_client
    if _vt_client is None:
        from app.config import settings
        _vt_client = VirusTotalClient(
            api_key=settings.VIRUSTOTAL_API_KEY,
            requests_per_minute=settings.VT_REQUESTS_PER_MINUTE,
        )
    return _vt_client
