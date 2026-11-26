import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000"
});

export async function fetchHealthMessage(): Promise<string> {
  const response = await client.get<{ message: string }>("/api/health");
  return response.data.message;
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
