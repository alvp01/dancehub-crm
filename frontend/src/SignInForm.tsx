import { useMutation } from "@tanstack/react-query";
import type { FormEvent } from "react";

import { signInAdministrator, type AdministratorSession } from "./api";

export default function SignInForm({
  onSignIn
}: {
  onSignIn?: (session: AdministratorSession) => void;
} = {}) {
  const signIn = useMutation({
    mutationFn: signInAdministrator,
    onSuccess: (session) => onSignIn?.(session)
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    signIn.mutate({
      email: String(data.get("email") ?? ""),
      password: String(data.get("password") ?? "")
    });
  }

  return (
    <main>
      <section>
        <h1>Sign in to DanceHub</h1>
        <form onSubmit={submit}>
          <label htmlFor="email">Email</label>
          <input id="email" name="email" type="email" autoComplete="username" required />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
          <button type="submit" disabled={signIn.isPending}>Sign in</button>
          {signIn.isError && <p role="alert">Email or password is incorrect.</p>}
        </form>
      </section>
    </main>
  );
}
