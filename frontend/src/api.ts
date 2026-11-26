import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true
});

export async function fetchHealthMessage(): Promise<string> {
  const message = await getWithSessionRefresh<{ message: string }>("/api/v1/health");
  return message.message;
}

async function getWithSessionRefresh<T>(url: string): Promise<T> {
  try {
    const response = await client.get<T>(url);
    return response.data;
  } catch (error) {
    if (!axios.isAxiosError(error) || error.response?.status !== 401) {
      throw error;
    }
    await client.post("/api/v1/auth/refresh");
    const response = await client.get<T>(url);
    return response.data;
  }
}

export interface AdministratorSession {
  name: string;
  email: string;
  academy_name: string;
}

export async function fetchAdministratorSession(): Promise<AdministratorSession | null> {
  try {
    return await getWithSessionRefresh<AdministratorSession>("/api/v1/auth/me");
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
  await client.post("/api/v1/auth/login", credentials);
  const session = await fetchAdministratorSession();
  if (!session) {
    throw new Error("Sign-in did not establish an administrator session.");
  }
  return session;
}

export async function signOutAdministrator(): Promise<void> {
  await client.post("/api/v1/auth/logout");
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
  await client.post("/api/v1/operator/registration", details, {
    headers: { "X-Operator-Secret": operatorSecret }
  });
}
