#!/usr/bin/env python3
"""
LinkedIn API Integration for LinkedIn Posting Automation

Implements official LinkedIn API integration for post publishing and management
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

import requests
import structlog
from requests_oauthlib import OAuth2Session

logger = structlog.get_logger()


class PostStatus(Enum):
    """Status of a LinkedIn post"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class MediaType(Enum):
    """Types of media attachments"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"


@dataclass
class MediaAsset:
    """Media asset for LinkedIn posts"""
    asset_id: str
    media_type: MediaType
    url: str
    alt_text: Optional[str] = None
    description: Optional[str] = None


@dataclass
class LinkedInPost:
    """Structure for a LinkedIn post"""
    id: str
    author_urn: str  # URN of the author (person or organization)
    text: str
    visibility: str = "PUBLIC"  # PUBLIC, CONNECTIONS_ONLY
    media_assets: List[MediaAsset] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_time: Optional[datetime] = None
    status: PostStatus = PostStatus.DRAFT
    engagement_metrics: Dict[str, int] = field(default_factory=dict)
    external_id: Optional[str] = None  # LinkedIn's post ID after publishing


@dataclass
class LinkedInProfile:
    """LinkedIn profile information"""
    urn: str
    name: str
    type: str  # "PERSON" or "ORGANIZATION"
    vanity_name: str
    description: Optional[str] = None
    followers_count: Optional[int] = None


class LinkedInAPIError(Exception):
    """Custom exception for LinkedIn API errors"""
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class LinkedInAPIIntegration:
    """Main class for LinkedIn API integration"""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, scopes: List[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or ["w_member_social", "w_organization_social"]

        # LinkedIn API endpoints
        self.base_url = "https://api.linkedin.com/v2"
        self.auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        self.token_url = "https://www.linkedin.com/oauth/v2/accessToken"

        self.oauth_session: Optional[OAuth2Session] = None
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        self.logger = logger.bind(component="LinkedInAPIIntegration")

    def initiate_oauth_flow(self) -> str:
        """Initiate OAuth 2.0 flow to get authorization URL"""
        self.oauth_session = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scopes
        )

        authorization_url, state = self.oauth_session.authorization_url(
            self.auth_url,
            state=os.urandom(32).hex()
        )

        self.logger.info("OAuth authorization URL generated", url=authorization_url)
        return authorization_url

    def complete_oauth_flow(self, authorization_code: str) -> Dict[str, str]:
        """Complete OAuth 2.0 flow with authorization code"""
        if not self.oauth_session:
            raise LinkedInAPIError("OAuth session not initialized. Call initiate_oauth_flow first.")

        token = self.oauth_session.fetch_token(
            self.token_url,
            client_secret=self.client_secret,
            authorization_response=f"{self.redirect_uri}?code={authorization_code}"
        )

        self.access_token = token.get('access_token')
        expires_in = token.get('expires_in', 0)
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

        self.logger.info("OAuth flow completed successfully", scopes=self.scopes)
        return token

    def set_access_token(self, access_token: str, expires_in: int = 3600):
        """Set access token directly (for cases where token is obtained externally)"""
        self.access_token = access_token
        self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

        # Initialize OAuth session with the token
        token_dict = {'access_token': access_token, 'token_type': 'Bearer'}
        self.oauth_session = OAuth2Session(
            client_id=self.client_id,
            token=token_dict,
            redirect_uri=self.redirect_uri
        )

        self.logger.info("Access token set successfully")

    def _ensure_token_valid(self):
        """Ensure the access token is valid, refresh if necessary"""
        if not self.access_token:
            raise LinkedInAPIError("No access token available. Authenticate first.")

        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            raise LinkedInAPIError("Access token has expired. Re-authenticate.")

    def _make_api_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an authenticated API request to LinkedIn"""
        self._ensure_token_valid()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
            'Content-Type': 'application/json'
        }

        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
            del kwargs['headers']

        response = requests.request(method, url, headers=headers, **kwargs)

        if response.status_code == 401:
            raise LinkedInAPIError("Unauthorized. Access token may be invalid or expired.", 401)
        elif response.status_code == 429:
            # Rate limit exceeded
            retry_after = response.headers.get('Retry-After', 60)
            self.logger.warning("Rate limit exceeded, waiting", retry_after=retry_after)
            time.sleep(int(retry_after))
            return self._make_api_request(method, endpoint, **kwargs)
        elif response.status_code >= 400:
            error_msg = response.text
            try:
                error_json = response.json()
                error_msg = error_json.get('message', error_msg)
            except:
                pass
            raise LinkedInAPIError(
                f"API request failed: {error_msg}",
                response.status_code,
                response.json() if response.content else None
            )

        try:
            return response.json() if response.content else {}
        except ValueError:
            # If response is not JSON, return the text content
            return {'content': response.text}

    def get_current_profile(self) -> LinkedInProfile:
        """Get the current authenticated user's profile"""
        # Get user info from LinkedIn
        user_info = self._make_api_request('GET', '/me')

        profile = LinkedInProfile(
            urn=f"urn:li:person:{user_info.get('id', '')}",
            name=f"{user_info.get('firstName', {}).get('localized', {}).get('en_US', '')} {user_info.get('lastName', {}).get('localized', {}).get('en_US', '')}".strip(),
            type="PERSON",
            vanity_name=user_info.get('vanityName', ''),
            description=None
        )

        self.logger.info("Current profile retrieved", profile_urn=profile.urn)
        return profile

    def get_organization_profiles(self) -> List[LinkedInProfile]:
        """Get organization profiles the user has admin rights to"""
        # Get organizations the user is an admin of
        orgs_response = self._make_api_request(
            'GET',
            '/organizationAcls',
            params={
                'q': 'roleAssignee',
                'role': 'ADMINISTRATOR',
                'projection': '(elements*(organization~(localizedName,vanityName,id)))'
            }
        )

        profiles = []
        for element in orgs_response.get('elements', []):
            org_data = element.get('organization~', {})
            profile = LinkedInProfile(
                urn=f"urn:li:organization:{org_data.get('id', '')}",
                name=org_data.get('localizedName', ''),
                type="ORGANIZATION",
                vanity_name=org_data.get('vanityName', ''),
                followers_count=element.get('followerCount', 0)
            )
            profiles.append(profile)

        self.logger.info("Organization profiles retrieved", count=len(profiles))
        return profiles

    def upload_media_asset(self, file_path: str, media_type: MediaType, owner_urn: str) -> str:
        """Upload a media asset to LinkedIn"""
        # Step 1: Initialize the upload
        upload_request = {
            "initializeUploadRequest": {
                "owner": owner_urn,
                "uploadCaptions": ["en_US:Upload Caption"]
            }
        }

        response = self._make_api_request(
            'POST',
            '/assets?action=initializeUpload',
            json=upload_request
        )

        asset_id = response.get('value', {}).get('asset', '')
        upload_url = response.get('value', {}).get('uploadUrl', '')

        if not asset_id or not upload_url:
            raise LinkedInAPIError("Failed to initialize media upload")

        # Step 2: Upload the file to LinkedIn's servers
        with open(file_path, 'rb') as f:
            file_content = f.read()

        upload_headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/octet-stream'
        }

        upload_response = requests.put(upload_url, data=file_content, headers=upload_headers)

        if upload_response.status_code != 201:
            raise LinkedInAPIError(f"Failed to upload media: {upload_response.text}", upload_response.status_code)

        self.logger.info("Media asset uploaded successfully", asset_id=asset_id, file_path=file_path)
        return asset_id

    def create_post(self, linkedin_post: LinkedInPost) -> str:
        """Create and publish a post on LinkedIn"""
        # Prepare the post content
        post_content = {
            "author": linkedin_post.author_urn,
            "lifecycleState": "PUBLISHED" if not linkedin_post.scheduled_time else "DRAFT",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": linkedin_post.text
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": linkedin_post.visibility
            }
        }

        # Add media if present
        if linkedin_post.media_assets:
            media_values = []
            for media_asset in linkedin_post.media_assets:
                media_values.append({
                    "status": "READY",
                    "description": {
                        "text": media_asset.alt_text or "Media attachment"
                    },
                    "visibility": "PUBLIC",
                    "originalUrl": media_asset.url,
                    "mediaType": media_asset.media_type.value
                })

            post_content["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
            post_content["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_values

        # Handle scheduled posts
        if linkedin_post.scheduled_time:
            post_content["distribution"] = {
                "feedDistribution": "MAIN_FEED",
                "targetEnties": [],
                "thirdPartyDistributionChannels": []
            }
            post_content["state"] = "SCHEDULED"
            post_content["scheduledPublishTime"] = linkedin_post.scheduled_time.isoformat() + "Z"
        else:
            post_content["distribution"] = {
                "feedDistribution": "MAIN_FEED",
                "targetEnties": [],
                "thirdPartyDistributionChannels": []
            }

        # Create the post
        response = self._make_api_request(
            'POST',
            '/ugcPosts',
            json=post_content
        )

        post_urn = response.get('id', '')
        if not post_urn:
            raise LinkedInAPIError("Failed to create post - no ID returned", None, response)

        # Update the post object with the external ID
        linkedin_post.external_id = post_urn
        linkedin_post.status = PostStatus.SCHEDULED if linkedin_post.scheduled_time else PostStatus.PUBLISHED

        self.logger.info("Post created successfully", post_urn=post_urn, status=linkedin_post.status.value)
        return post_urn

    def update_post(self, post_urn: str, updated_content: Dict[str, Any]) -> bool:
        """Update an existing LinkedIn post"""
        # LinkedIn doesn't allow updating published posts, only certain properties
        # This is a limitation of the LinkedIn API
        raise NotImplementedError("LinkedIn API does not allow updating published posts")

    def delete_post(self, post_urn: str) -> bool:
        """Delete a LinkedIn post"""
        try:
            self._make_api_request('DELETE', f'/ugcPosts/{post_urn}')
            self.logger.info("Post deleted successfully", post_urn=post_urn)
            return True
        except LinkedInAPIError as e:
            self.logger.error("Failed to delete post", post_urn=post_urn, error=str(e))
            return False

    def get_post_engagement(self, post_urn: str) -> Dict[str, int]:
        """Get engagement metrics for a post"""
        # Get social actions (likes, comments, shares)
        engagement_response = self._make_api_request(
            'GET',
            f'/socialActions/{post_urn}/statistics',
            params={'q': 'reference'}
        )

        metrics = {
            'likes': engagement_response.get('likes', 0),
            'comments': engagement_response.get('comments', 0),
            'shares': engagement_response.get('reshares', 0),
            'impressions': engagement_response.get('impressionCount', 0)
        }

        self.logger.info("Engagement metrics retrieved", post_urn=post_urn, metrics=metrics)
        return metrics

    def get_recent_posts(self, author_urn: str, count: int = 10) -> List[LinkedInPost]:
        """Get recent posts from a specific author"""
        # This is a simplified implementation - the actual LinkedIn API for retrieving
        # posts from an author is complex and varies based on context
        # For a full implementation, we would need to use the Analytics API

        # Placeholder implementation returning empty list
        # In a real implementation, this would connect to LinkedIn's feed API
        self.logger.info("Retrieving recent posts", author_urn=author_urn, count=count)
        return []

    def get_my_posts(self) -> List[LinkedInPost]:
        """Get posts published by the authenticated user"""
        # Get current user profile
        profile = self.get_current_profile()

        # Get user's posts (this is a simplified approach)
        # In reality, LinkedIn's API makes it difficult to retrieve all posts by a user
        # This would require using the Analytics API or other methods
        self.logger.info("Retrieving user's posts", profile_urn=profile.urn)
        return []


class LinkedInPostManager:
    """Manager class for handling LinkedIn post operations"""

    def __init__(self, api_integration: LinkedInAPIIntegration):
        self.api = api_integration
        self.logger = logger.bind(component="LinkedInPostManager")

    def create_draft_post(self,
                         author_urn: str,
                         text: str,
                         visibility: str = "PUBLIC",
                         media_files: List[str] = None,
                         scheduled_time: Optional[datetime] = None) -> LinkedInPost:
        """Create a draft LinkedIn post"""
        post_id = f"post_{int(time.time())}_{hash(text) % 10000}"

        # Upload media if provided
        media_assets = []
        if media_files:
            for file_path in media_files:
                # For simplicity, we'll assume the file is already uploaded and we have a URL
                # In a real implementation, we would upload the files to LinkedIn
                media_type = MediaType.IMAGE  # Simplified assumption
                asset = MediaAsset(
                    asset_id=f"asset_{hash(file_path)}",
                    media_type=media_type,
                    url=file_path,  # This would be the actual uploaded URL
                    alt_text=f"Image for post {post_id}"
                )
                media_assets.append(asset)

        draft_post = LinkedInPost(
            id=post_id,
            author_urn=author_urn,
            text=text,
            visibility=visibility,
            media_assets=media_assets,
            scheduled_time=scheduled_time,
            status=PostStatus.DRAFT
        )

        self.logger.info("Draft post created", post_id=draft_post.id)
        return draft_post

    def submit_for_approval(self, post: LinkedInPost) -> LinkedInPost:
        """Submit a post for approval"""
        post.status = PostStatus.PENDING_APPROVAL
        self.logger.info("Post submitted for approval", post_id=post.id)
        return post

    def approve_post(self, post: LinkedInPost) -> LinkedInPost:
        """Approve a post"""
        if post.status != PostStatus.PENDING_APPROVAL:
            raise ValueError(f"Post {post.id} is not pending approval")

        post.status = PostStatus.APPROVED
        self.logger.info("Post approved", post_id=post.id)
        return post

    def reject_post(self, post: LinkedInPost, reason: str = "") -> LinkedInPost:
        """Reject a post"""
        if post.status != PostStatus.PENDING_APPROVAL:
            raise ValueError(f"Post {post.id} is not pending approval")

        post.status = PostStatus.REJECTED
        self.logger.info("Post rejected", post_id=post.id, reason=reason)
        return post

    def publish_approved_post(self, post: LinkedInPost) -> LinkedInPost:
        """Publish an approved post to LinkedIn"""
        if post.status != PostStatus.APPROVED:
            raise ValueError(f"Post {post.id} is not approved for publishing")

        try:
            # Publish the post via API
            post_urn = self.api.create_post(post)
            post.external_id = post_urn

            if post.scheduled_time:
                post.status = PostStatus.SCHEDULED
                self.logger.info("Post scheduled", post_id=post.id, scheduled_time=post.scheduled_time)
            else:
                post.status = PostStatus.PUBLISHED
                self.logger.info("Post published", post_id=post.id, post_urn=post_urn)

        except LinkedInAPIError as e:
            post.status = PostStatus.FAILED
            self.logger.error("Post publishing failed", post_id=post.id, error=str(e))
            raise

        return post

    def get_post_status(self, post: LinkedInPost) -> Dict[str, Any]:
        """Get the current status and engagement of a post"""
        if not post.external_id:
            return {"status": post.status.value, "engagement": {}}

        try:
            engagement = self.api.get_post_engagement(post.external_id)
            return {
                "status": post.status.value,
                "engagement": engagement
            }
        except LinkedInAPIError as e:
            self.logger.error("Failed to get post status", post_id=post.id, error=str(e))
            return {
                "status": post.status.value,
                "engagement": {},
                "error": str(e)
            }


# Convenience functions
def create_linkedin_api_integration(config: Dict[str, Any]) -> LinkedInAPIIntegration:
    """Create and configure a LinkedIn API integration from config"""
    return LinkedInAPIIntegration(
        client_id=config["linkedin"]["oauth_client_id"],
        client_secret=config["linkedin"]["oauth_client_secret"],
        redirect_uri=config["linkedin"]["redirect_uri"],
        scopes=config["linkedin"].get("scopes", ["w_member_social"])
    )


def demo_linkedin_integration():
    """Demo function to show LinkedIn API integration usage"""
    print("LinkedIn API Integration Demo")
    print("=" * 40)

    # This would normally be configured with real credentials
    # For demo purposes, we'll show the usage pattern
    print("Note: This demo shows the usage pattern but requires real LinkedIn API credentials")
    print("to actually connect to LinkedIn API")

    # Example usage (without actual API calls):
    print("\nExample usage:")
    print("# Initialize API integration")
    print("api = LinkedInAPIIntegration(client_id='...', client_secret='...', redirect_uri='...')")
    print("# Get authorization URL")
    print("auth_url = api.initiate_oauth_flow()")
    print("# After user authorizes, complete the flow")
    print("# api.complete_oauth_flow(authorization_code)")
    print("# Or set token directly if already obtained")
    print("# api.set_access_token(access_token)")

    print("\n# Create post manager")
    print("post_manager = LinkedInPostManager(api)")

    print("\n# Create a draft post")
    print("draft = post_manager.create_draft_post(")
    print("    author_urn='urn:li:person:...',")
    print("    text='Hello, LinkedIn!',")
    print("    visibility='PUBLIC'")
    print(")")

    print("\n# Submit for approval")
    print("submitted = post_manager.submit_for_approval(draft)")

    print("\n# Approve the post")
    print("approved = post_manager.approve_post(submitted)")

    print("\n# Publish the approved post")
    print("published = post_manager.publish_approved_post(approved)")
    print("print(f'Post published with ID: {published.external_id}')")


if __name__ == "__main__":
    demo_linkedin_integration()