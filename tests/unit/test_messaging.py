import pytest
from uuid import UUID
from datetime import datetime

pytestmark = pytest.mark.asyncio


async def test_direct_messages(db_service, test_user, additional_test_users):
    sender = test_user["id"]
    receiver = additional_test_users[0]["id"]

    # Send a message
    msg = await db_service.send_message(sender, receiver, "hello")
    assert msg["sender_id"] == str(sender)
    assert msg["receiver_id"] == str(receiver)
    assert msg["content"] == "hello"

    # Retrieve conversation
    messages = await db_service.get_messages(sender, receiver)
    assert any(m["id"] == msg["id"] for m in messages)


async def test_message_pagination(db_service, test_user, additional_test_users):
    sender = test_user["id"]
    receiver = additional_test_users[0]["id"]

    # Create multiple messages
    for i in range(6):
        await db_service.send_message(sender, receiver, f"m{i}")

    page1 = await db_service.get_messages(sender, receiver, limit=3)
    assert len(page1) == 3

    before = datetime.fromisoformat(page1[0]["created_at"])
    page2 = await db_service.get_messages(sender, receiver, limit=3, before=before)
    assert len(page2) == 3


async def test_group_messages(db_service, test_user, additional_test_users):
    creator = test_user["id"]
    member_id = additional_test_users[0]["id"]

    # Create group
    group = await db_service.create_group("Test Group", creator)
    group_id = UUID(group["id"])

    # Add another member
    await db_service.add_group_member(group_id, member_id)

    # Send group message
    gmsg = await db_service.send_group_message(group_id, creator, "hi group")
    assert gmsg["group_id"] == str(group_id)
    assert gmsg["sender_id"] == str(creator)

    # Retrieve messages
    messages = await db_service.get_group_messages(group_id)
    assert any(m["id"] == gmsg["id"] for m in messages)


async def test_group_message_pagination(db_service, test_user, additional_test_users):
    creator = test_user["id"]
    member_id = additional_test_users[0]["id"]

    group = await db_service.create_group("Pagination Group", creator)
    group_id = UUID(group["id"])
    await db_service.add_group_member(group_id, member_id)

    for i in range(5):
        await db_service.send_group_message(group_id, creator, f"g{i}")

    page1 = await db_service.get_group_messages(group_id, limit=2)
    assert len(page1) == 2

    before = datetime.fromisoformat(page1[0]["created_at"])
    page2 = await db_service.get_group_messages(group_id, limit=3, before=before)
    assert len(page2) == 3
