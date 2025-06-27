-- Add players table for real and fake player profiles
create table players (
  id uuid primary key default gen_random_uuid(),
  user_id uuid unique references auth.users,
  owner_id uuid references auth.users not null,
  display_name text not null,
  linked_player uuid references players(id),
  created_at timestamptz default now()
);

-- Seed players table with existing users
insert into players (id, user_id, owner_id, display_name)
select u.id, u.id, u.id, coalesce(p.display_name, '')
from auth.users u
left join profiles p on p.user_id = u.id;

-- Update foreign keys to reference players
alter table teams drop constraint if exists teams_player_a_fkey;
alter table teams drop constraint if exists teams_player_b_fkey;
alter table teams add constraint teams_player_a_fkey foreign key (player_a) references players(id);
alter table teams add constraint teams_player_b_fkey foreign key (player_b) references players(id);

alter table player_ratings drop constraint if exists player_ratings_player_id_fkey;
alter table player_ratings add constraint player_ratings_player_id_fkey foreign key (player_id) references players(id);

alter table match_players drop constraint if exists match_players_player_id_fkey;
alter table match_players add constraint match_players_player_id_fkey foreign key (player_id) references players(id);

-- Recreate compatibility view to join players
drop materialized view if exists compatibility;
create materialized view compatibility as
select
  t.player_a,
  t.player_b,
  t.mu                                    as team_mu,
  ((r1.mu + r2.mu)/2)                     as avg_individual_mu,
  t.mu - ((r1.mu + r2.mu)/2)              as delta
from teams t
join player_ratings r1 on r1.player_id = t.player_a
join player_ratings r2 on r2.player_id = t.player_b
join players p1 on p1.id = t.player_a
join players p2 on p2.id = t.player_b;
create unique index on compatibility(player_a, player_b);

-- Row level security for players
alter table players enable row level security;
create policy "own players" on players
  for select using (owner_id = auth.uid() or user_id = auth.uid());
create policy "insert own players" on players
  for insert with check (owner_id = auth.uid());
create policy "update own players" on players
  for update using (owner_id = auth.uid());
