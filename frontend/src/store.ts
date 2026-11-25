import { create } from "zustand";

type AppState = {
  academyName: string;
  setAcademyName: (academyName: string) => void;
};

export const useAppStore = create<AppState>((set) => ({
  academyName: "DanceHub Academy",
  setAcademyName: (academyName) => set({ academyName })
}));
