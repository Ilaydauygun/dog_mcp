from fastmcp import FastMCP, Context
import httpx
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import asyncio
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("DogMCP")

# HTTP client with timeout
client = httpx.AsyncClient(timeout=10.0)

# API configuration
DOG_API_BASE_URL = "https://api.thedogapi.com/v1"
API_KEY = os.getenv("DOG_API_KEY")

@mcp.tool()
async def get_random_dog_image(
    breed_id: Optional[str] = None,
    category_ids: Optional[str] = None,
    format: str = "json",
    limit: int = 1
) -> str:
    """
    Get random dog images with optional breed and category filtering.

    Args:
        breed_id: Optional breed ID to filter by specific breed
        category_ids: Optional category IDs (comma-separated) to filter by
        format: Response format (json or src)
        limit: Number of images to return (1-10)

    Returns:
        JSON string with dog image data
    """
    try:
        # Validate limit
        if limit < 1 or limit > 10:
            limit = 1

        params = {
            "limit": limit,
            "format": format
        }

        if breed_id:
            params["breed_ids"] = breed_id
        if category_ids:
            params["category_ids"] = category_ids

        headers = {}
        if API_KEY:
            headers["x-api-key"] = API_KEY

        response = await client.get(
            f"{DOG_API_BASE_URL}/images/search",
            params=params,
            headers=headers
        )

        if response.status_code == 200:
            data = response.json()

            # Format response for better readability
            result = {
                "status": "success",
                "count": len(data),
                "images": []
            }

            for img in data:
                image_info = {
                    "id": img.get("id"),
                    "url": img.get("url"),
                    "width": img.get("width"),
                    "height": img.get("height")
                }

                # Include breed information if available
                if "breeds" in img and img["breeds"]:
                    breed = img["breeds"][0]
                    image_info["breed"] = {
                        "name": breed.get("name"),
                        "temperament": breed.get("temperament"),
                        "life_span": breed.get("life_span"),
                        "weight": breed.get("weight", {}).get("metric", "Unknown"),
                        "height": breed.get("height", {}).get("metric", "Unknown")
                    }

                result["images"].append(image_info)

            return json.dumps(result, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": f"API request failed with status {response.status_code}",
                "details": response.text
            }, indent=2)

    except httpx.TimeoutException:
        return json.dumps({
            "status": "error",
            "message": "Request timeout - The Dog API took too long to respond",
            "suggestion": "Please try again in a moment"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, indent=2)

@mcp.tool()
async def get_dog_breeds(
    limit: int = 10,
    page: int = 0,
    search: Optional[str] = None
) -> str:
    """
    Get list of dog breeds with detailed information.

    Args:
        limit: Number of breeds to return (1-100)
        page: Page number for pagination
        search: Search term to filter breeds by name

    Returns:
        JSON string with breed information
    """
    try:
        # Validate parameters
        if limit < 1 or limit > 100:
            limit = 10
        if page < 0:
            page = 0

        params = {
            "limit": limit,
            "page": page
        }

        if search:
            params["q"] = search

        headers = {}
        if API_KEY:
            headers["x-api-key"] = API_KEY

        response = await client.get(
            f"{DOG_API_BASE_URL}/breeds",
            params=params,
            headers=headers
        )

        if response.status_code == 200:
            breeds = response.json()

            result = {
                "status": "success",
                "count": len(breeds),
                "page": page,
                "breeds": []
            }

            for breed in breeds:
                breed_info = {
                    "id": breed.get("id"),
                    "name": breed.get("name"),
                    "temperament": breed.get("temperament"),
                    "life_span": breed.get("life_span"),
                    "alt_names": breed.get("alt_names", ""),
                    "wikipedia_url": breed.get("wikipedia_url"),
                    "origin": breed.get("origin", "Unknown"),
                    "weight_metric": breed.get("weight", {}).get("metric", "Unknown"),
                    "height_metric": breed.get("height", {}).get("metric", "Unknown"),
                    "bred_for": breed.get("bred_for", "Unknown"),
                    "breed_group": breed.get("breed_group", "Unknown"),
                    "reference_image_id": breed.get("reference_image_id")
                }
                result["breeds"].append(breed_info)

            return json.dumps(result, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": f"Failed to fetch breeds with status {response.status_code}",
                "details": response.text
            }, indent=2)

    except httpx.TimeoutException:
        return json.dumps({
            "status": "error",
            "message": "Request timeout while fetching dog breeds",
            "suggestion": "Please try again with a smaller limit or check your connection"
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error fetching dog breeds: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, indent=2)

@mcp.tool()
async def search_dog_images(
    breed_name: str,
    limit: int = 5,
    has_breeds: bool = True
) -> str:
    """
    Search for dog images by breed name.

    Args:
        breed_name: Name of the dog breed to search for
        limit: Number of images to return (1-10)
        has_breeds: Whether to include breed information

    Returns:
        JSON string with search results
    """
    try:
        # First, find the breed ID
        breed_response = await client.get(
            f"{DOG_API_BASE_URL}/breeds/search",
            params={"q": breed_name},
            headers={"x-api-key": API_KEY} if API_KEY else {}
        )

        if breed_response.status_code != 200:
            return json.dumps({
                "status": "error",
                "message": f"Failed to search for breed '{breed_name}'",
                "suggestion": "Check the breed name spelling or try a different breed"
            }, indent=2)

        breeds = breed_response.json()
        if not breeds:
            return json.dumps({
                "status": "error",
                "message": f"No breeds found matching '{breed_name}'",
                "suggestion": "Try searching for popular breeds like 'Golden Retriever', 'Labrador', 'Poodle'"
            }, indent=2)

        breed_id = breeds[0]["id"]

        # Now search for images of this breed
        params = {
            "breed_ids": breed_id,
            "limit": min(max(1, limit), 10),
            "has_breeds": 1 if has_breeds else 0
        }

        response = await client.get(
            f"{DOG_API_BASE_URL}/images/search",
            params=params,
            headers={"x-api-key": API_KEY} if API_KEY else {}
        )

        if response.status_code == 200:
            images = response.json()

            result = {
                "status": "success",
                "breed_searched": breed_name,
                "breed_found": breeds[0]["name"],
                "count": len(images),
                "images": []
            }

            for img in images:
                image_info = {
                    "id": img.get("id"),
                    "url": img.get("url"),
                    "width": img.get("width"),
                    "height": img.get("height")
                }

                if "breeds" in img and img["breeds"]:
                    breed = img["breeds"][0]
                    image_info["breed_details"] = {
                        "name": breed.get("name"),
                        "temperament": breed.get("temperament"),
                        "bred_for": breed.get("bred_for"),
                        "life_span": breed.get("life_span")
                    }

                result["images"].append(image_info)

            return json.dumps(result, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": f"Failed to fetch images for {breed_name}",
                "details": response.text
            }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error searching for {breed_name} images: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, indent=2)

