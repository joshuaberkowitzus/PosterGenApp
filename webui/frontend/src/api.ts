import axios from 'axios';
import { GeneratePosterResponse, PosterFormState } from './types';

const CLOUD_RUN_BASE_URL = 'https://postergen-backend-367063486603.us-east4.run.app';
const resolvedEnv =
  typeof import.meta !== 'undefined' && 'env' in import.meta
    ? (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env
    : undefined;
const API_BASE = resolvedEnv?.VITE_API_BASE_URL ?? CLOUD_RUN_BASE_URL;

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15 * 60 * 1000, // allow up to 15 minutes for poster generation
});

const buildPayload = (form: PosterFormState) => {
  const payload: Record<string, unknown> = {
    gcs_input_bucket: form.gcs_input_bucket.trim(),
    gcs_output_bucket: form.gcs_output_bucket.trim(),
    pdf_path: form.pdf_path.trim(),
    text_model: form.text_model.trim(),
    multimodal_model: form.multimodal_model.trim(),
    image_model: form.image_model.trim(),
    fast_llm_model: form.fast_llm_model.trim(),
    fast_search: form.fast_search,
    output_path: form.output_path.trim(),
    debug_mode: form.debug_mode,
    width: Number(form.width),
    height: Number(form.height),
  };

  const optionalMappings: Array<[keyof PosterFormState, string]> = [
    ['logo', 'logo'],
    ['aff_logo', 'aff_logo'],
    ['url', 'url'],
  ];

  optionalMappings.forEach(([field, key]) => {
    const value = form[field];
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed) {
        payload[key] = trimmed;
      }
    }
  });

  return payload;
};

export const apiService = {
  async generatePoster(form: PosterFormState): Promise<GeneratePosterResponse> {
    const response = await api.post<GeneratePosterResponse>('/generate-poster/', buildPayload(form), {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return response.data;
  },
};