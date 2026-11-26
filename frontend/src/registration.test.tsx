import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";

const http = vi.hoisted(() => ({
  post: vi.fn(),
  get: vi.fn()
}));

vi.mock("axios", () => ({
  default: {
    create: () => http,
    isAxiosError: (error: unknown) =>
      typeof error === "object" && error !== null && "isAxiosError" in error
  }
}));

afterEach(() => {
  vi.clearAllMocks();
  document.body.innerHTML = "";
  window.history.replaceState({}, "", "/");
});

test("registration form submits details and displays server errors and success", async () => {
  window.history.replaceState({}, "", "/operator/register");
  document.body.innerHTML = '<div id="root"></div>';
  const container = document.getElementById("root")!;
  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  http.post
    .mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 422, data: { detail: "Password needs an uppercase letter." } }
    })
    .mockResolvedValueOnce({ data: {} });

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );
  });

  const values = {
    "Operator secret": "test-operator-secret",
    "Academy name": "Acme Dance Academy",
    "Academy phone": "+1-555-555-0100",
    "Administrator name": "Jamie Chen",
    "Administrator email": "jamie@example.com",
    "Administrator password": "DanceHub!2026"
  };
  for (const [labelText, value] of Object.entries(values)) {
    const label = Array.from(container.querySelectorAll("label")).find(
      (element) => element.textContent?.trim() === labelText
    );
    expect(label, `Missing label: ${labelText}`).toBeDefined();
    const input = document.getElementById(label!.htmlFor);
    expect(input).toBeInstanceOf(HTMLInputElement);
    (input as HTMLInputElement).value = value;
  }

  const form = container.querySelector("form");
  expect(form).not.toBeNull();
  await act(async () => {
    form!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });

  expect(http.post).toHaveBeenCalledWith(
    "/api/operator/registration",
    {
      academy_name: "Acme Dance Academy",
      academy_phone: "+1-555-555-0100",
      administrator_name: "Jamie Chen",
      administrator_email: "jamie@example.com",
      administrator_password: "DanceHub!2026"
    },
    { headers: { "X-Operator-Secret": "test-operator-secret" } }
  );
  expect(container.textContent).toContain("Password needs an uppercase letter.");

  await act(async () => {
    form!.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  });
  expect(container.textContent).toContain("Academy registered");

  await act(async () => root.unmount());
});
