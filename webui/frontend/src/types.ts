export interface PosterFormState {
  gcs_input_bucket: string;
  gcs_output_bucket: string;
  pdf_path: string;
  logo: string;
  aff_logo: string;
  text_model: string;
  multimodal_model: string;
  image_model: string;
  fast_llm_model: string;
  fast_search: boolean;
  output_path: string;
  debug_mode: boolean;
  width: number;
  height: number;
  url: string;
}

export interface GeneratePosterResponse {
  status: string;
  output_path: string;
}