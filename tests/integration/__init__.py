"""
Integration tests for SmashMate.

This package contains comprehensive integration tests that verify the complete
user journey and system interactions across multiple components.

Features tested:
- Complete user workflows from signup to match completion
- Database operations with TrueSkill rating calculations
- Social features and messaging systems
- Venue management and geographic queries
- Performance under concurrent loads
- Error handling and edge cases

Test files:
- test_happy_path.py: Core user journey integration tests
- test_advanced_scenarios.py: Performance, error handling, and complex workflows

All integration tests use automatic database cleanup to ensure isolation.
"""

# Mark this package for pytest discovery
__all__ = []