@mcp.tool()
async def check_dog_api_status() -> str:
    """
    Check the status and configuration of The Dog API connection.

    Returns:
        JSON string with API status information
    """
    try:
        # Test basic API connectivity
        response = await client.get(f"{DOG_API_BASE_URL}/images/search?limit=1")

        result = {
            "timestamp": datetime.now().isoformat(),
            "api_status": "unknown",
            "api_key_configured": bool(API_KEY),
            "base_url": DOG_API_BASE_URL,
            "connectivity": "unknown",
            "configuration": {
                "timeout": "10 seconds",
                "max_images_per_request": 10,
                "supported_formats": ["json", "src"]
            }
        }

        if response.status_code == 200:
            result["api_status"] = "operational"
            result["connectivity"] = "successful"

            # Test with API key if available
            if API_KEY:
                auth_response = await client.get(
                    f"{DOG_API_BASE_URL}/breeds",
                    headers={"x-api-key": API_KEY}
                )
                result["api_key_status"] = "valid" if auth_response.status_code == 200 else "invalid"
            else:
                result["api_key_status"] = "not_configured"
                result["note"] = "API key not set. Some features may be limited."

        else:
            result["api_status"] = "error"
            result["connectivity"] = f"failed_with_status_{response.status_code}"
            result["error_details"] = response.text

        # Add troubleshooting tips
        result["troubleshooting"] = {
            "api_key_setup": "Set DOG_API_KEY environment variable",
            "get_api_key": "Visit https://thedogapi.com to get a free API key",
            "common_issues": [
                "Check internet connection",
                "Verify API key is correct",
                "Ensure rate limits are not exceeded"
            ]
        }

        return json.dumps(result, indent=2)

    except httpx.TimeoutException:
        return json.dumps({
            "status": "error",
            "message": "Connection timeout to The Dog API",
            "troubleshooting": {
                "suggestions": [
                    "Check your internet connection",
                    "Try again in a few moments",
                    "Verify The Dog API is operational"
                ]
            },
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to check API status: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, indent=2)

@mcp.resource("config://dog-api")
async def dog_api_config(context: Context) -> str:
    """
    Returns configuration information for The Dog API.
    """
    config = {
        "api_name": "The Dog API",
        "provider": "That API Company",
        "base_url": DOG_API_BASE_URL,
        "documentation": "https://docs.thedogapi.com/",
        "features": {
            "random_images": "Get random dog images with breed filtering",
            "breed_search": "Search and list dog breeds with detailed info",
            "image_search": "Find images by specific breed name",
            "breed_info": "Detailed breed characteristics and temperament"
        },
        "authentication": {
            "type": "API Key",
            "header": "x-api-key",
            "required": "Optional (some features limited without key)",
            "signup": "https://thedogapi.com"
        },
        "rate_limits": {
            "free_tier": "1000 requests per month",
            "with_api_key": "Higher limits available"
        },
        "supported_formats": ["json", "src"],
        "max_images_per_request": 10,
        "setup_instructions": [
            "1. Visit https://thedogapi.com",
            "2. Sign up for a free account",
            "3. Get your API key from the dashboard",
            "4. Set DOG_API_KEY environment variable",
            "5. Restart the MCP server"
        ]
    }

    return json.dumps(config, indent=2)

@mcp.resource("data://popular-breeds")
async def popular_dog_breeds(context: Context) -> str:
    """
    Returns a list of popular dog breeds for testing and examples.
    """
    breeds_data = {
        "popular_breeds": [
            {"name": "Golden Retriever", "id": "golden", "category": "Sporting"},
            {"name": "Labrador Retriever", "id": "labrador", "category": "Sporting"},
            {"name": "German Shepherd", "id": "german_shepherd", "category": "Herding"},
            {"name": "French Bulldog", "id": "french_bulldog", "category": "Non-Sporting"},
            {"name": "Bulldog", "id": "bulldog", "category": "Non-Sporting"},
            {"name": "Poodle", "id": "poodle", "category": "Non-Sporting"},
            {"name": "Beagle", "id": "beagle", "category": "Hound"},
            {"name": "Rottweiler", "id": "rottweiler", "category": "Working"},
            {"name": "Yorkshire Terrier", "id": "yorkshire_terrier", "category": "Toy"},
            {"name": "German Shorthaired Pointer", "id": "german_shorthaired_pointer", "category": "Sporting"}
        ],
        "usage_examples": {
            "get_random_image": "get_random_dog_image(breed_id='golden')",
            "search_breed": "get_dog_breeds(search='retriever')",
            "find_images": "search_dog_images(breed_name='German Shepherd')"
        },
        "categories": [
            "Sporting", "Hound", "Working", "Terrier",
            "Toy", "Non-Sporting", "Herding", "Misc"
        ],
        "note": "These are some of the most popular dog breeds. The API supports hundreds of breeds."
    }

    return json.dumps(breeds_data, indent=2)

# Server startup configuration
if __name__ == "__main__":
    # Minimal output for STDIO compatibility
    print("Starting Dog API MCP Server...", flush=True)

    # Check API key configuration
    if not API_KEY:
        print("Warning: DOG_API_KEY not set. Some features may be limited.", flush=True)
        print("Get your free API key at: https://thedogapi.com", flush=True)

    try:
        # Run the server
        mcp.run()
    except KeyboardInterrupt:
        print("\nShutting down Dog API MCP Server...", flush=True)
    except Exception as e:
        print(f"Server error: {e}", flush=True)
    finally:
        # Cleanup
        asyncio.create_task(client.aclose())