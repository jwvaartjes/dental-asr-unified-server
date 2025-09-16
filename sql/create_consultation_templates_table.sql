-- Create consultation_templates table for template-based consultation system
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS consultation_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_name TEXT NOT NULL,
    template_type TEXT NOT NULL DEFAULT 'general',
    description TEXT DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    settings JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT template_name_not_empty CHECK (template_name != ''),
    CONSTRAINT valid_template_type CHECK (template_type IN ('general', 'specialty', 'emergency', 'pediatric', 'orthodontic', 'periodontal', 'endodontic', 'oral_surgery')),
    CONSTRAINT settings_not_empty CHECK (settings != '{}'::jsonb),

    -- Unique template name per user
    UNIQUE(user_id, template_name)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_consultation_templates_user_id ON consultation_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_consultation_templates_active ON consultation_templates(user_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_consultation_templates_default ON consultation_templates(user_id, is_default) WHERE is_default = TRUE;
CREATE INDEX IF NOT EXISTS idx_consultation_templates_type ON consultation_templates(user_id, template_type);
CREATE INDEX IF NOT EXISTS idx_consultation_templates_name ON consultation_templates(user_id, template_name);

-- Add GIN index for JSONB settings for efficient querying
CREATE INDEX IF NOT EXISTS idx_consultation_templates_settings_gin ON consultation_templates USING GIN (settings);

-- Create function to enforce single active template per user
CREATE OR REPLACE FUNCTION enforce_single_active_template()
RETURNS TRIGGER AS $$
BEGIN
    -- If setting a template as active, deactivate all others for this user
    IF NEW.is_active = TRUE THEN
        UPDATE consultation_templates
        SET is_active = FALSE
        WHERE user_id = NEW.user_id
          AND id != NEW.id
          AND is_active = TRUE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce single active template
DROP TRIGGER IF EXISTS trigger_single_active_template ON consultation_templates;
CREATE TRIGGER trigger_single_active_template
    BEFORE INSERT OR UPDATE ON consultation_templates
    FOR EACH ROW
    EXECUTE FUNCTION enforce_single_active_template();

-- Create function to enforce single default template per user
CREATE OR REPLACE FUNCTION enforce_single_default_template()
RETURNS TRIGGER AS $$
BEGIN
    -- If setting a template as default, remove default from all others for this user
    IF NEW.is_default = TRUE THEN
        UPDATE consultation_templates
        SET is_default = FALSE
        WHERE user_id = NEW.user_id
          AND id != NEW.id
          AND is_default = TRUE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to enforce single default template
DROP TRIGGER IF EXISTS trigger_single_default_template ON consultation_templates;
CREATE TRIGGER trigger_single_default_template
    BEFORE INSERT OR UPDATE ON consultation_templates
    FOR EACH ROW
    EXECUTE FUNCTION enforce_single_default_template();

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_consultation_templates_updated_at ON consultation_templates;
CREATE TRIGGER trigger_update_consultation_templates_updated_at
    BEFORE UPDATE ON consultation_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE consultation_templates ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (adjust based on your auth system)
-- Users can only see their own templates
DROP POLICY IF EXISTS "Users can view own consultation templates" ON consultation_templates;
CREATE POLICY "Users can view own consultation templates" ON consultation_templates
    FOR SELECT USING (
        auth.uid()::text = user_id::text OR
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('admin', 'super_admin')
        )
    );

-- Users can insert their own templates
DROP POLICY IF EXISTS "Users can insert own consultation templates" ON consultation_templates;
CREATE POLICY "Users can insert own consultation templates" ON consultation_templates
    FOR INSERT WITH CHECK (
        auth.uid()::text = user_id::text OR
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('admin', 'super_admin')
        )
    );

-- Users can update their own templates
DROP POLICY IF EXISTS "Users can update own consultation templates" ON consultation_templates;
CREATE POLICY "Users can update own consultation templates" ON consultation_templates
    FOR UPDATE USING (
        auth.uid()::text = user_id::text OR
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('admin', 'super_admin')
        )
    ) WITH CHECK (
        auth.uid()::text = user_id::text OR
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('admin', 'super_admin')
        )
    );

-- Users can delete their own templates
DROP POLICY IF EXISTS "Users can delete own consultation templates" ON consultation_templates;
CREATE POLICY "Users can delete own consultation templates" ON consultation_templates
    FOR DELETE USING (
        auth.uid()::text = user_id::text OR
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('admin', 'super_admin')
        )
    );

-- Grant necessary permissions
GRANT ALL ON consultation_templates TO authenticated;
GRANT USAGE ON SCHEMA public TO authenticated;

-- Example default template settings JSONB structure for reference:
/*
{
  "prompt_config": {
    "system_prompt": "Dit is een Nederlandse tandheelkundige consultatie. Gebruik correcte tandheelkundige terminologie voor elementen, bevindingen, behandelingen en anatomische structuren. Element nummers zijn: 11-18, 21-28, 31-38, 41-48, 51-55, 61-65, 71-75, 81-85.",
    "include_base_prompt": true,
    "additional_context": ""
  },
  "model_config": {
    "provider": "openai",
    "model_name": "gpt-4o-transcribe",
    "language": "nl",
    "temperature": 0.2
  },
  "vad_config": {
    "enable_silero": true,
    "silero_threshold": 0.9,
    "enable_frontend_vad": false,
    "silence_duration": 1.5
  },
  "lexicon_config": {
    "enabled_categories": [],
    "disabled_categories": [],
    "use_custom_patterns": true,
    "use_protected_words": true,
    "custom_additions": {}
  },
  "normalization_config": {
    "enable_phonetic": true,
    "phonetic_threshold": 0.84,
    "enable_element_parsing": true,
    "enable_variant_generation": true
  }
}
*/

-- Verification queries (run after table creation):
-- SELECT * FROM consultation_templates LIMIT 5;
-- SELECT COUNT(*) FROM consultation_templates;
-- \d consultation_templates