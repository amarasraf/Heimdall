-- Run this in your Supabase SQL Editor!

-- Add a unique whatsapp_number column to user_profiles
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS whatsapp_number TEXT UNIQUE;

-- Update RLS so users can update their own profile
CREATE POLICY "Users can update own profile" 
ON public.user_profiles FOR UPDATE 
USING (auth.uid() = user_id);
