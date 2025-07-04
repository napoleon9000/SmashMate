-- Enable PostGIS extension
create extension if not exists postgis;

-- 2.2 Venues (with geospatial support)
create table venues (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  location geography(point, 4326) not null, -- lat/lon
  address text,
  created_by uuid references auth.users
);
create index venues_location_idx on venues using gist(location);

-- 2.1 User Profiles
create table profiles (
  user_id uuid primary key references auth.users on delete cascade,
  display_name text,
  avatar_url text,
  default_venue uuid references venues(id)
);

-- 2.3 Follows
create table follows (
  follower uuid references auth.users on delete cascade,
  followee uuid references auth.users on delete cascade,
  created_at timestamp default now(),
  primary key (follower, followee)
);

-- 2.4 Teams and Player Ratings
create table teams (
  id uuid primary key default gen_random_uuid(),
  player_a uuid not null,
  player_b uuid not null,
  mu numeric not null,
  sigma numeric not null,
  games_played int default 0,
  constraint unique_player_pair check (player_a < player_b)
);

create table player_ratings (
  player_id uuid primary key references auth.users on delete cascade,
  mu numeric not null,
  sigma numeric not null,
  games_played int default 0
);

-- 2.5 Matches and Players
create type match_status as enum ('confirmed','pending');

create table matches (
  id uuid primary key default gen_random_uuid(),
  venue_id uuid references venues(id),
  played_at timestamptz not null,
  created_by uuid references auth.users,
  scores jsonb not null,            -- [{set:1,team1:21,team2:17}, ...]
  status match_status default 'confirmed',
  version int default 1             -- optimistic lock
);

create table match_players (
  match_id uuid references matches(id) on delete cascade,
  player_id uuid references auth.users,
  team smallint check (team in (1,2)),
  is_winner bool,
  primary key (match_id, player_id)
);
create index mp_player_idx on match_players(player_id);

-- 2.6 Compatibility Materialized View
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
join auth.users p1 on p1.id = t.player_a
join auth.users p2 on p2.id = t.player_b;

create unique index on compatibility(player_a, player_b);

-- Row Level Security Policies

-- Profiles RLS
alter table profiles enable row level security;
create policy "self profile" on profiles
  for select using (user_id = auth.uid());

-- Venues RLS
alter table venues enable row level security;
create policy "public read venues"  on venues for select using (true);
create policy "create venue"        on venues for insert with check (created_by = auth.uid());
create policy "edit own venue"      on venues for update using (created_by = auth.uid());

-- Follows RLS
alter table follows enable row level security;
create policy "follow myself only"  on follows
  for insert with check (follower = auth.uid());
create policy "read my follows"     on follows
  for select using (
    follower = auth.uid() or followee = auth.uid()
  );

-- Matches RLS
alter table matches enable row level security;
create policy "view participants" on matches
  for select using (
    exists (
      select 1 from match_players mp
      where mp.match_id = id and mp.player_id = auth.uid()
    )
  );
create policy "edit participants" on matches
  for update using (
    exists (
      select 1 from match_players
      where match_id = id and player_id = auth.uid()
    )
  );

-- Match Players RLS
alter table match_players enable row level security;
create policy "only participants insert" on match_players
  for insert with check (player_id = auth.uid());
create policy "participants read" on match_players
  for select using (
    player_id = auth.uid() OR
    exists (select 1 from match_players mp2
            where mp2.match_id = match_id and mp2.player_id = auth.uid())
  ); 