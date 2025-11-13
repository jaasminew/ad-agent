# tools/pixelhub.py
import os
import logging
from typing import Dict, Any, List, Optional
import requests
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

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


# Lazy initialization of PixelHub client
_pixelhub_client = None


def get_pixelhub_client() -> PixelHubClient:
    """Get or create the PixelHub client singleton"""
    global _pixelhub_client
    if _pixelhub_client is None:
        _pixelhub_client = PixelHubClient()
    return _pixelhub_client


# ==================== LangChain Tools ====================

# Input schemas for tools
class ListTagsInput(BaseModel):
    """Input schema for list_tags tool"""
    page: int = Field(default=1, description="Page number (starting from 1)")
    limit: int = Field(default=1000, description="Number of tags per page (max: 1000). Use a high value to get all tags at once.")


class SearchImagesByTagsInput(BaseModel):
    """Input schema for search_images_by_tags tool"""
    tags: List[str] = Field(description="List of tags to search for. MUST use tags from list_tags result.")
    page: int = Field(default=1, description="Page number (starting from 1)")
    limit: int = Field(default=20, description="Number of results per page (max: 100)")


# Implementation functions
def _list_tags_impl(page: int = 1, limit: int = 1000) -> str:
    """Implementation for list_tags tool"""
    logger.info(f"🏷️  [list_tags] Called - page: {page}, limit: {limit}")
    
    try:
        client = get_pixelhub_client()
        result = client.list_tags(page=page, limit=limit)
        
        # Format result for better readability
        total = result.get("total", 0)
        current_page = result.get("current_page", page)
        tags = result.get("tags", [])
        
        response = {
            "total": total,
            "current_page": current_page,
            "tags_count": len(tags),
            "tags": tags
        }
        
        logger.info(f"✓ [list_tags] Retrieved {len(tags)} tags (total: {total})")
        
        import json
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except PixelHubAPIError as e:
        logger.error(f"❌ [list_tags] API error: {e}")
        return f"API Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [list_tags] Exception: {e}")
        return f"Error: {str(e)}"


def _search_images_by_tags_impl(tags: List[str], page: int = 1, limit: int = 20) -> str:
    """Implementation for search_images_by_tags tool"""
    logger.info(f"🔍 [search_images_by_tags] Called - tags: {tags}, page: {page}, limit: {limit}")
    
    # Validate input
    if not tags:
        error_msg = "tags parameter is required and must not be empty"
        logger.error(f"❌ [search_images_by_tags] {error_msg}")
        return f"Error: {error_msg}"
    
    if not isinstance(tags, list):
        error_msg = f"tags must be a list, received: {type(tags)}"
        logger.error(f"❌ [search_images_by_tags] {error_msg}")
        return f"Error: {error_msg}"
    
    try:
        client = get_pixelhub_client()
        result = client.search_images(tags=tags, page=page, limit=limit)
        
        # Format result for better readability
        total = result.get("total", 0)
        current_page = result.get("current_page", page)
        results = result.get("results", [])
        
        response = {
            "total": total,
            "current_page": current_page,
            "results_count": len(results),
            "results": results
        }
        
        logger.info(f"✓ [search_images_by_tags] Found {total} images, returned {len(results)} results")
        
        import json
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except PixelHubAPIError as e:
        logger.error(f"❌ [search_images_by_tags] API error: {e}")
        return f"API Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [search_images_by_tags] Exception: {e}")
        return f"Error: {str(e)}"


# Create StructuredTool instances
list_tags = StructuredTool.from_function(
    func=_list_tags_impl,
    name="list_tags",
    description="List all available tags in PixelHub. This helps understand what tags are available before searching for images. IMPORTANT: ALWAYS call this tool FIRST before searching for images to get available tags.",
    args_schema=ListTagsInput,
)

search_images_by_tags = StructuredTool.from_function(
    func=_search_images_by_tags_impl,
    name="search_images_by_tags",
    description="Search images by tags using relevance ranking (OR logic). Returns images that match any of the provided tags, sorted by number of matched tags. IMPORTANT: Only use tags that exist in the system (call list_tags first).",
    args_schema=SearchImagesByTagsInput,
)

