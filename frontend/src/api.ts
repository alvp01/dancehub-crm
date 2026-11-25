import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000"
});

export async function fetchHealthMessage(): Promise<string> {
  const response = await client.get<{ message: string }>("/api/health");
  return response.data.message;
}
