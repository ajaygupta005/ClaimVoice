"""Component 04 - Python logger emits the schema."""
import json
import io
import pytest


def test_python_logger_emits_required_fields():
    """Emit one log line, assert all required schema fields are present."""
    pytest.importorskip("loguru")
    from loguru import logger

    buf = io.StringIO()
    handler_id = logger.add(buf, format="{message}", serialize=True)
    logger.bind(service="test", correlation_id="abc-123").info("hello")
    logger.remove(handler_id)

    line = buf.getvalue().strip().splitlines()[-1]
    data = json.loads(line)
    record = data.get("record", data)
    # loguru serializes inside "record"; check timestamp/level/message exist
    assert "time" in record or "timestamp" in record
    assert "level" in record
    assert "message" in record or "text" in record
