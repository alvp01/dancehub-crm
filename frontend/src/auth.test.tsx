import { act } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";
import { fetchHealthMessage } from "./api";
import SignInForm from "./SignInForm";

const http = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  config: undefined as unknown
}));

vi.mock("axios", () => ({
  default: {
    create: (config: unknown) => {
      http.config = config;
      return http;
    },
    isAxiosError: (error: unknown) =>
      typeof error === "object" && error !== null && "isAxiosError" in error
  }
}));

afterEach(() => {
  vi.clearAllMocks();
  document.body.innerHTML = "";
  window.history.replaceState({}, "", "/");
});

test("frontend_auth_requests_send_cookies", () => {
  expect(http.config).toMatchObject({ withCredentials: true });
});

test("app_renews_expired_access_and_retries_request", async () => {
  http.get
    .mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 401 }
    })
    .mockResolvedValueOnce({ data: { message: "DanceHub CRM is ready" } });
  http.post.mockResolvedValueOnce({ data: { message: "Session renewed." } });

  await expect(fetchHealthMessage()).resolves.toBe("DanceHub CRM is ready");

  expect(http.post).toHaveBeenCalledWith("/api/auth/refresh");
  expect(http.get).toHaveBeenCalledTimes(2);
  expect(http.get).toHaveBeenLastCalledWith("/api/health");
});

test("app_restores_crm_home_after_browser_reload_with_valid_cookie", async () => {
  document.body.innerHTML = '<div id="root"></div>';
  const container = document.getElementById("root")!;
  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  http.get.mockResolvedValueOnce({
    data: {
      name: "Jamie Chen",
      email: "jamie@example.com",
      academy_name: "Acme Dance Academy"
    }
  });

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  expect(container.textContent).toContain("Acme Dance Academy");
  expect(container.textContent).toContain("Jamie Chen");

  await act(async () => root.unmount());
});

test("signed_out_app_renders_email_and_password_fields", async () => {
  document.body.innerHTML = '<div id="root"></div>';
  const container = document.getElementById("root")!;
  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  http.post.mockRejectedValueOnce({
    isAxiosError: true,
    response: { status: 401 }
  });
  http.get.mockRejectedValueOnce({
    isAxiosError: true,
    response: { status: 401 }
  });

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  expect(container.querySelector('input[type="email"]')).not.toBeNull();
  expect(container.querySelector('input[type="password"]')).not.toBeNull();

  await act(async () => root.unmount());
});

test("sign_in_form_submits_credentials_and_returns_administrator_session", async () => {
  document.body.innerHTML = '<div id="root"></div>';
  const container = document.getElementById("root")!;
  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  const administrator = {
    name: "Jamie Chen",
    email: "jamie@example.com",
    academy_name: "Acme Dance Academy"
  };
  const onSignIn = vi.fn();
  http.post.mockResolvedValueOnce({ data: { message: "Signed in." } });
  http.get.mockResolvedValueOnce({ data: administrator });

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <SignInForm onSignIn={onSignIn} />
      </QueryClientProvider>
    );
  });

  (document.getElementById("email") as HTMLInputElement).value = "jamie@example.com";
  (document.getElementById("password") as HTMLInputElement).value = "DanceHub!2026";
  await act(async () => {
    container.querySelector("form")!.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true })
    );
  });

  expect(http.post).toHaveBeenCalledWith("/api/auth/login", {
    email: "jamie@example.com",
    password: "DanceHub!2026"
  });
  expect(http.get).toHaveBeenCalledWith("/api/auth/me");
  expect(onSignIn).toHaveBeenCalledWith(administrator);

  await act(async () => root.unmount());
});

test("sign_in_form_displays_generic_error_for_invalid_credentials", async () => {
  document.body.innerHTML = '<div id="root"></div>';
  const container = document.getElementById("root")!;
  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  http.post.mockRejectedValueOnce({
    isAxiosError: true,
    response: { status: 401 }
  });

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <SignInForm />
      </QueryClientProvider>
    );
  });
  (document.getElementById("email") as HTMLInputElement).value = "jamie@example.com";
  (document.getElementById("password") as HTMLInputElement).value = "wrong-password";
  await act(async () => {
    container.querySelector("form")!.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true })
    );
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  expect(container.querySelector('[role="alert"]')?.textContent).toBe(
    "Email or password is incorrect."
  );

  await act(async () => root.unmount());
});

test("successful_sign_in_displays_crm_home", async () => {
  document.body.innerHTML = '<div id="root"></div>';
  const container = document.getElementById("root")!;
  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  http.post
    .mockRejectedValueOnce({
      isAxiosError: true,
      response: { status: 401 }
    })
    .mockResolvedValueOnce({ data: { message: "Signed in." } });
  http.get
    .mockRejectedValueOnce({ isAxiosError: true, response: { status: 401 } })
    .mockResolvedValueOnce({
      data: {
        name: "Jamie Chen",
        email: "jamie@example.com",
        academy_name: "Acme Dance Academy"
      }
    })
    .mockResolvedValueOnce({ data: { message: "Backend is running" } });

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  (document.getElementById("email") as HTMLInputElement).value = "jamie@example.com";
  (document.getElementById("password") as HTMLInputElement).value = "DanceHub!2026";
  await act(async () => {
    container.querySelector("form")!.dispatchEvent(
      new Event("submit", { bubbles: true, cancelable: true })
    );
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  expect(container.textContent).toContain("Acme Dance Academy");
  expect(container.textContent).toContain("Jamie Chen");

  await act(async () => root.unmount());
});

test("signed_in_app_sign_out_returns_to_sign_in", async () => {
  document.body.innerHTML = '<div id="root"></div>';
  const container = document.getElementById("root")!;
  const root = createRoot(container);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });
  http.get
    .mockResolvedValueOnce({
      data: {
        name: "Jamie Chen",
        email: "jamie@example.com",
        academy_name: "Acme Dance Academy"
      }
    })
    .mockResolvedValueOnce({ data: { message: "Backend is running" } });
  http.post.mockResolvedValueOnce({ data: { message: "Signed out." } });

  await act(async () => {
    root.render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    );
  });
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  const signOutButton = Array.from(container.querySelectorAll("button")).find(
    (button) => button.textContent?.trim() === "Sign out"
  );
  expect(signOutButton).toBeDefined();
  await act(async () => {
    signOutButton!.dispatchEvent(new Event("click", { bubbles: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  expect(http.post).toHaveBeenCalledWith("/api/auth/logout");
  expect(container.textContent).toContain("Sign in to DanceHub");

  await act(async () => root.unmount());
});
