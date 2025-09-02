"""Gemini API client for image analysis and document understanding."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
import types
from pathlib import Path
from typing import Any, ClassVar, Self

import aiohttp

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for Google Gemini API with rate limiting and image analysis."""

    # API configuration
    BASE_URL: ClassVar[str] = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL: ClassVar[str] = "gemini-1.5-flash"

    # Rate limiting (requests per minute)
    RATE_LIMIT: ClassVar[int] = 60
    RATE_WINDOW: ClassVar[int] = 60  # seconds

    def __init__(self, api_key: str, model: str | None = None):
        """Initialize Gemini client."""
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.session: aiohttp.ClientSession | None = None

        # Rate limiting
        self._request_times: list[float] = []
        self._rate_lock = asyncio.Lock()

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("Created Gemini API session")

    async def disconnect(self) -> None:
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Closed Gemini API session")

    async def _wait_for_rate_limit(self) -> None:
        """Wait if rate limit would be exceeded."""
        async with self._rate_lock:
            now = time.time()

            # Remove old requests outside the window
            self._request_times = [
                t for t in self._request_times if now - t < self.RATE_WINDOW
            ]

            # Check if we need to wait
            if len(self._request_times) >= self.RATE_LIMIT:
                oldest_request = self._request_times[0]
                wait_time = self.RATE_WINDOW - (now - oldest_request) + 0.1
                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    # Clean up again after waiting
                    now = time.time()
                    self._request_times = [
                        t for t in self._request_times if now - t < self.RATE_WINDOW
                    ]

            # Record this request
            self._request_times.append(now)

    async def _make_request(
        self, endpoint: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Make API request with error handling."""
        if not self.session:
            await self.connect()

        # Apply rate limiting
        await self._wait_for_rate_limit()

        url = f"{self.BASE_URL}/models/{self.model}:{endpoint}?key={self.api_key}"

        # Assert session is not None (guaranteed by connect() call above)
        assert self.session is not None

        try:
            async with self.session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result: dict[str, Any] = await response.json()
                    return result
                if response.status == 429:
                    # Rate limit exceeded, wait and retry
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"Rate limit exceeded, retrying after {retry_after}s"
                    )
                    await asyncio.sleep(retry_after)
                    return await self._make_request(endpoint, payload)
                error_text = await response.text()
                msg = f"Gemini API error ({response.status}): {error_text}"
                raise ValueError(msg)
        except asyncio.TimeoutError as e:
            msg = "Gemini API request timed out"
            raise TimeoutError(msg) from e
        except Exception:
            logger.exception("Gemini API request failed")
            raise

    async def analyze_image(
        self,
        image_path: Path | str,
        prompt: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any]:
        """Analyze an image with Gemini Vision."""
        image_path = Path(image_path) if isinstance(image_path, str) else image_path

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Detect MIME type if not provided
        if not mime_type:
            suffix = image_path.suffix.lower()
            mime_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".bmp": "image/bmp",
                ".webp": "image/webp",
            }
            mime_type = mime_map.get(suffix, "image/jpeg")

        # Default prompt for document/chart analysis
        if not prompt:
            prompt = """Analyze this image and provide:
1. A detailed description of what you see
2. If it's a chart or graph, extract the data and explain the trends
3. If it contains text, extract all visible text
4. If it's a diagram, explain the relationships shown
5. Any other relevant information or insights"""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": image_data}},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 32,
                "topP": 1,
                "maxOutputTokens": 4096,
            },
        }

        response = await self._make_request("generateContent", payload)

        # Extract text from response
        result = {
            "prompt": prompt,
            "response": self._extract_text_from_response(response),
            "image_path": str(image_path),
            "mime_type": mime_type,
        }

        return result

    async def extract_chart_data(self, image_path: Path | str) -> dict[str, Any]:
        """Extract structured data from charts and graphs."""
        prompt = """You are analyzing a chart or graph. Please:
1. Identify the type of chart (bar, line, pie, scatter, etc.)
2. Extract all data points with their exact values
3. Identify axes labels and units
4. Extract the title and any legends
5. Provide the data in a structured JSON format like:
{
    "chart_type": "...",
    "title": "...",
    "x_axis": {"label": "...", "unit": "..."},
    "y_axis": {"label": "...", "unit": "..."},
    "data_points": [...],
    "legend": [...]
}"""

        result = await self.analyze_image(image_path, prompt)
        result["extraction_type"] = "chart_data"
        return result

    async def perform_ocr(self, image_path: Path | str) -> dict[str, Any]:
        """Perform OCR on an image."""
        prompt = """Extract ALL text from this image.
Please provide:
1. The complete text content preserving the original formatting
2. Any headers or titles
3. Any tables with their structure preserved
4. Any footnotes or captions
Return the text exactly as it appears."""

        result = await self.analyze_image(image_path, prompt)
        result["extraction_type"] = "ocr"
        return result

    async def describe_diagram(self, image_path: Path | str) -> dict[str, Any]:
        """Describe diagrams and flowcharts."""
        prompt = """Analyze this diagram or flowchart. Please provide:
1. The type of diagram (flowchart, UML, network, org chart, etc.)
2. All components/nodes and their labels
3. All connections/relationships between components
4. The flow or hierarchy shown
5. A structured representation of the diagram's information"""

        result = await self.analyze_image(image_path, prompt)
        result["extraction_type"] = "diagram"
        return result

    async def analyze_document_page(self, image_path: Path | str) -> dict[str, Any]:
        """Analyze a document page image."""
        prompt = """Analyze this document page. Extract and provide:
1. All text content maintaining the original structure
2. Section headings and their hierarchy
3. Any tables with their full content
4. Lists and bullet points
5. Page numbers if visible
6. Headers and footers
7. Any special formatting or emphasis
Preserve the document structure and formatting in your response."""

        result = await self.analyze_image(image_path, prompt)
        result["extraction_type"] = "document_page"
        return result

    async def batch_analyze(
        self, image_paths: list[Path | str], prompt: str | None = None
    ) -> list[dict[str, Any]]:
        """Analyze multiple images with rate limiting."""
        results = []

        for image_path in image_paths:
            try:
                result = await self.analyze_image(image_path, prompt)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze {image_path}: {e}")
                results.append(
                    {
                        "image_path": str(image_path),
                        "error": str(e),
                        "prompt": prompt,
                    }
                )

        return results

    def _extract_text_from_response(self, response: dict[str, Any]) -> str:
        """Extract text content from Gemini API response."""
        try:
            candidates = response.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text: str = parts[0].get("text", "")
                    return text
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Failed to extract text from response: {e}")

        return ""

    async def get_rate_limit_status(self) -> dict[str, Any]:
        """Get current rate limit status."""
        async with self._rate_lock:
            now = time.time()
            self._request_times = [
                t for t in self._request_times if now - t < self.RATE_WINDOW
            ]

            return {
                "requests_made": len(self._request_times),
                "requests_limit": self.RATE_LIMIT,
                "window_seconds": self.RATE_WINDOW,
                "requests_remaining": self.RATE_LIMIT - len(self._request_times),
            }
