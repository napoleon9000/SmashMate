#!/bin/bash

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "Supabase CLI is not installed. Please install it first:"
    echo "brew install supabase/tap/supabase"
    exit 1
fi

# Initialize Supabase project if not already initialized
if [ ! -d "supabase" ]; then
    echo "Initializing Supabase project..."
    supabase init
fi

# Start Supabase services
echo "Starting Supabase services..."
supabase start

# Apply migrations
echo "Applying database migrations..."
supabase db reset

echo "Local Supabase instance is ready!"
echo "Studio URL: http://localhost:54323"
echo "API URL: http://localhost:54321"
echo "Database URL: postgresql://postgres:postgres@localhost:54322/postgres" 
