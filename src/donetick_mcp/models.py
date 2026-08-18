"""Pydantic models for Donetick API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Assignee(BaseModel):
    """Chore assignee model."""

    userId: int = Field(..., description="User ID of the assignee")


class Label(BaseModel):
    """Chore label model."""

    id: int = Field(..., description="Label ID")
    name: str = Field(..., description="Label name")
    color: str | None = Field(None, description="Label color (hex code)")
    created_by: int | None = Field(None, alias="createdBy", description="User ID who created the label")


class NotificationMetadata(BaseModel):
    """Notification configuration metadata."""

    nagging: bool = Field(default=False, description="Enable nagging notifications")
    predue: bool = Field(default=False, description="Enable pre-due notifications")


class ChoreUpdate(BaseModel):
    """Model for updating a chore."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Take out recycling",
                "description": "Biweekly recycling collection",
                "nextDueDate": "2025-11-17",
                "priority": 2,
                "points": 10,
                "isPrivate": False,
            }
        }
    )

    # Basic fields
    name: str | None = Field(None, min_length=1, max_length=200, description="Chore name")
    description: str | None = Field(None, description="Chore description")
    nextDueDate: str | None = Field(None, description="Next due date (ISO 8601)")

    # Scheduling
    frequencyType: str | None = Field(None, description="Frequency type (once, daily, weekly, etc)")
    frequency: int | None = Field(None, ge=1, description="Frequency value")
    frequencyMetadata: dict[str, Any] | None = Field(None, description="Frequency metadata (days, time, timezone, etc)")
    isRolling: bool | None = Field(None, description="Is rolling schedule")

    # Assignment
    assignStrategy: str | None = Field(None, description="Assignment strategy")
    assignees: list[dict[str, int]] | None = Field(None, description="List of assignees with userId")

    # Notifications
    notification: bool | None = Field(None, description="Enable notifications")
    notificationMetadata: dict[str, Any] | None = Field(
        None, description="Notification metadata (templates, nagging, predue)"
    )

    # Status & Priority
    isActive: bool | None = Field(None, description="Is chore active")
    priority: int | None = Field(None, ge=0, le=4, description="Priority (0=unset, 1=lowest, 4=highest)")

    # Gamification & Labels
    points: int | None = Field(None, ge=0, description="Points awarded for completion")
    labelsV2: list[dict[str, int]] | None = Field(None, description="List of labels with id")

    # Privacy & Approval
    isPrivate: bool | None = Field(None, description="Hide from other circle members")
    requireApproval: bool | None = Field(None, description="Requires approval to mark complete")

    # Completion & Deadline Settings
    completionWindow: int | None = Field(None, ge=0, description="SECONDS before due time for early completion")
    deadlineOffset: int | None = Field(None, ge=0, description="SECONDS after due time for grace period")

    # Subtasks (can be updated)
    subTasks: list[dict[str, Any]] | None = Field(None, description="List of subtasks with name and orderId")


class Chore(BaseModel):
    """Complete chore model as returned by the API."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Chore ID")
    name: str = Field(..., description="Chore name")
    description: str | None = Field(None, description="Chore description")
    frequencyType: str = Field(..., description="Frequency type (once, daily, weekly, etc)")
    frequency: int = Field(..., description="Frequency value")
    frequencyMetadata: dict[str, Any] | None = Field(None, description="Frequency metadata")
    nextDueDate: str | None = Field(None, description="Next due date (ISO 8601)")
    isRolling: bool = Field(default=False, description="Is rolling schedule")
    assignedTo: int | None = Field(None, description="User ID of assigned user")
    assignees: list[Assignee] = Field(default_factory=list, description="List of assignees")
    assignStrategy: str = Field(
        default="least_completed",
        description="Assignment strategy",
    )
    isActive: bool = Field(default=True, description="Is chore active")
    notification: bool = Field(default=False, description="Enable notifications")
    notificationMetadata: NotificationMetadata | None = Field(
        None,
        description="Notification settings",
    )
    labels: list[str] | None = Field(None, description="Legacy labels")
    labelsV2: list[Label] = Field(default_factory=list, description="Chore labels")
    circleId: int = Field(..., description="Circle/household ID")
    createdAt: str = Field(..., description="Creation timestamp (ISO 8601)")
    updatedAt: str = Field(..., description="Last update timestamp (ISO 8601)")
    createdBy: int = Field(..., description="Creator user ID")
    updatedBy: int | None = Field(None, description="Last updater user ID")
    status: Any | None = Field(None, description="Chore status (can be string or int)")
    priority: int | None = Field(None, ge=0, le=4, description="Priority (0=unset, 1=lowest, 4=highest)")
    isPrivate: bool = Field(default=False, description="Is private chore")
    points: int | None = Field(None, description="Points awarded")
    subTasks: list[Any] = Field(default_factory=list, description="Sub-tasks")
    thingChore: dict[str, Any] | None = Field(None, description="Thing chore metadata")
    completionWindow: int | None = Field(None, description="Days before/after due date for completion window")
    requireApproval: bool | None = Field(None, description="Requires approval to mark complete")
    deadlineOffset: int | None = Field(None, description="Offset in days for deadline calculation")


class CircleMember(BaseModel):
    """Circle member model."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Circle member ID")
    userId: int = Field(..., description="User ID")
    circleId: int = Field(..., description="Circle ID")
    role: str = Field(..., description="Member role (admin, member)")
    isActive: bool = Field(..., description="Whether member is active")
    username: str = Field(..., description="Username")
    displayName: str | None = Field(None, description="Display name")
    image: str | None = Field(None, description="Profile image URL")
    points: int | None = Field(0, description="Member points")
    pointsRedeemed: int | None = Field(0, description="Points redeemed")


