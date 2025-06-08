-- Messaging tables

create table messages (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid references auth.users on delete cascade,
  receiver_id uuid references auth.users on delete cascade,
  content text not null,
  created_at timestamptz default now()
);

create table groups (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  creator_id uuid references auth.users on delete cascade,
  created_at timestamptz default now()
);

create table group_members (
  group_id uuid references groups(id) on delete cascade,
  user_id uuid references auth.users on delete cascade,
  primary key (group_id, user_id)
);

create table group_messages (
  id uuid primary key default gen_random_uuid(),
  group_id uuid references groups(id) on delete cascade,
  sender_id uuid references auth.users on delete cascade,
  content text not null,
  created_at timestamptz default now()
);

-- Enable RLS
alter table messages enable row level security;
create policy "read own direct messages" on messages
  for select using (
    sender_id = auth.uid() or receiver_id = auth.uid()
  );
create policy "send direct messages" on messages
  for insert with check (sender_id = auth.uid());

alter table groups enable row level security;
create policy "group creator" on groups
  for insert with check (creator_id = auth.uid());
create policy "view own groups" on groups
  for select using (
    creator_id = auth.uid() or
    exists (
      select 1 from group_members m
      where m.group_id = id and m.user_id = auth.uid()
    )
  );

alter table group_members enable row level security;
create policy "join group" on group_members
  for insert with check (
    auth.uid() = user_id or auth.uid() = (
      select creator_id from groups g where g.id = group_id
    )
  );
create policy "view group members" on group_members
  for select using (
    exists (
      select 1 from group_members m
      where m.group_id = group_id and m.user_id = auth.uid()
    )
  );

alter table group_messages enable row level security;
create policy "send group message" on group_messages
  for insert with check (
    sender_id = auth.uid() and exists (
      select 1 from group_members m
      where m.group_id = group_id and m.user_id = auth.uid()
    )
  );
create policy "read group messages" on group_messages
  for select using (
    exists (
      select 1 from group_members m
      where m.group_id = group_id and m.user_id = auth.uid()
    )
  );
