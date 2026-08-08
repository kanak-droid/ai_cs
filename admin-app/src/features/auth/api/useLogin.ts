import { useMutation } from "@tanstack/react-query";

import { api } from "../../../lib/apiClient";

interface LoginResponse {
  access_token: string;
  admin_id: number;
  name: string;
  email: string;
}

export function useLogin() {
  return useMutation({
    mutationFn: (credentials: { email: string; password: string }) =>
      api.post<LoginResponse>("/api/admin/login", credentials),
  });
}
