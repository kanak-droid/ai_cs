import { useQuery } from "@tanstack/react-query";

import { fetchFeedbackCalls } from "./feedbackCallsApi";

import type { FeedbackCallFilters } from "./feedbackCallsApi";

export function useFeedbackCalls(filters: FeedbackCallFilters = {}) {
  return useQuery({
    queryKey: ["admin", "feedback-calls", filters],
    queryFn: () => fetchFeedbackCalls(filters),
    refetchInterval: 20_000,
  });
}
