import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import type { FormEvent } from "react";

import { registerAcademy } from "./api";

export default function RegistrationForm() {
  const registration = useMutation({
    mutationFn: ({ details, secret }: {
      details: Parameters<typeof registerAcademy>[0];
      secret: string;
    }) => registerAcademy(details, secret)
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    registration.mutate({
      secret: String(data.get("operator_secret") ?? ""),
      details: {
        academy_name: String(data.get("academy_name") ?? ""),
        academy_phone: String(data.get("academy_phone") ?? ""),
        administrator_name: String(data.get("administrator_name") ?? ""),
        administrator_email: String(data.get("administrator_email") ?? ""),
        administrator_password: String(data.get("administrator_password") ?? "")
      }
    });
  }

  let errorMessage = "Could not register the academy. Please try again.";
  if (axios.isAxiosError(registration.error)) {
    const detail: unknown = registration.error.response?.data?.detail;
    if (typeof detail === "string") {
      errorMessage = detail;
    }
  }

  return (
    <main className="registration">
      <h1>Register an academy</h1>
      <section>
        <form onSubmit={submit}>
          <label htmlFor="operator-secret">Operator secret</label>
          <input id="operator-secret" name="operator_secret" type="password" required />
          <label htmlFor="academy-name">Academy name</label>
          <input id="academy-name" name="academy_name" required />
          <label htmlFor="academy-phone">Academy phone</label>
          <input id="academy-phone" name="academy_phone" type="tel" required />
          <label htmlFor="administrator-name">Administrator name</label>
          <input id="administrator-name" name="administrator_name" required />
          <label htmlFor="administrator-email">Administrator email</label>
          <input id="administrator-email" name="administrator_email" type="email" required />
          <label htmlFor="administrator-password">Administrator password</label>
          <input
            id="administrator-password"
            name="administrator_password"
            type="password"
            aria-describedby="password-requirements"
            required
          />
          <p id="password-requirements">
            At least 12 characters, an uppercase letter, a digit, and one of - ! # = ?.
          </p>
          <button type="submit" disabled={registration.isPending}>Register academy</button>
          {registration.isError ? <p role="alert">{errorMessage}</p> : null}
          {registration.isSuccess ? <p role="status">Academy registered.</p> : null}
        </form>
      </section>
    </main>
  );
}
