import { useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchAdministratorSession,
  fetchHealthMessage,
  type AdministratorSession
} from "./api";
import RegistrationForm from "./RegistrationForm";
import SignInForm from "./SignInForm";

export default function App() {
  if (window.location.pathname === "/operator/register") {
    return <RegistrationForm />;
  }

  return <AdministratorApp />;
}

function AdministratorApp() {
  const queryClient = useQueryClient();
  const sessionQuery = useQuery({
    queryKey: ["administrator-session"],
    queryFn: fetchAdministratorSession,
    retry: false
  });

  if (sessionQuery.isPending) {
    return <main><p>Checking your sign-in...</p></main>;
  }

  if (sessionQuery.isError) {
    return <main><p role="alert">Could not verify your sign-in.</p></main>;
  }

  if (!sessionQuery.data) {
    return (
      <SignInForm
        onSignIn={(administrator) =>
          queryClient.setQueryData(["administrator-session"], administrator)
        }
      />
    );
  }

  return <Home administrator={sessionQuery.data} />;
}

function Home({ administrator }: { administrator: AdministratorSession }) {
  const healthQuery = useQuery({
    queryKey: ["health-message"],
    queryFn: fetchHealthMessage
  });

  return (
    <main>
      <p className="eyebrow">Dance academy CRM</p>
      <h1>{administrator.academy_name}</h1>
      <p>Signed in as {administrator.name}</p>
      <section aria-live="polite">
        {healthQuery.isPending && <p>Connecting to the backend...</p>}
        {healthQuery.isError && <p>Could not reach the backend.</p>}
        {healthQuery.data && <p>{healthQuery.data}</p>}
      </section>
    </main>
  );
}
