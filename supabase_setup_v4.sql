-- supabase_setup_v4.sql

-- 1. Create a sessions table so the bot has a "memory" of conversations
CREATE TABLE IF NOT EXISTS public.whatsapp_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    sender_number TEXT NOT NULL,
    state TEXT NOT NULL, -- e.g., 'AWAITING_PRICE', 'AWAITING_RECEIPT', 'COMPLETED'
    parsed_address JSONB,
    raw_message TEXT,
    amount NUMERIC,
    payment_link TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- 2. Setup Public Storage Bucket for DuitNow QRs
INSERT INTO storage.buckets (id, name, public) 
VALUES ('duitnow_qrs', 'duitnow_qrs', true) 
ON CONFLICT (id) DO NOTHING;

-- 3. Storage Policies
CREATE POLICY "Public DuitNow Access" 
ON storage.objects FOR SELECT 
USING (bucket_id = 'duitnow_qrs');

CREATE POLICY "Authenticated Users can upload QRs" 
ON storage.objects FOR INSERT 
WITH CHECK (bucket_id = 'duitnow_qrs');

CREATE POLICY "Authenticated Users can update QRs" 
ON storage.objects FOR UPDATE 
USING (bucket_id = 'duitnow_qrs');
