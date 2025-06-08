# SmashMate Integration Tests

This directory contains comprehensive integration tests that verify the complete SmashMate user journey and system interactions.

## 🧪 Test Files

### `test_happy_path.py`
- **Complete Happy Path Flow**: 12-step user journey from signup to leaderboards
- **Edge Case Scenarios**: Single player journeys, venue searches, rating calculations
- **Social Network Features**: Following/follower relationships, mutual connections
- **Messaging Integration**: Match coordination and communication workflows

### `test_advanced_scenarios.py`
- **Performance Scenarios**: Large tournaments with 12 users and concurrent operations
- **Error Handling**: Invalid match scenarios and edge cases
- **Real-World Workflows**: Weekly leagues and new player onboarding
- **Concurrent Load Testing**: Heavy messaging and database operations

## 🧹 Database Cleanup System

### Automatic Cleanup
All integration tests use **automatic database cleanup** to ensure complete isolation:

```python
@pytest.fixture(autouse=True)
async def integration_test_cleanup(db_service):
    """Comprehensive database cleanup for integration tests."""
    # Clean up before test
    await comprehensive_database_cleanup(db_service)
    yield
    # Clean up after test
    await comprehensive_database_cleanup(db_service)
```

### Cleanup Features
- **Comprehensive**: Cleans all test-related tables in dependency order
- **Safe**: Respects foreign key constraints and handles errors gracefully
- **Automatic**: Runs before and after each test without manual intervention
- **Logged**: Provides detailed logging of cleanup operations
- **Verified**: Checks remaining records after cleanup

### Tables Cleaned
The cleanup system handles these tables in the correct order:
1. `group_messages` - Group chat messages
2. `messages` - Direct messages
3. `match_players` - Match participation records
4. `matches` - Match data
5. `player_ratings` - TrueSkill ratings
6. `teams` - Team combinations and ratings
7. `follows` - Social connections
8. `groups` - Group chats
9. `venues` - Badminton venues
10. `profiles` - User profiles

## 🚀 Running Integration Tests

### Run All Integration Tests
```bash
pytest tests/integration/ -v
```

### Run with Markers
```bash
# Run only integration tests
pytest -m integration -v

# Run performance tests specifically  
pytest -m "integration and performance" -v
```

### Cleanup Demo
Run the cleanup demonstration:
```bash
python tests/test_integration_cleanup_demo.py
```

## 📊 Test Coverage

### User Journey Testing
- ✅ Authentication and profile creation
- ✅ Venue search and selection
- ✅ Social network building (following/followers)
- ✅ Group messaging and coordination
- ✅ Match creation with different partner combinations
- ✅ TrueSkill rating calculations and updates
- ✅ Compatibility score generation
- ✅ Partner recommendations
- ✅ Leaderboard rankings

### Performance Testing
- ✅ Tournament simulation with 12 users
- ✅ Concurrent messaging (30+ messages simultaneously)
- ✅ Direct messaging between all user pairs
- ✅ Complex social network operations
- ✅ Multiple venue and match operations

### Error Handling
- ✅ Invalid match scenarios
- ✅ Extreme geographic coordinates
- ✅ Social network stress testing
- ✅ Database constraint handling

## 🔧 Configuration

### Test Markers
Integration tests are automatically marked with `@pytest.mark.integration` based on their location in the `tests/integration/` directory.

### Environment Requirements
- Supabase local development environment
- PostgreSQL with PostGIS extension
- All environment variables properly configured in `.env`

### Logging
Test logging is configured to show:
- Cleanup operations and record counts
- Test progress and checkpoints
- Warning messages for cleanup issues
- Summary statistics after each test

## 🛠️ Troubleshooting

### Common Issues

**Q: Tests fail with "user already exists" errors**
A: The automatic cleanup system now prevents this by using unique timestamps in email addresses.

**Q: Database cleanup warnings appear**
A: This is normal - cleanup attempts all possible deletion paths and logs warnings for missing tables or constraint violations.

**Q: Tests are slow**
A: Integration tests include comprehensive database operations and cleanup. Use `pytest -x` to stop on first failure for faster debugging.

### Debug Mode
Enable debug logging for detailed cleanup information:
```python
import logging
logging.getLogger('tests.utils').setLevel(logging.DEBUG)
```

## 📈 Performance Metrics

### Typical Test Times
- **Happy Path Tests**: 8-12 seconds (6 tests)
- **Advanced Scenarios**: 15-20 seconds (7 tests)
- **Total Integration Suite**: 20-25 seconds (13 tests)

### Database Operations per Test
- **User Creation**: 6-12 test users per test
- **Profile Operations**: 6-12 profiles created/updated
- **Match Simulations**: 3-9 matches with rating calculations
- **Social Operations**: 10-50 follow/unfollow operations
- **Messaging**: 10-30 messages sent

## 🔮 Future Enhancements

- [ ] Add API endpoint integration tests
- [ ] Include real-time features testing
- [ ] Add mobile app workflow simulations
- [ ] Performance benchmarking and monitoring
- [ ] Integration with CI/CD pipeline metrics 