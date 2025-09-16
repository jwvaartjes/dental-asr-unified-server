-- Enhance existing users table for user management system
-- Run this in Supabase SQL Editor

-- 1. Add missing columns to public.users
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0;

-- 2. Update role constraint to include super_admin
ALTER TABLE public.users
DROP CONSTRAINT IF EXISTS users_role_check;

ALTER TABLE public.users
ADD CONSTRAINT users_role_check
CHECK (role IN ('user', 'admin', 'super_admin'));

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOTå EXISTS idx_users_status ON public.users(status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON public.users(last_login);

-- 4. Create activity log table for audit trail
CREATE TABLE IF NOT EXISTS public.user_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    admin_id UUID REFERENCES public.users(id), -- Who performed the action
    action TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create indexes for activity log
CREATE INDEX IF NOT EXISTS idx_user_activity_log_user_id ON public.user_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_admin_id ON public.user_activity_log(admin_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_created_at ON public.user_activity_log(created_at);
CREATE INDEX IF NOT EXISTS idx_user_activity_log_action ON public.user_activity_log(action);

-- 6. Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_users_updated_at ON public.users;
CREATE TRIGGER trigger_update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 8. Enable Row Level Security (RLS) on both tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_activity_log ENABLE ROW LEVEL SECURITY;

-- 9. Create RLS policies for users table
DROP POLICY IF EXISTS "Users can view own profile" ON public.users;
CREATE POLICY "Users can view own profile" ON public.users
    FOR SELECT USING (
        auth.uid()::text = id::text OR
        EXISTS (
            SELECT 1 FROM public.users admin_user
            WHERE admin_user.id::text = auth.uid()::text
            AND admin_user.role IN ('admin', 'super_admin')
        )
    );

DROP POLICY IF EXISTS "Admins can manage users" ON public.users;
CREATE POLICY "Admins can manage users" ON public.users
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.users admin_user
            WHERE admin_user.id::text = auth.uid()::text
            AND admin_user.role IN ('admin', 'super_admin')
        )
    );

-- 10. Create RLS policies for activity log
DROP POLICY IF EXISTS "Admins can view activity log" ON public.user_activity_log;
CREATE POLICY "Admins can view activity log" ON public.user_activity_log
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.users admin_user
            WHERE admin_user.id::text = auth.uid()::text
            AND admin_user.role IN ('admin', 'super_admin')
        )
    );

DROP POLICY IF EXISTS "System can insert activity log" ON public.user_activity_log;
CREATE POLICY "System can insert activity log" ON public.user_activity_log
    FOR INSERT WITH CHECK (true);

-- 11. Grant permissions
GRANT ALL ON public.users TO authenticated;
GRANT ALL ON public.user_activity_log TO authenticated;
GRANT USAGE ON SCHEMA public TO authenticated;

-- 12. Ensure we have a super_admin user (update existing admin)
-- IMPORTANT: Replace this ID with your actual admin user ID if different
UPDATE public.users
SET role = 'super_admin', status = 'active'
WHERE id = '76c7198e-710f-41dc-b26d-ce728571a546';

-- 13. Verification queries
SELECT 'Users table schema updated' as result;
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users' AND table_schema = 'public'
ORDER BY ordinal_position;

SELECT 'Activity log table created' as result;
SELECT count(*) as user_count, role, status
FROM public.users
GROUP BY role, status;