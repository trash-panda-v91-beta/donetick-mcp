"""
Unit tests for notification metadata transformation.

Tests the transform_notification_metadata function in isolation.
"""

import pytest

from donetick_mcp.client import DonetickClient


class TestNotificationTransform:
    """Unit tests for notification metadata transformation."""

    def setup_method(self):
        """Create a client instance for testing."""
        # We don't need a real connection for unit tests
        self.client = DonetickClient(base_url="https://example.com", api_token="test-token")

    def test_nagging_only(self):
        """Test nagging flag only."""
        result = self.client.transform_notification_metadata(nagging=True)

        assert result["nagging"] is True
        assert result["predue"] is False
        assert "templates" not in result

    def test_predue_only(self):
        """Test predue flag only."""
        result = self.client.transform_notification_metadata(predue=True)

        assert result["nagging"] is False
        assert result["predue"] is True
        assert "templates" not in result

    def test_offset_only(self):
        """Test offset reminder only."""
        result = self.client.transform_notification_metadata(offset_minutes=-15)

        assert result["nagging"] is False
        assert result["predue"] is False
        assert "templates" in result
        assert len(result["templates"]) == 1
        assert result["templates"][0]["value"] == -15
        assert result["templates"][0]["unit"] == "m"

    def test_remind_at_due_time_only(self):
        """Test reminder at due time only."""
        result = self.client.transform_notification_metadata(remind_at_due_time=True)

        assert result["nagging"] is False
        assert result["predue"] is False
        assert "templates" in result
        assert len(result["templates"]) == 1
        assert result["templates"][0]["value"] == 0
        assert result["templates"][0]["unit"] == "m"

    def test_dual_reminders(self):
        """Test offset + at due time."""
        result = self.client.transform_notification_metadata(offset_minutes=-30, remind_at_due_time=True)

        assert result["nagging"] is False
        assert result["predue"] is False
        assert "templates" in result
        assert len(result["templates"]) == 2

        # Check both reminders present
        values = [t["value"] for t in result["templates"]]
        assert -30 in values
        assert 0 in values

    def test_all_combined(self):
        """Test all notification mechanisms together."""
        result = self.client.transform_notification_metadata(
            offset_minutes=-15, remind_at_due_time=True, nagging=True, predue=True
        )

        # Check flags
        assert result["nagging"] is True
        assert result["predue"] is True

        # Check templates
        assert "templates" in result
        assert len(result["templates"]) == 2
        values = [t["value"] for t in result["templates"]]
        assert -15 in values
        assert 0 in values

    def test_no_notifications(self):
        """Test no notification settings."""
        result = self.client.transform_notification_metadata()

        assert result["nagging"] is False
        assert result["predue"] is False
        assert "templates" not in result

    def test_offset_zero_ignored(self):
        """Test that offset_minutes=0 is ignored (use remind_at_due_time instead)."""
        result = self.client.transform_notification_metadata(offset_minutes=0)

        # Zero offset should not create a template
        assert result["nagging"] is False
        assert result["predue"] is False
        assert "templates" not in result

    def test_positive_offset(self):
        """Test positive offset (after due time)."""
        result = self.client.transform_notification_metadata(offset_minutes=30)

        assert result["nagging"] is False
        assert result["predue"] is False
        assert "templates" in result
        assert len(result["templates"]) == 1
        assert result["templates"][0]["value"] == 30
        assert result["templates"][0]["unit"] == "m"

    def test_nagging_and_predue_without_templates(self):
        """Test nagging and predue flags without any templates."""
        result = self.client.transform_notification_metadata(nagging=True, predue=True)

        assert result["nagging"] is True
        assert result["predue"] is True
        assert "templates" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
