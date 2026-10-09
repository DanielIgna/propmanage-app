import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;
const supabaseKey = process.env.REACT_APP_SUPABASE_PUBLISHABLE_KEY;

// Browser client: only ever uses the publishable key. Access is enforced by RLS.
export const supabase =
  supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey, {
        // PKCE; AuthCallback exchanges the ?code itself (avoids clashing with the direct Google flow).
        auth: { flowType: "pkce", detectSessionInUrl: false },
      }) : null;
