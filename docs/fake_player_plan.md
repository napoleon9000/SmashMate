# Fake Player Linking Refactor

This migration introduces a unified `players` table to store both real users and fake players. Fake players can be linked to real players so their match history and ratings merge.

## Database Changes

- New `players` table with columns:
  - `id` primary key
  - `user_id` references `auth.users` (null for fake players)
  - `owner_id` the user who created the fake player
  - `display_name`
  - `linked_player` optional reference to another player
- Existing tables `teams`, `player_ratings` and `match_players` now reference `players.id` instead of `auth.users`.
- A data migration seeds rows for all existing users so their player IDs match their user IDs.
- Row level security policies restrict access so users can manage their own fake players.

Run `supabase db push` after applying the migration file `20240401000000_add_players.sql`.
