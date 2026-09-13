import axios from "axios";

// Lecture de l'URL injectée dynamiquement par le Hub dans window.API_URL
const getBaseUrl = () => {
  // @ts-ignore
  if (window.API_URL) return window.API_URL;
  return import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
};

export const api = axios.create({
  baseURL: getBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

export interface Prospect {
  id: number;
  nom_entreprise?: string;
  entreprise?: string;
  contact_nom?: string;
  contact?: string;
  nom?: string;
  email: string;
  statut: string;
  pitch_genere?: string;
  pitch_commercial?: string;
}

export const getProspects = async (): Promise<Prospect[]> => {
  const response = await api.get("/prospects");
  return response.data;
};

export const importProspectsCSV = async (file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/prospects/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const genererPitch = async (id: number) => {
  const response = await api.post(`/prospects/${id}/generate`);
  return response.data;
};

export const updatePitch = async (id: number, pitch_genere: string) => {
  const response = await api.put(`/prospects/${id}/pitch`, { pitch_genere });
  return response.data;
};

export const deleteDraft = async (id: number) => {
  const response = await api.delete(`/prospects/${id}/draft`);
  return response.data;
};

export const deleteProspect = async (id: number) => {
  const response = await api.delete(`/prospects/${id}`);
  return response.data;
};