class ChoreHistory(BaseModel):
    """Model for chore completion history entry."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="History record ID")
    choreId: int = Field(..., description="Associated chore ID")
    performedAt: str = Field(..., description="When the chore was performed (ISO 8601 datetime)")
    completedBy: int = Field(..., description="User ID who completed the chore")
    assignedTo: int | None = Field(None, description="User ID the chore was assigned to")
    note: str | None = Field(None, max_length=5000, description="Completion note")
    dueDate: str | None = Field(None, description="Original due date (ISO 8601)")
    status: str = Field(
        default="completed",
        description="Completion status: completed, skipped, missed, pending_approval",
    )
    points: int | None = Field(None, ge=0, description="Points awarded for completion")
    duration: int | None = Field(None, ge=0, description="Time to completion in seconds")

    @field_validator("performedAt")
    @classmethod
    def validate_performed_at(cls, v: str) -> str:
        """Validate performedAt is in RFC3339 or ISO 8601 format."""
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(
                "performedAt must be in RFC3339 format (e.g., 2025-11-10T14:30:00Z) or ISO 8601 format"
            ) from None

    @field_validator("dueDate")
    @classmethod
    def validate_history_due_date(cls, v: str | None) -> str | None:
        """Validate dueDate is in RFC3339 or ISO 8601 format."""
        if v is None:
            return v

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(
                "dueDate must be in RFC3339 format (e.g., 2025-11-10T00:00:00Z) or ISO 8601 format"
            ) from None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate history status value."""
        valid_statuses = ["completed", "skipped", "missed", "pending_approval"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"status must be one of: {', '.join(valid_statuses)}")
        return v.lower()


class ChoreDetail(Chore):
    """Extended chore model with statistics and completion history."""

    # The detail endpoint returns a lighter shape than a full chore; relax the
    # otherwise-required Chore fields it omits.
    frequency: int | None = Field(None, description="Frequency value")
    circleId: int | None = Field(None, description="Circle/household ID")
    createdAt: str | None = Field(None, description="Creation timestamp (ISO 8601)")
    updatedAt: str | None = Field(None, description="Last update timestamp (ISO 8601)")

    # Analytics and statistics fields
    totalCompletedCount: int | None = Field(
        None, ge=0, description="Total number of times this chore has been completed"
    )
    lastCompletedDate: str | None = Field(None, description="Most recent completion timestamp (ISO 8601)")
    lastCompletedBy: int | None = Field(None, description="User ID who completed the chore most recently")
    averageDuration: float | None = Field(
        None,
        ge=0,
        description="Average time to completion in seconds (from due date to completed date)",
    )
    completionHistory: list[ChoreHistory] | None = Field(
        default_factory=list, description="List of completion history records for this chore"
    )

    @field_validator("lastCompletedDate")
    @classmethod
    def validate_last_completed_date(cls, v: str | None) -> str | None:
        """Validate lastCompletedDate is in RFC3339 or ISO 8601 format."""
        if v is None:
            return v

        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except ValueError:
            raise ValueError(
                "lastCompletedDate must be in RFC3339 format (e.g., 2025-11-10T14:30:00Z) or ISO 8601 format"
            ) from None


class Thing(BaseModel):
    """Thing model (trackable value on a chore)."""

    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(..., description="Thing ID")
    name: str = Field(..., description="Thing name")
    state: str | None = Field(None, description="Current state value")
    type: str | None = Field(None, description="Thing type (number, boolean, text)")
    thingChores: list[Any] = Field(default_factory=list, description="Associated thing chore links")
    createdAt: str | None = Field(None, description="Creation timestamp (ISO 8601)")
    updatedAt: str | None = Field(None, description="Last update timestamp (ISO 8601)")
