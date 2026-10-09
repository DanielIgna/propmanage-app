import { defineCloudflareConfig } from "@opennextjs/cloudflare";

// No incremental cache bucket yet: pages are rendered per request (the SPA shell is tiny).
export default defineCloudflareConfig({});
