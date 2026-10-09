import { createContext, useContext } from "react";

// True when the current page was rendered by a Next.js server route (metadata, CMS texts
// and page config already present in the HTML), so client-side duplicates can be skipped.
export const ServerRenderedContext = createContext(false);
export const useServerRendered = () => useContext(ServerRenderedContext);
