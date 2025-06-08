# Instant Messaging Feature Plan

This document outlines the steps to enable a simple instant messaging system using Supabase. It covers database schema creation, Supabase dashboard configuration and backend integration.

## 1. Database schema
Create a new migration under `supabase/migrations` with the following tables:

- **messages**: direct messages between two users
  - `id` UUID primary key
  - `sender_id` UUID references `auth.users`
  - `receiver_id` UUID references `auth.users`
  - `content` text
  - `created_at` timestamp with time zone default `now()`

- **groups**: chat groups
  - `id` UUID primary key
  - `name` text
  - `creator_id` UUID references `auth.users`
  - `created_at` timestamp with time zone default `now()`

- **group_members**: membership table
  - `group_id` UUID references `groups`
  - `user_id` UUID references `auth.users`
  - primary key (`group_id`, `user_id`)

- **group_messages**: messages sent in a group
  - `id` UUID primary key
  - `group_id` UUID references `groups`
  - `sender_id` UUID references `auth.users`
  - `content` text
  - `created_at` timestamp with time zone default `now()`

Enable Row Level Security and add policies so users can only read their own direct messages and the groups they belong to.

## 2. Supabase dashboard setup
1. Start your local Supabase instance with `supabase start` or deploy a project on [Supabase](https://supabase.com).
2. Apply the migrations:
   ```bash
   supabase db reset --schema public
   supabase db diff --file supabase/migrations/<timestamp>_add_messages.sql
   supabase db push
   ```
3. In the dashboard, open **Auth > Policies** and verify that the row level security policies from the migration were applied.
4. Under **Database > Realtime**, enable Realtime for the `messages` and `group_messages` tables so the frontend can subscribe to new inserts.

## 3. Backend integration
The backend exposes helper methods in `DatabaseService` for sending and retrieving messages. See `app/services/database.py` for implementations:

- `send_message(sender_id, receiver_id, content)`
- `get_messages(user1_id, user2_id, limit=50, before=None)`
- `create_group(name, creator_id)`
- `add_group_member(group_id, user_id)`
- `send_group_message(group_id, sender_id, content)`
- `get_group_messages(group_id, limit=50, before=None)`

These functions use `supabase-py` and can be consumed by API routes or other services.

Both message retrieval helpers support simple pagination through the
`limit` and `before` parameters. Fetch the most recent messages with the
desired limit, then request older history by passing the timestamp from
the earliest loaded message to the next call's `before` argument.

## 4. Usage
On the client side, subscribe to `INSERT` events on the `messages` and `group_messages` tables using the Supabase Realtime SDK. When a new record is inserted, update the chat UI accordingly.

