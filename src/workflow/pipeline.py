"""
Main workflow pipeline for paper-to-poster generation
"""

import argparse
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from google.cloud import secretmanager
from google.cloud import storage
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# langgraph imports
from langgraph.graph import StateGraph, START, END

from src.state.poster_state import create_state, PosterState
from src.agents.parser import parser_node
from src.agents.curator import curator_node
from src.agents.layout_with_balancer import layout_with_balancer_node as layout_optimizer_node
from src.agents.section_title_designer import section_title_designer_node
from src.agents.color_agent import color_agent_node
from src.agents.font_agent import font_agent_node
from src.agents.renderer import renderer_node
from utils.src.logging_utils import log_agent_info, log_agent_success, log_agent_error

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Get the GCP Project ID from environment variables
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")

def get_secret(secret_id, version_id="latest"):
    """
    Get information about the given secret version.
    """
    if not GCP_PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID environment variable not set.")
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")

def download_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)
    print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

def create_workflow_graph() -> StateGraph:
    """create the langgraph workflow"""
    graph = StateGraph(PosterState)
    
    # add all nodes in the workflow
    graph.add_node("parser", parser_node)
    graph.add_node("curator", curator_node)
    graph.add_node("color_agent", color_agent_node)
    graph.add_node("section_title_designer", section_title_designer_node)
    graph.add_node("layout_optimizer", layout_optimizer_node)
    graph.add_node("font_agent", font_agent_node)
    graph.add_node("renderer", renderer_node)
    
    # workflow: parser -> story board -> color -> title design -> layout -> font -> render
    graph.add_edge(START, "parser")
    graph.add_edge("parser", "curator")
    graph.add_edge("curator", "color_agent")
    graph.add_edge("color_agent", "section_title_designer")
    graph.add_edge("section_title_designer", "layout_optimizer")
    graph.add_edge("layout_optimizer", "font_agent")
    graph.add_edge("font_agent", "renderer")
    graph.add_edge("renderer", END)
    
    return graph


