from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TwitterUser(BaseModel):
    user_id: str
    name: str
    screen_name: str
    bio: Optional[str] = None
    location: Optional[str] = None
    followers: int
    following: int
    tweets: int
    favorites: int
    private: bool = False
    verified: bool = False
    avatar: Optional[str] = None
    created: Optional[str] = None


class UserSearchResult(BaseModel):
    users: List[TwitterUser]
    metadata: dict


class FollowingUser(BaseModel):
    id: str
    name: str
    username: str
    followers: int
    following: int
    url: str = ""
    tweets: int
    profile_image_url_https: Optional[str] = None
    created: Optional[str] = None


class FollowingResult(BaseModel):
    users: List[FollowingUser]
    metadata: dict


class Tweet(BaseModel):
    id: str
    user_id: str
    date: str
    tweets: str
    screen_name: str
    name: str
    retweet: int
    replies: int
    link_media: str = ""
    likes: int
    link: str
    views: int
    quote: int
    engagement: float
    hashtags: List[str]
    mentions: List[str]
    source: str


class HashtagAnalysis(BaseModel):
    hashtags: str
    count: int
    percentage: float


class MentionAnalysis(BaseModel):
    user_mention: str
    count: int
    percentage: float


class TimelineResult(BaseModel):
    timelines: List[Tweet]
    hashtags: List[HashtagAnalysis]
    mentions: List[MentionAnalysis]
    metadata: dict


# Request schemas
class UserSearchRequest(BaseModel):
    q: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(20, ge=1, le=100, description="Number of results")


class UserFollowingRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Twitter username")
    limit: int = Field(20, ge=1, le=100, description="Number of results")


class UserFollowersRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Twitter username")
    limit: int = Field(20, ge=1, le=100, description="Number of results")


class TimelineRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Twitter username")
    count: int = Field(80, ge=20, le=100, description="Number of tweets to analyze")
    include_analysis: bool = Field(True, description="Include hashtag/mention analysis")
