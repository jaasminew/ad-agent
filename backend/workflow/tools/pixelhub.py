# tools/pixelhub.py
import ast
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)
 
# ==================== Configuration ====================
PIXELHUB_CONFIG = {
    "timeout": 30,  # Request timeout in seconds
    "max_retries": 3,  # Maximum number of retries
}
 
 
# ==================== PixelHub Client ====================
class PixelHubAPIError(Exception):
    """Custom exception for PixelHub API errors"""
 
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)
 
 
class PixelHubClient:
    """Client for interacting with PixelHub API"""
 
    def __init__(self, api_url: Optional[str] = None):
        self.api_url = api_url or os.environ.get("PIXELHUB_API_URL")
        if not self.api_url:
            raise ValueError("PIXELHUB_API_URL environment variable is not set")
        self.api_url = self.api_url.rstrip("/")
        self.timeout = PIXELHUB_CONFIG["timeout"]
        logger.info(f"✓ PixelHub client initialized with api_url: {self.api_url}")
 
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to PixelHub API"""
        url = f"{self.api_url}{endpoint}"
        try:
            response = requests.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
           
            data = response.json()
           
            # Check if response has expected structure
            if "code" not in data:
                logger.warning(f"Unexpected response structure from {endpoint}")
                return data
           
            # Handle API error codes
            if data["code"] >= 400:
                error_msg = data.get("message", "Unknown error")
                raise PixelHubAPIError(error_msg, data["code"])
           
            return data.get("data", {})
           
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {endpoint}: {e}")
            raise PixelHubAPIError(
                f"HTTP {e.response.status_code}: {e.response.text}",
                e.response.status_code,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {endpoint}: {e}")
            raise PixelHubAPIError(f"Request failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error for {endpoint}: {e}")
            raise PixelHubAPIError(f"Unexpected error: {str(e)}") from e
 
    def list_tags(self, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        List all tags from PixelHub.
       
        Args:
            page: Page number (starting from 1)
            limit: Number of tags per page (max 100)
       
        Returns:
            Response containing tags list:
            {
                "total": int,
                "current_page": int,
                "tags": [{"name": str, "count": int}, ...]
            }
        """
        logger.debug(f"Listing tags: page={page}, limit={limit}")

        result = self._make_request(
            "GET", "/tags", params={"page": page, "limit": limit}
        )
       
        logger.info(
            f"Retrieved {len(result.get('tags', []))} tags "
            f"(page {result.get('current_page', page)})"
        )
       
        return result
 
    def search_images(
        self, tags: List[str], page: int = 1, limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search images by tags (relevance search, OR logic).
       
        Args:
            tags: List of tags to search for
            page: Page number (starting from 1)
            limit: Number of results per page (max 100)
       
        Returns:
            Response containing search results:
            {
                "total": int,
                "current_page": int,
                "results": [
                    {
                        "id": str,
                        "url": str,
                        "description": str,
                        "matched_tag_count": int,
                        "tags": list[str]
                    },
                    ...
                ]
            }
        """
        logger.debug(f"Searching images: tags={tags}, page={page}, limit={limit}")

        if not tags:
            logger.warning("Empty tags list provided for search")
            return {"total": 0, "current_page": page, "results": []}
       
        result = self._make_request(
            "GET",
            "/search/relevance",
            params={"tags": ",".join(tags), "page": page, "limit": limit},
        )
       
        logger.info(
            f"Found {result.get('total', 0)} images for tags {tags}, "
            f"returned {len(result.get('results', []))} results"
        )
       
        return result
 
 
def _coerce_action_input_to_dict(raw_value: Any, tool_name: str) -> Dict[str, Any]:
    """Best-effort parse of legacy string formats like 'tool(param=1)' into dicts."""
    if isinstance(raw_value, dict):
        return raw_value
    if not isinstance(raw_value, str):
        return {}

    cleaned = raw_value.strip()
    if cleaned.lower().startswith("action input:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    cleaned = cleaned.strip().strip('"').strip("'")

    prefix = f"{tool_name}("
    if cleaned.lower().startswith(prefix):
        cleaned = cleaned[len(prefix) :]
        if cleaned.endswith(")"):
            cleaned = cleaned[:-1]
    elif cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]

    if cleaned.startswith("{") and cleaned.endswith("}"):
        for loader in (json.loads, ast.literal_eval):
            try:
                parsed = loader(cleaned)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

    dict_expr = f"dict({cleaned})" if cleaned else "dict()"
    try:
        parsed = ast.literal_eval(dict_expr)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    result: Dict[str, Any] = {}
    for fragment in re.split(r",\s*", cleaned):
        if "=" not in fragment:
            continue
        key, value = fragment.split("=", 1)
        key = key.strip()
        value = value.strip()
        try:
            parsed_value = ast.literal_eval(value)
        except Exception:
            parsed_value = value.strip('"').strip("'")
        result[key] = parsed_value
    return result


def _normalize_tags(tags_value: Any) -> List[str]:
    """Normalize tag inputs into a clean list of non-empty strings."""
    if isinstance(tags_value, list):
        return [str(tag).strip() for tag in tags_value if str(tag).strip()]
    if isinstance(tags_value, str):
        cleaned = tags_value.strip()
        try:
            parsed = ast.literal_eval(cleaned)
            if isinstance(parsed, (list, tuple, set)):
                return [str(tag).strip() for tag in parsed if str(tag).strip()]
            if isinstance(parsed, str):
                cleaned = parsed
        except Exception:
            pass
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1]
        return [part.strip().strip('"').strip("'") for part in cleaned.split(",") if part.strip()]
    return []


def _normalize_color_text(text: str) -> str:
    """Lowercase and strip punctuation so color keywords can be compared reliably."""
    normalized = text.lower().replace("-", " ")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


COLOR_FAMILY_KEYWORDS: Dict[str, List[str]] = {
    "blue": [
        "blue",
        "deep blue",
        "navy",
        "royal blue",
        "midnight blue",
        "cobalt",
        "indigo",
        "azure",
        "cerulean",
        "sky blue",
        "baby blue",
        "ice blue",
        "sapphire",
        "denim",
        "ocean blue",
        "prussian blue",
        "teal",
        "turquoise",
        "cyan",
        "aqua",
        "aquamarine",
    ],
    "green": [
        "green",
        "forest green",
        "emerald",
        "olive",
        "sage",
        "mint",
        "lime",
        "chartreuse",
        "seafoam",
        "moss",
        "jade",
        "hunter green",
    ],
    "red": [
        "red",
        "crimson",
        "scarlet",
        "ruby",
        "burgundy",
        "maroon",
        "wine",
        "cherry",
        "carmine",
        "garnet",
    ],
    "orange": [
        "orange",
        "amber",
        "tangerine",
        "apricot",
        "coral",
        "copper",
        "rust",
        "vermillion",
        "sunset orange",
    ],
    "yellow": [
        "yellow",
        "mustard",
        "lemon",
        "sunflower",
        "goldenrod",
        "citrine",
        "dandelion",
    ],
    "purple": [
        "purple",
        "violet",
        "lavender",
        "plum",
        "amethyst",
        "mauve",
        "lilac",
    ],
    "pink": [
        "pink",
        "rose",
        "blush",
        "fuchsia",
        "magenta",
        "salmon",
        "bubblegum",
        "hot pink",
    ],
    "brown": [
        "brown",
        "chocolate",
        "coffee",
        "mocha",
        "taupe",
        "sepia",
        "umber",
        "espresso",
        "caramel",
        "hazel",
    ],
    "black": [
        "black",
        "charcoal",
        "jet",
        "ebony",
        "onyx",
        "ink",
    ],
    "white": [
        "white",
        "ivory",
        "cream",
        "alabaster",
        "snow",
        "pearl",
    ],
    "gray": [
        "gray",
        "grey",
        "slate",
        "ash",
        "graphite",
        "pewter",
        "smoke",
    ],
    "gold": [
        "gold",
        "golden",
        "champagne",
    ],
    "silver": [
        "silver",
        "platinum",
        "chrome",
    ],
    "beige": [
        "beige",
        "khaki",
        "sand",
        "tan",
        "ecru",
    ],
}

_COLOR_PHRASE_KEYWORDS: Dict[str, str] = {}
_COLOR_WORD_KEYWORDS: Dict[str, str] = {}
for family, keywords in COLOR_FAMILY_KEYWORDS.items():
    for keyword in keywords:
        normalized_keyword = _normalize_color_text(keyword)
        if not normalized_keyword:
            continue
        if " " in normalized_keyword:
            _COLOR_PHRASE_KEYWORDS[normalized_keyword] = family
        else:
            _COLOR_WORD_KEYWORDS[normalized_keyword] = family


def _detect_color_family_from_text(text: str) -> Optional[str]:
    """Attempt to map a freeform tag into one of the coarse color families."""
    normalized = _normalize_color_text(text)
    if not normalized:
        return None

    for phrase, family in _COLOR_PHRASE_KEYWORDS.items():
        if phrase in normalized:
            return family

    for token in normalized.split():
        if token in _COLOR_WORD_KEYWORDS:
            return _COLOR_WORD_KEYWORDS[token]
    return None


def _extract_color_family_from_tags(tags: Any) -> Optional[str]:
    """Inspect a list of tags and return the first recognizable color family."""
    tag_list: List[str]
    if isinstance(tags, list):
        tag_list = [str(tag) for tag in tags]
    elif isinstance(tags, str):
        tag_list = [tags]
    else:
        return None

    for tag in tag_list:
        family = _detect_color_family_from_text(tag)
        if family:
            return family
    return None


def _tags_match_color_family(tags: Any, target_family: Optional[str]) -> bool:
    """Check whether the provided tag collection matches the given color family."""
    if not target_family:
        return False

    tag_list: List[str]
    if isinstance(tags, list):
        tag_list = [str(tag) for tag in tags]
    elif isinstance(tags, str):
        tag_list = [tags]
    else:
        return False

    for tag in tag_list:
        if _detect_color_family_from_text(tag) == target_family:
            return True
    return False


def _apply_color_realm_filter(
    sorted_results: List[Dict[str, Any]],
    max_results: int = 2,
) -> Tuple[List[Dict[str, Any]], Optional[str], int]:
    """
    Keep the anchor result and only include additional candidates whose tags map to the same color family.
    Returns the filtered list, the reference family, and the number of discarded candidates.
    """
    if not sorted_results or max_results <= 0:
        return [], None, 0

    anchor = sorted_results[0]
    reference_family = _extract_color_family_from_tags(anchor.get("tags"))
    if not reference_family:
        return sorted_results[:max_results], None, 0

    filtered: List[Dict[str, Any]] = [anchor]
    discarded = 0
    for candidate in sorted_results[1:]:
        if _tags_match_color_family(candidate.get("tags"), reference_family):
            filtered.append(candidate)
            if len(filtered) == max_results:
                break
        else:
            discarded += 1
    return filtered, reference_family, discarded


def _coerce_int(value: Any, field_name: str, tool_name: str) -> Any:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            parsed = _coerce_action_input_to_dict(stripped, tool_name)
            if field_name in parsed:
                return parsed[field_name]
        if stripped.isdigit():
            return int(stripped)
    return value


def _coerce_tags_argument(tags_value: Any) -> List[str]:
    if isinstance(tags_value, list):
        return _normalize_tags(tags_value)
    if isinstance(tags_value, str):
        stripped = tags_value.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            parsed = _coerce_action_input_to_dict(stripped, "search_images_by_tags")
            return _normalize_tags(parsed.get("tags", []))
        return _normalize_tags(tags_value)
    if isinstance(tags_value, dict):
        return _normalize_tags(tags_value.get("tags", []))
    return []


class ListTagsInput(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=1000, ge=1, le=1000)

    @model_validator(mode="before")
    @classmethod
    def parse_legacy_formats(cls, value: Any):
        if isinstance(value, str):
            return _coerce_action_input_to_dict(value, "list_tags")
        if isinstance(value, dict):
            page_val = value.get("page")
            limit_val = value.get("limit")
            combined: Dict[str, Any] = {}
            if isinstance(page_val, str) and page_val.strip().startswith("{"):
                combined = _coerce_action_input_to_dict(page_val, "list_tags")
            elif isinstance(limit_val, str) and limit_val.strip().startswith("{"):
                combined = _coerce_action_input_to_dict(limit_val, "list_tags")
            if combined:
                merged = combined.copy()
                merged.update({k: v for k, v in value.items() if k not in combined or not isinstance(v, str) or not v.strip().startswith("{")})
                return merged
            coerced = value.copy()
            return coerced
        return value

    @field_validator("page", "limit", mode="before")
    @classmethod
    def _coerce_int_fields(cls, value: Any, info):
        return _coerce_int(value, info.field_name, "list_tags")


class SearchImagesInput(BaseModel):
    tags: List[str]
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="before")
    @classmethod
    def parse_legacy_formats(cls, value: Any):
        if isinstance(value, str):
            value = _coerce_action_input_to_dict(value, "search_images_by_tags")
        if isinstance(value, dict):
            if isinstance(value.get("tags"), str) and value["tags"].strip().startswith("{"):
                legacy = _coerce_action_input_to_dict(value["tags"], "search_images_by_tags")
                merged = {**legacy, **value}
                value = merged
            value = value.copy()
            value["tags"] = _normalize_tags(value.get("tags", []))
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def _coerce_tags(cls, value: Any):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                parsed = _coerce_action_input_to_dict(stripped, "search_images_by_tags")
                if "tags" in parsed:
                    return _normalize_tags(parsed.get("tags", []))
            return _normalize_tags(value)
        return value

    @field_validator("page", "limit", mode="before")
    @classmethod
    def _coerce_page_limit(cls, value: Any, info):
        return _coerce_int(value, info.field_name, "search_images_by_tags")

    @model_validator(mode="after")
    def validate_tags(self):
        self.tags = [tag for tag in self.tags if tag]
        if not self.tags:
            raise ValueError("tags parameter is required and must contain at least one value")
        return self


# Lazy initialization of PixelHub client
_pixelhub_client = None


def get_pixelhub_client() -> PixelHubClient:
    """Get or create the PixelHub client singleton"""
    global _pixelhub_client
    if _pixelhub_client is None:
        _pixelhub_client = PixelHubClient()
    return _pixelhub_client


# ==================== LangChain Tools ====================

@tool("list_tags", args_schema=ListTagsInput)
def list_tags(page: int = 1, limit: int = 1000) -> str:
    """List all available tags in PixelHub. This helps understand what tags are available before searching for images.
    IMPORTANT: ALWAYS call this tool FIRST before searching for images to get available tags.

    Args:
        page: Page number (default: 1)
        limit: Number of tags per page (default: 1000, max: 1000). Use a high value to get all tags at once.

    Returns:
        A JSON string containing tags list with their usage counts.
    """
    logger.info(f"🏷️  [list_tags] Called - page: {page}, limit: {limit}")

    try:
        client = get_pixelhub_client()
        safe_page = _coerce_int(page, "page", "list_tags")
        safe_limit = _coerce_int(limit, "limit", "list_tags")
        result = client.list_tags(page=safe_page, limit=safe_limit)

        total = result.get("total", 0)
        current_page = result.get("current_page", safe_page)
        tags = result.get("tags", [])

        response = {
            "total": total,
            "current_page": current_page,
            "tags_count": len(tags),
            "tags": tags,
        }

        logger.info(f"✓ [list_tags] Retrieved {len(tags)} tags (total: {total})")
        return json.dumps(response, ensure_ascii=False, indent=2)

    except PixelHubAPIError as e:
        logger.error(f"❌ [list_tags] API error: {e}")
        return f"API Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [list_tags] Exception: {e}")
        return f"Error: {str(e)}"


@tool("search_images_by_tags", args_schema=SearchImagesInput)
def search_images_by_tags(tags: List[str], page: int = 1, limit: int = 20) -> str:
    """Search images by tags using relevance ranking (OR logic). Returns the top matches
    (max 2) sorted by matched tags and highlights the single best match explicitly. Additional
    results are only accepted if they share the color/tone family of the top match.
    IMPORTANT: Only use tags that exist in the system (call list_tags first).

    Args:
        tags: List of tags to search for. MUST use tags from list_tags result.
        page: Page number (default: 1)
        limit: Number of results per page (default: 20, max: 100)

    Returns:
        A JSON string containing the highlighted top match plus up to two top-ranked
        results with image URLs, descriptions, and matched tag counts.
    """
    normalized_tags = _coerce_tags_argument(tags)
    normalized_page = _coerce_int(page, "page", "search_images_by_tags")
    normalized_limit = _coerce_int(limit, "limit", "search_images_by_tags")

    logger.info(
        f"🔍 [search_images_by_tags] Called - tags: {normalized_tags}, page: {normalized_page}, limit: {normalized_limit}"
    )

    if not normalized_tags:
        error_msg = "tags parameter is required and must not be empty"
        logger.error(f"❌ [search_images_by_tags] {error_msg}")
        return f"Error: {error_msg}"

    try:
        client = get_pixelhub_client()
        result = client.search_images(tags=normalized_tags, page=normalized_page, limit=normalized_limit)

        total = result.get("total", 0)
        current_page = result.get("current_page", page)
        results = result.get("results", [])
        sorted_results = sorted(
            results,
            key=lambda item: (
                item.get("matched_tag_count", 0),
                item.get("upload_date") or "",
                item.get("id") or "",
            ),
            reverse=True,
        )
        filtered_results, reference_color_family, discarded_candidates = _apply_color_realm_filter(
            sorted_results,
            max_results=2,
        )
        top_match = filtered_results[0] if filtered_results else None

        if reference_color_family:
            logger.info(
                "🎨 [search_images_by_tags] Anchored color realm '%s' retained %d result(s), discarded %d mismatched candidate(s)",
                reference_color_family,
                len(filtered_results),
                discarded_candidates,
            )
        else:
            logger.debug("[search_images_by_tags] Color realm filter skipped (no color tags detected in top result).")

        response = {
            "total": total,
            "current_page": current_page,
            "available_results_count": len(results),
            "results_count": len(filtered_results),
            "top_match": top_match,
            "results": filtered_results,
            "color_filter": {
                "filter_applied": bool(reference_color_family),
                "reference_family": reference_color_family,
                "discarded_candidates": discarded_candidates if reference_color_family else 0,
            },
        }

        logger.info(
            "✓ [search_images_by_tags] Found %d images, returning %d filtered result(s)",
            total,
            len(filtered_results),
        )
        return json.dumps(response, ensure_ascii=False, indent=2)

    except PixelHubAPIError as e:
        logger.error(f"❌ [search_images_by_tags] API error: {e}")
        return f"API Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [search_images_by_tags] Exception: {e}")
        return f"Error: {str(e)}"