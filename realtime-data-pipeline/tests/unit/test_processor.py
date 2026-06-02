"""Unit tests for stream processor."""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.processors.processor import handler, process_event, parse_timestamp


class TestProcessEvent:
    def test_valid_event(self):
        event = {
            "event_type": "page_view",
            "timestamp": "2024-01-15T10:30:00Z",
            "user_id": "user123",
            "session_id": "session456",
            "properties": {"page": "/home"},
        }

        result = process_event(event)

        assert result is not None
        assert result["event_type"] == "page_view"
        assert result["user_id"] == "user123"
        assert result["session_id"] == "session456"
        assert "event_id" in result
        assert "processed_at" in result

    def test_missing_required_field(self):
        event = {
            "user_id": "user123",
            "timestamp": "2024-01-15T10:30:00Z",
        }

        result = process_event(event)
        assert result is None

    def test_missing_timestamp(self):
        event = {
            "event_type": "click",
        }

        result = process_event(event)
        assert result is None

    def test_unix_timestamp(self):
        event = {
            "event_type": "page_view",
            "timestamp": 1705317000,
        }

        result = process_event(event)
        assert result is not None
        assert "2024" in result["timestamp"]

    def test_invalid_timestamp(self):
        event = {
            "event_type": "page_view",
            "timestamp": "not-a-timestamp",
        }

        result = process_event(event)
        assert result is None

    def test_auto_generated_event_id(self):
        event = {
            "event_type": "page_view",
            "timestamp": "2024-01-15T10:30:00Z",
        }

        result = process_event(event)
        assert result is not None
        # Should be a valid UUID
        uuid.UUID(result["event_id"])


class TestParseTimestamp:
    def test_iso_string(self):
        result = parse_timestamp("2024-01-15T10:30:00Z")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_unix_timestamp(self):
        result = parse_timestamp(1705317000)
        assert result.year == 2024

    def test_invalid_type(self):
        with pytest.raises(ValueError):
            parse_timestamp(None)


class TestHandler:
    @patch("src.processors.processor.s3_client")
    @patch("src.processors.processor.BUCKET_NAME", "test-bucket")
    def test_process_valid_records(self, mock_s3):
        mock_s3.put_object.return_value = {}

        event = {
            "Records": [
                {
                    "kinesis": {
                        "data": json.dumps({
                            "event_type": "page_view",
                            "timestamp": "2024-01-15T10:30:00Z",
                            "user_id": "user1",
                        }),
                        "sequenceNumber": "seq1",
                    }
                },
                {
                    "kinesis": {
                        "data": json.dumps({
                            "event_type": "click",
                            "timestamp": "2024-01-15T10:31:00Z",
                            "user_id": "user2",
                        }),
                        "sequenceNumber": "seq2",
                    }
                },
            ]
        }

        context = MagicMock()
        result = handler(event, context)

        assert result["batchItemFailures"] == []
        mock_s3.put_object.assert_called_once()

    @patch("src.processors.processor.s3_client")
    @patch("src.processors.processor.BUCKET_NAME", "test-bucket")
    def test_process_invalid_records(self, mock_s3):
        mock_s3.put_object.return_value = {}

        event = {
            "Records": [
                {
                    "kinesis": {
                        "data": json.dumps({
                            "user_id": "user1",  # Missing event_type
                            "timestamp": "2024-01-15T10:30:00Z",
                        }),
                        "sequenceNumber": "seq1",
                    }
                },
                {
                    "kinesis": {
                        "data": "invalid json",
                        "sequenceNumber": "seq2",
                    }
                },
            ]
        }

        context = MagicMock()
        result = handler(event, context)

        assert len(result["batchItemFailures"]) == 2
        assert result["batchItemFailures"][0]["itemIdentifier"] == "seq1"
        assert result["batchItemFailures"][1]["itemIdentifier"] == "seq2"

    @patch("src.processors.processor.s3_client")
    @patch("src.processors.processor.BUCKET_NAME", "test-bucket")
    def test_empty_records(self, mock_s3):
        event = {"Records": []}
        context = MagicMock()
        result = handler(event, context)

        assert result["batchItemFailures"] == []
        mock_s3.put_object.assert_not_called()
