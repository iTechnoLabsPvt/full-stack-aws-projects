"""Unit tests for batch processor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.processors.batch_processor import (
    handler,
    generate_aggregations,
    run_quality_checks,
)


class TestGenerateAggregations:
    def test_basic_aggregation(self):
        records = [
            {"event_type": "page_view", "user_id": "user1", "session_id": "sess1"},
            {"event_type": "page_view", "user_id": "user2", "session_id": "sess2"},
            {"event_type": "click", "user_id": "user1", "session_id": "sess1"},
        ]

        hour = datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)
        result = generate_aggregations(records, hour)

        assert len(result) == 2

        page_view_agg = next(a for a in result if a["event_type"] == "page_view")
        assert page_view_agg["event_count"] == 2
        assert page_view_agg["unique_users"] == 2
        assert page_view_agg["unique_sessions"] == 2

        click_agg = next(a for a in result if a["event_type"] == "click")
        assert click_agg["event_count"] == 1

    def test_empty_records(self):
        result = generate_aggregations([], datetime.now(timezone.utc))
        assert result == []


class TestRunQualityChecks:
    def test_all_valid(self):
        records = [
            {"event_type": "page_view", "user_id": "user1", "timestamp": "2024-01-15T10:00:00Z"},
            {"event_type": "click", "user_id": "user2", "timestamp": "2024-01-15T10:01:00Z"},
        ]

        result = run_quality_checks(records)

        assert result["total_records"] == 2
        assert result["missing_event_type"] == 0
        assert result["missing_user_id"] == 0
        assert result["missing_timestamp"] == 0
        assert result["unique_event_types"] == 2

    def test_with_missing_fields(self):
        records = [
            {"event_type": "page_view", "user_id": "user1", "timestamp": "2024-01-15T10:00:00Z"},
            {"event_type": None, "user_id": "", "timestamp": None},
        ]

        result = run_quality_checks(records)

        assert result["total_records"] == 2
        assert result["missing_event_type"] == 1
        assert result["missing_user_id"] == 1
        assert result["missing_timestamp"] == 1


class TestHandler:
    @patch("src.processors.batch_processor.s3_client")
    @patch("src.processors.batch_processor.BUCKET_NAME", "test-bucket")
    def test_no_data(self, mock_s3):
        mock_s3.list_objects_v2.return_value = {"Contents": []}

        event = {}
        context = MagicMock()
        result = handler(event, context)

        assert result["status"] == "no_data"
        assert result["records_processed"] == 0
