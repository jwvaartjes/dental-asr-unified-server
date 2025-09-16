# CRITICAL PROJECT RULE

**WORKSPACE DIRECTORY**: `/Users/janwillemvaartjes/projects/pairing_server`

**ABSOLUTE RULE**: We work ONLY in the current project directory. 

**DO NOT**: 
- Import from `/Users/janwillemvaartjes/tand-asr-runpod/stable_baseline_workspace`
- Reference old workspace paths
- Try to use external supabase_manager module

**CURRENT ISSUE**: Template system trying to import supabase_manager from old workspace, causing server crashes.

**SOLUTION NEEDED**: Either:
1. Remove template functionality completely, OR
2. Reimplement template storage using existing SupabaseLoader class that's already working