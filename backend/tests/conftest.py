import pytest


@pytest.fixture(autouse=True)
def _fresh_llm_limiters():
    """Per-model limiters are process-wide; forget per-minute history between tests."""
    from finn.llm.router import reset_limiters

    reset_limiters()
    yield
