import { useQuery } from "@tanstack/react-query";

import { fetchHealthMessage } from "./api";
import RegistrationForm from "./RegistrationForm";
import { useAppStore } from "./store";

export default function App() {
  if (window.location.pathname === "/operator/register") {
    return <RegistrationForm />;
  }

  return <Home />;
}

function Home() {
  const academyName = useAppStore((state) => state.academyName);
  const healthQuery = useQuery({
    queryKey: ["health-message"],
    queryFn: fetchHealthMessage
  });

  return (
    <main>
      <p className="eyebrow">Dance academy CRM</p>
      <h1>{academyName}</h1>
      <section aria-live="polite">
        {healthQuery.isPending && <p>Connecting to the backend...</p>}
        {healthQuery.isError && <p>Could not reach the backend.</p>}
        {healthQuery.data && <p>{healthQuery.data}</p>}
      </section>
    </main>
  );
}
