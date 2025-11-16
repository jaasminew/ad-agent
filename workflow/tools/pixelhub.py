# tools/pixelhub.py
import os
import logging
from typing import Dict, Any, List, Optional
import requests
from langchain.tools import tool

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

@tool("list_tags")
def list_tags() -> str:
    """List all available tags in PixelHub. This helps understand what tags are available before searching for images.
    IMPORTANT: ALWAYS call this tool FIRST before searching for images to get available tags.
    
    Returns:
        A JSON string containing a simple list of all tag names: ["tag1", "tag2", "tag3"]
    """
    logger.info(f"?️  [list_tags] Called - fetching all tags")
    
    try:
        client = get_pixelhub_client()
        all_tag_names = []
        page = 1
        limit = 1000  # Max allowed per page
        
        while True:
            result = client.list_tags(page=page, limit=limit)
            tags = result.get("tags", [])
            
            # Extract tag names from current page
            tag_names = [tag.get("name") for tag in tags if tag.get("name")]
            all_tag_names.extend(tag_names)
            
            # Check if we have more pages
            total = result.get("total", 0)
            current_count = len(all_tag_names)
            
            logger.debug(f"Page {page}: Retrieved {len(tag_names)} tags (total so far: {current_count}/{total})")
            
            if current_count >= total or len(tags) < limit:
                # No more pages
                break
            
            page += 1
        
        logger.info(f"✓ [list_tags] Retrieved all {len(all_tag_names)} tags")
        
        import json
        return json.dumps(all_tag_names, ensure_ascii=False)
        
    except PixelHubAPIError as e:
        logger.error(f"❌ [list_tags] API error: {e}")
        return f"API Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [list_tags] Exception: {e}")
        return f"Error: {str(e)}"


@tool("search_images_by_tags")
def search_images_by_tags(tags: List[str], n: int = 20) -> str:
    """Search images by tags using relevance ranking (OR logic). Returns the top n images that match any of the provided tags,
    sorted by number of matched tags. IMPORTANT: Only use tags that exist in the system (call list_tags first).
    
    Args:
        tags: List of tags to search for. MUST use tags from list_tags result.
        n: Number of results to return (default: 20)
    
    Returns:
        A JSON string containing search results with image URLs, descriptions, and matched tags.
    """
    logger.info(f"? [search_images_by_tags] Called - tags: {tags}, n: {n}")
    
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
        all_results = []
        page = 1
        limit = min(100, n)  # Use max allowed per page or requested n, whichever is smaller
        
        while len(all_results) < n:
            result = client.search_images(tags=tags, page=page, limit=limit)
            results = result.get("results", [])
            
            if not results:
                # No more results
                break
            
            all_results.extend(results)
            
            total = result.get("total", 0)
            logger.debug(f"Page {page}: Retrieved {len(results)} images (total so far: {len(all_results)}/{min(total, n)})")
            
            # Check if we have enough or no more results
            if len(all_results) >= n or len(results) < limit:
                break
            
            page += 1
        
        # Trim to exactly n results
        all_results = all_results[:n]
        
        response = {
            "results_count": len(all_results),
            "results": all_results
        }
        
        logger.info(f"✓ [search_images_by_tags] Returned {len(all_results)} images")
        
        import json
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except PixelHubAPIError as e:
        logger.error(f"❌ [search_images_by_tags] API error: {e}")
        return f"API Error: {str(e)}"
    except Exception as e:
        logger.error(f"❌ [search_images_by_tags] Exception: {e}")
        return f"Error: {str(e)}"
