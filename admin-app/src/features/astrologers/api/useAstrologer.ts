import { useQuery } from "@tanstack/react-query";

import { fetchAstrologers } from "./astrologersApi";

// Roster changes rarely — fetched once as a lookup map (5 min staleTime)
// rather than re-fetched per ticket row.
export function useAstrologersLookup() {
  return useQuery({
    queryKey: ["admin", "astrologers"],
    queryFn: fetchAstrologers,
    staleTime: 5 * 60_000,
  });
}
