"""Supabase persistence layer for projects, sessions, and chat turns."""

import json
import logging
from datetime import datetime, timezone

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def save_user_project(
    user_id: str,
    project_id: str,
    slug: str,
    project_root: str,
    github_url: str | None = None,
    total_files: int = 0,
) -> dict | None:
    """Save or upsert a project for a user."""
    try:
        sb = get_supabase()
        data = {
            "id": project_id,
            "user_id": user_id,
            "slug": slug,
            "project_root": project_root,
            "github_url": github_url,
            "total_files": total_files,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
            "last_accessed_at": datetime.now(timezone.utc).isoformat(),
        }
        result = sb.table("projects").upsert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("Failed to save project: %s", e)
        return None


def list_user_projects(user_id: str) -> list[dict]:
    """List all projects for a user, ordered by last accessed."""
    try:
        sb = get_supabase()
        result = (
            sb.table("projects")
            .select("*")
            .eq("user_id", user_id)
            .order("last_accessed_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error("Failed to list projects: %s", e)
        return []


def delete_user_project(user_id: str, project_id: str) -> bool:
    """Delete a project and its sessions/turns (cascades)."""
    try:
        sb = get_supabase()
        sb.table("projects").delete().eq("id", project_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error("Failed to delete project: %s", e)
        return False


def touch_project(project_id: str) -> None:
    """Update last_accessed_at for a project."""
    try:
        sb = get_supabase()
        sb.table("projects").update(
            {"last_accessed_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", project_id).execute()
    except Exception as e:
        logger.error("Failed to touch project: %s", e)


def ensure_session(user_id: str, project_id: str, session_id: str) -> dict | None:
    """Create a session if it doesn't exist, return it."""
    try:
        sb = get_supabase()
        # Check if session exists
        existing = sb.table("sessions").select("*").eq("id", session_id).execute()
        if existing.data:
            # Update last_message_at
            sb.table("sessions").update(
                {"last_message_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", session_id).execute()
            return existing.data[0]
        # Create new session (title column may not exist yet)
        data = {
            "id": session_id,
            "user_id": user_id,
            "project_id": project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_message_at": datetime.now(timezone.utc).isoformat(),
        }
        result = sb.table("sessions").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("Failed to ensure session: %s", e)
        return None


def get_project_by_slug(user_id: str, slug: str) -> dict | None:
    """Look up a project by slug for a user."""
    try:
        sb = get_supabase()
        result = (
            sb.table("projects")
            .select("*")
            .eq("user_id", user_id)
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("Failed to get project by slug: %s", e)
        return None


def list_project_sessions(user_id: str, project_id: str) -> list[dict]:
    """List all sessions for a user's project."""
    try:
        sb = get_supabase()
        result = (
            sb.table("sessions")
            .select("*")
            .eq("user_id", user_id)
            .eq("project_id", project_id)
            .order("last_message_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error("Failed to list sessions: %s", e)
        return []


def update_session_title(session_id: str, title: str) -> None:
    """Set the title for a session (auto-generated from first question)."""
    try:
        sb = get_supabase()
        sb.table("sessions").update({"title": title}).eq("id", session_id).execute()
    except Exception as e:
        logger.error("Failed to update session title: %s", e)


def delete_session(user_id: str, session_id: str) -> bool:
    """Delete a session and its turns."""
    try:
        sb = get_supabase()
        # Delete turns first, then session
        sb.table("turns").delete().eq("session_id", session_id).execute()
        sb.table("sessions").delete().eq("id", session_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error("Failed to delete session: %s", e)
        return False


def save_chat_turn(
    session_id: str,
    turn_index: int,
    question: str,
    answer: str,
    relevant_files: list[str] | None = None,
) -> dict | None:
    """Save a single Q&A turn to Supabase."""
    try:
        sb = get_supabase()
        data = {
            "session_id": session_id,
            "turn_index": turn_index,
            "question": question,
            "answer": answer,
            "relevant_files": json.dumps(relevant_files or []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = sb.table("turns").upsert(
            data, on_conflict="session_id,turn_index"
        ).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("Failed to save chat turn: %s", e)
        return None


def load_chat_history(session_id: str) -> list[dict]:
    """Load all turns for a session, ordered by turn_index."""
    try:
        sb = get_supabase()
        result = (
            sb.table("turns")
            .select("turn_index, question, answer, relevant_files, created_at")
            .eq("session_id", session_id)
            .order("turn_index")
            .execute()
        )
        turns = result.data or []
        # Parse relevant_files JSON strings back to lists
        for turn in turns:
            if isinstance(turn.get("relevant_files"), str):
                turn["relevant_files"] = json.loads(turn["relevant_files"])
        return turns
    except Exception as e:
        logger.error("Failed to load chat history: %s", e)
        return []
