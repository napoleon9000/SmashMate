import asyncio
import uuid
from types import SimpleNamespace
from typing import Generator

import pytest


class FakeResponse:
    def __init__(self, data=None, user=None):
        self.data = data
        self.user = user


class FakeTable:
    def __init__(self, storage):
        self.storage = storage
        self._filter = lambda row: True
        self._limit = None
        self._action = "select"
        self._payload = None
        self._update_data = None

    def insert(self, data):
        self._action = "insert"
        self._payload = data
        return self

    def select(self, *args):
        self._action = "select"
        self._filter = lambda row: True
        self._limit = None
        self._payload = None
        self._update_data = None
        return self

    def limit(self, n):
        self._limit = n
        return self

    def eq(self, key, value):
        prev_filter = self._filter
        self._filter = lambda row, prev_filter=prev_filter: prev_filter(row) and row.get(key) == value
        return self

    def update(self, data):
        self._action = "update"
        self._update_data = data
        return self

    def delete(self):
        self._action = "delete"
        return self

    def execute(self):
        if self._action == "insert":
            self.storage.append(self._payload)
            return FakeResponse([self._payload])

        if self._action == "update":
            result = []
            for row in self.storage:
                if self._filter(row):
                    row.update(self._update_data)
                    result.append(row)
            return FakeResponse(result)

        if self._action == "delete":
            result = [row for row in self.storage if self._filter(row)]
            self.storage[:] = [row for row in self.storage if not self._filter(row)]
            return FakeResponse(result)

        # select
        result = [row for row in self.storage if self._filter(row)]
        if self._limit is not None:
            result = result[: self._limit]
        return FakeResponse(result)


class FakeAuthAdmin:
    def __init__(self, users):
        self.users = users

    def create_user(self, data):
        user = {"id": str(uuid.uuid4()), "email": data["email"], "password": data["password"]}
        self.users.append(user)
        return FakeResponse(user=SimpleNamespace(id=user["id"]))

    def delete_user(self, user_id):
        self.users[:] = [u for u in self.users if u["id"] != user_id]
        return FakeResponse([])


class FakeAuth:
    def __init__(self, users):
        self.admin = FakeAuthAdmin(users)


class FakeSupabaseClient:
    def __init__(self):
        self._tables = {"profiles": [], "users": []}
        self.auth = FakeAuth(self._tables["users"])

    def table(self, name):
        return FakeTable(self._tables.setdefault(name, []))


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def supabase_client():
    return FakeSupabaseClient()


@pytest.fixture
async def test_user(supabase_client):
    email = f"test_{uuid.uuid4()}@example.com"
    password = "test_password123"
    response = supabase_client.auth.admin.create_user({"email": email, "password": password})
    user_id = response.user.id
    yield {"id": user_id, "email": email, "password": password}
    supabase_client.auth.admin.delete_user(user_id)