def main():
    parser = argparse.ArgumentParser(description="PosterGen: Multi-agent Aesthetic-aware Paper-to-poster generation")
    # GCS arguments
    parser.add_argument("--gcs_input_bucket", type=str, help="GCS bucket for input files")
    parser.add_argument("--gcs_output_bucket", type=str, help="GCS bucket for output files")
    parser.add_argument("--paper_path", type=str, help="Path to the PDF paper in GCS (e.g., your_paper_name/paper.pdf)")
    parser.add_argument("--logo", type=str, help="Path to conference/journal logo in GCS (e.g., your_paper_name/logo.png)")
    parser.add_argument("--aff_logo", type=str, help="Path to affiliation logo in GCS (e.g., your_paper_name/aff.png)")

    parser.add_argument("--text_model", type=str, default="gpt-4o-2024-08-06", 
                       choices=["gpt-4o-2024-08-06", "gpt-4.1-2025-04-14", "gpt-4.1-mini-2025-04-14", "claude-sonnet-4-20250514", "gemini-2.5-pro", "glm-4.5", "glm-4.5-air", "glm-4"],
                       help="Text model for content processing")
    parser.add_argument("--vision_model", type=str, default="gpt-4o-2024-08-06",
                       choices=["gpt-4o-2024-08-06", "gpt-4.1-2025-04-14", "gpt-4.1-mini-2025-04-14", "claude-sonnet-4-20250514", "gemini-2.5-pro", "glm-4.5v", "glm-4v"],
                       help="Vision model for image analysis")
    parser.add_argument("--poster_width", type=float, default=54, help="Poster width in inches")
    parser.add_argument("--poster_height", type=float, default=36, help="Poster height in inches")
    parser.add_argument("--url", type=str, help="URL for QR code on poster")
    
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        local_paper_path = None
        if args.gcs_input_bucket and args.paper_path:
            local_paper_path = os.path.join(temp_dir, "paper.pdf")
            download_from_gcs(args.gcs_input_bucket, args.paper_path, local_paper_path)
        elif args.paper_path:
             local_paper_path = args.paper_path

        local_logo_path = None
        if args.gcs_input_bucket and args.logo:
            local_logo_path = os.path.join(temp_dir, "logo.png")
            download_from_gcs(args.gcs_input_bucket, args.logo, local_logo_path)
        elif args.logo:
            local_logo_path = args.logo

        local_aff_logo_path = None
        if args.gcs_input_bucket and args.aff_logo:
            local_aff_logo_path = os.path.join(temp_dir, "aff.png")
            download_from_gcs(args.gcs_input_bucket, args.aff_logo, local_aff_logo_path)
        elif args.aff_logo:
            local_aff_logo_path = args.aff_logo

        # poster dimensions: fix width to 54", adjust height by ratio
        input_ratio = args.poster_width / args.poster_height
        # check poster ratio: lower bound 1.4 (ISO A paper size), upper bound 2 (human vision limit)
        if input_ratio > 2 or input_ratio < 1.4:
            print(f"❌ Poster ratio is out of range: {input_ratio}. Please use a ratio between 1.4 and 2.")
            return 1
        
        final_width = 54.0
        final_height = final_width / input_ratio
        
        # check api keys
        api_keys = {}
        required_keys = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY", "zhipu": "ZHIPU_API_KEY"}
        model_providers = {"claude-sonnet-4-20250514": "anthropic", "gemini": "google", "gemini-2.5-pro": "google",
                          "gpt-4o-2024-08-06": "openai", "gpt-4.1-2025-04-14": "openai", "gpt-4.1-mini-2025-04-14": "openai",
                          "glm-4.5": "zhipu", "glm-4.5-air": "zhipu", "glm-4.5v": "zhipu", "glm-4": "zhipu", "glm-4v": "zhipu"}
        
        needed_keys = set()
        if args.text_model in model_providers:
            needed_keys.add(required_keys[model_providers[args.text_model]])
        if args.vision_model in model_providers:
            needed_keys.add(required_keys[model_providers[args.vision_model]])
        
        missing_keys = []
        for key in needed_keys:
            try:
                if GCP_PROJECT_ID:
                    api_keys[key] = get_secret(key)
                else:
                    api_keys[key] = os.getenv(key)
                if not api_keys[key]:
                    missing_keys.append(key)
            except Exception as e:
                print(f"Could not retrieve secret {key}: {e}")
                # Fallback to environment variables if Secret Manager fails
                api_key_val = os.getenv(key)
                if api_key_val:
                    api_keys[key] = api_key_val
                else:
                    missing_keys.append(key)

        if missing_keys:
            print(f"❌ Missing API keys: {missing_keys}")
            return 1
        
        # get pdf path
        if not local_paper_path or not Path(local_paper_path).exists():
            print("❌ PDF not found")
            return 1
        
        print(f"🚀 PosterGen Pipeline")
        print(f"📄 PDF: {local_paper_path}")
        print(f"🤖 Models: {args.text_model}/{args.vision_model}")
        print(f"📏 Size: {final_width}\" × {final_height:.2f}\"")
        print(f"🏢 Conference Logo: {local_logo_path}")
        print(f"🏫 Affiliation Logo: {local_aff_logo_path}")
        
        try:
            # create poster state
            state = create_state(
                local_paper_path, args.text_model, args.vision_model, 
                final_width, final_height, 
                args.url, local_logo_path, local_aff_logo_path,
            )
            
            log_agent_info("pipeline", "creating workflow graph")
            graph = create_workflow_graph()
            workflow = graph.compile()
            
            log_agent_info("pipeline", "executing workflow")
            final_state = workflow.invoke(state)

            if final_state.get("errors"):
                log_agent_error("pipeline", f"Pipeline errors: {final_state['errors']}")
                return 1
            required_outputs = ["story_board", "design_layout", "color_scheme", "styled_layout"]
            missing = [out for out in required_outputs if not final_state.get(out)]
            if missing:
                log_agent_error("pipeline", f"Missing outputs: {missing}")
                return 1
            
            log_agent_success("pipeline", "Pipeline completed successfully")

            # full pipeline summary
            log_agent_success("pipeline", "Full pipeline complete")
            log_agent_info("pipeline", f"Total tokens: {final_state['tokens'].input_text} → {final_state['tokens'].output_text}")
            
            output_dir = Path(final_state["output_dir"])
            if args.gcs_output_bucket:
                for file_path in output_dir.rglob('*'):
                    if file_path.is_file():
                        destination_blob_name = f"{final_state['poster_name']}/{file_path.relative_to(output_dir)}"
                        upload_to_gcs(args.gcs_output_bucket, str(file_path), destination_blob_name)
            
            output_path = output_dir / f"{final_state['poster_name']}.pptx"
            log_agent_info("pipeline", f"Final poster saved to: {output_path}")
            
            return 0
            
        except Exception as e:
            log_agent_error("pipeline", f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    sys.exit(main())
