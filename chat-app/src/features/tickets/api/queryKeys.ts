export const ticketsKeys = {
  list: () => ["tickets", "list"] as const,
  detail: (id: number) => ["tickets", "detail", id] as const,
};
