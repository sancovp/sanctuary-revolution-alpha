#!/usr/bin/env python3
"""
SEED Membership Site Integration

This module provides tools for interacting with the SEED public membership site
hosted on Replit, including triggering content refreshes from the GitHub public branch.
"""

import requests
import logging
import os
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeedMembershipSite:
    """Manages interactions with the SEED public membership site."""
    
    def __init__(self, site_url: str = None):
        """
        Initialize the membership site integration.
        
        Args:
            site_url: URL of the SEED membership site (defaults to env var)
        """
        self.site_url = site_url or os.getenv('SEED_MEMBERSHIP_SITE_URL', '')
        
        if not self.site_url:
            logger.warning("SEED_MEMBERSHIP_SITE_URL not configured - refresh operations will fail")
        else:
            # Ensure URL doesn't end with slash for consistent API calls
            self.site_url = self.site_url.rstrip('/')
            logger.info(f"SEED membership site URL: {self.site_url}")
    
    def refresh_seed_membership_site(self) -> Dict[str, Any]:
        """
        Trigger a refresh of the SEED membership site from GitHub public branch.
        
        This hits the /api/refresh endpoint on the Replit site to force it to
        pull the latest content from the GitHub public branch immediately.
        
        Returns:
            Dict with refresh result status
        """
        if not self.site_url:
            return {
                "success": False,
                "error": "SEED membership site URL not configured",
                "message": "Set SEED_MEMBERSHIP_SITE_URL environment variable"
            }
        
        refresh_url = f"{self.site_url}/api/refresh"
        logger.info(f"Triggering SEED membership site refresh: {refresh_url}")
        
        try:
            response = requests.post(refresh_url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                logger.info("✅ SEED membership site refresh successful")
                return {
                    "success": True,
                    "message": result.get("message", "Refresh completed"),
                    "status_code": response.status_code
                }
            else:
                error_msg = f"Refresh failed with status {response.status_code}"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                    "response_text": response.text
                }
                
        except requests.exceptions.Timeout:
            error_msg = "Refresh request timed out after 30 seconds"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Refresh request failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def check_site_status(self) -> Dict[str, Any]:
        """
        Check if the SEED membership site is accessible.
        
        Returns:
            Dict with site status information
        """
        if not self.site_url:
            return {
                "accessible": False,
                "error": "Site URL not configured"
            }
        
        try:
            response = requests.get(f"{self.site_url}/api/stats", timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                logger.info("✅ SEED membership site is accessible")
                return {
                    "accessible": True,
                    "stats": stats,
                    "status_code": response.status_code
                }
            else:
                return {
                    "accessible": False,
                    "error": f"Site returned status {response.status_code}",
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "accessible": False,
                "error": f"Connection failed: {str(e)}"
            }
    
    def get_published_concepts(self) -> Dict[str, Any]:
        """
        Get list of concepts currently published on the membership site.
        
        Returns:
            Dict with published concept files
        """
        if not self.site_url:
            return {
                "success": False,
                "error": "Site URL not configured",
                "concepts": []
            }
        
        try:
            response = requests.get(f"{self.site_url}/api/concept-files", timeout=15)
            
            if response.status_code == 200:
                concepts = response.json()
                logger.info(f"✅ Retrieved {len(concepts)} published concepts from membership site")
                return {
                    "success": True,
                    "concepts": concepts,
                    "count": len(concepts)
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get concepts: status {response.status_code}",
                    "concepts": []
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "concepts": []
            }


# Global instance for easy importing
seed_membership_site = SeedMembershipSite()

# Convenience function for direct usage
def refresh_seed_membership_site() -> Dict[str, Any]:
    """
    Convenience function to refresh the SEED membership site.
    
    Returns:
        Dict with refresh result status
    """
    return seed_membership_site.refresh_seed_membership_site()


def main():
    """Test the SEED membership site integration."""
    print("SEED Membership Site Integration Test")
    print("=" * 50)
    
    # Test site URL configuration
    site_url = os.getenv('SEED_MEMBERSHIP_SITE_URL', 'https://example-replit-url.replit.app')
    site = SeedMembershipSite(site_url)
    
    print(f"Site URL: {site.site_url}")
    
    # Test site accessibility
    print("\n1. Checking site status...")
    status = site.check_site_status()
    print(f"Accessible: {status.get('accessible', False)}")
    if status.get('stats'):
        stats = status['stats']
        print(f"Published files: {stats.get('totalFiles', 'N/A')}")
        print(f"Last updated: {stats.get('lastUpdated', 'N/A')}")
    
    # Test getting published concepts
    print("\n2. Getting published concepts...")
    concepts_result = site.get_published_concepts()
    if concepts_result['success']:
        print(f"Found {concepts_result['count']} published concepts")
        for concept in concepts_result['concepts'][:3]:  # Show first 3
            print(f"  - {concept['name']} ({concept['size']} bytes)")
    else:
        print(f"Failed to get concepts: {concepts_result['error']}")
    
    # Test refresh
    print("\n3. Testing refresh...")
    refresh_result = site.refresh_seed_membership_site()
    print(f"Refresh success: {refresh_result.get('success', False)}")
    print(f"Message: {refresh_result.get('message', refresh_result.get('error', 'N/A'))}")
    
    print("\nTest completed!")


if __name__ == "__main__":
    main()