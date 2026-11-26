import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true
});

export async function fetchHealthMessage(): Promise<string> {
  const response = await client.get<{ message: string }>("/api/health");
  return response.data.message;
}

export interface AdministratorSession {
  name: string;
  email: string;
  academy_name: string;
}

export async function fetchAdministratorSession(): Promise<AdministratorSession | null> {
  try {
    const response = await client.get<AdministratorSession>("/api/auth/me");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      return null;
    }
    throw error;
  }
}

export async function signInAdministrator(credentials: {
  email: string;
  password: string;
}): Promise<AdministratorSession> {
  await client.post("/api/auth/login", credentials);
  const session = await fetchAdministratorSession();
  if (!session) {
    throw new Error("Sign-in did not establish an administrator session.");
  }
  return session;
}

export interface RegistrationDetails {
  academy_name: string;
  academy_phone: string;
  administrator_name: string;
  administrator_email: string;
  administrator_password: string;
}

export async function registerAcademy(
  details: RegistrationDetails,
  operatorSecret: string
): Promise<void> {
  await client.post("/api/operator/registration", details, {
    headers: { "X-Operator-Secret": operatorSecret }
  });
}
