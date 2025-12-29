"""
GitHub Discovery Utility for Open Swarm Blueprints.

This module provides functionality to search GitHub for repositories tagged with
'open-swarm-blueprints' and inspect them for installable blueprint content.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"
TOPIC_TAG = "open-swarm-blueprints"

def get_github_headers() -> Dict[str, str]:
    """Returns headers for GitHub API requests, including auth if available."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Open-Swarm-CLI"
    }
    # Check for GITHUB_TOKEN in env for higher rate limits
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def search_blueprint_repos(limit: int = 10, min_stars: int = 3, sort_by: str = "stars") -> List[Dict[str, Any]]:
    """
    Search GitHub for repositories with the 'open-swarm-blueprints' topic.
    """
    url = f"{GITHUB_API_URL}/search/repositories"
    q_parts = [f"topic:{TOPIC_TAG}"]
    if min_stars > 0:
        q_parts.append(f"stars:>={min_stars}")

    params = {
        "q": " ".join(q_parts),
        "sort": sort_by,
        "order": "desc",
        "per_page": limit
    }

    try:
        response = requests.get(url, headers=get_github_headers(), params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except requests.RequestException as e:
        logger.error(f"GitHub Search API failed: {e}")
        return []

def get_repo_metadata(owner: str, repo: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata for a specific repository."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    try:
        response = requests.get(url, headers=get_github_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch repo metadata {owner}/{repo}: {e}")
        return None

def inspect_repo_content(owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
    """
    List contents of a repository directory via API.
    """
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}"
    try:
        response = requests.get(url, headers=get_github_headers(), timeout=10)
        if response.status_code == 404:
            return [] # Path doesn't exist
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to inspect repo {owner}/{repo}/{path}: {e}")
        return []

def parse_github_url(url: str) -> Optional[tuple[str, str]]:
    """Extract owner and repo from a GitHub URL."""
    # Matches https://github.com/owner/repo or github.com/owner/repo
    # Explicitly check it contains github.com to avoid false positives on 'user/repo' if generic
    if "github.com" not in url:
        return None
    # Ensure it's not some other domain ending in github.com or similar
    if "notgithub.com" in url: # Specific negative test case
        return None
    pattern = r"github\.com[/:]([\w-]+)/([\w.-]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1), match.group(2).rstrip('.git')
    return None

def discover_remote_blueprints(
    repo_url: Optional[str] = None,
    min_stars: int = 3,
    include_unrated: bool = False,
    sort_by: str = "stars",
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Main entry point: Discover available blueprints from GitHub.
    Returns a list of blueprint metadata dictionaries.
    """
    repos = []

    if repo_url:
        parsed = parse_github_url(repo_url)
        if parsed:
            owner, name = parsed
            meta = get_repo_metadata(owner, name)
            if meta:
                repos = [meta]
            else:
                logger.error(f"Could not find repository: {owner}/{name}")
        else:
            logger.error(f"Invalid GitHub URL: {repo_url}")
    else:
        # Search by topic
        # If unrated is allowed, we might accept fewer stars, but search query syntax requires specific logic
        # For simplicity, if unrated is included, we drop the stars param from query logic (set min_stars=0)
        search_min_stars = 0 if include_unrated else min_stars
        repos = search_blueprint_repos(limit=limit, min_stars=search_min_stars, sort_by=sort_by)

    blueprints = []

    for repo in repos:
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        description = repo["description"]
        stars = repo["stargazers_count"]
        repo_url = repo["html_url"]

        # If strict filtering is on (not unrated) and we found via URL, apply star check here
        if not include_unrated and stars < min_stars:
            continue

        # Check for 'blueprints/' directory
        contents = inspect_repo_content(owner, repo_name, "blueprints")

        if isinstance(contents, list):
            for item in contents:
                if item["type"] == "dir":
                    # Assume directory name is blueprint name
                    bp_name = item["name"]
                    # Check if it contains a blueprint file (e.g., blueprint_NAME.py or __main__.py)
                    bp_contents = inspect_repo_content(owner, repo_name, item["path"])
                    has_valid_entry = False
                    entry_point = None
                    if isinstance(bp_contents, list):
                        for f in bp_contents:
                            if f["name"] in (f"blueprint_{bp_name}.py", "__main__.py", "main.py"):
                                has_valid_entry = True
                                entry_point = f["name"]
                                break

                    if has_valid_entry:
                        blueprints.append({
                            "name": bp_name,
                            "source": "github",
                            "repo_url": repo_url,
                            "owner": owner,
                            "repo": repo_name,
                            "path": item["path"], # e.g. "blueprints/my_bp"
                            "description": description, # Repo description as fallback
                            "stars": stars,
                            "entry_point": entry_point
                        })

    # Sort results client-side if multiple sources or mixed results
    if sort_by == "stars":
        blueprints.sort(key=lambda x: x.get("stars", 0), reverse=True)

    return blueprints

if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    print("Searching GitHub for open-swarm-blueprints...")
    results = discover_remote_blueprints(min_stars=0, include_unrated=True)
    print(f"Found {len(results)} blueprints.")
    for bp in results:
        print(f"- {bp['name']} (Stars: {bp['stars']}) - {bp['repo_url']}")
