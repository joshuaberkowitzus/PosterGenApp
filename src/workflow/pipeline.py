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
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn

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

app = FastAPI()

class PosterRequest(BaseModel):
    gcs_input_bucket: str
    gcs_output_bucket: str
    pdf_path: str
    logo: Optional[str] = None
    aff_logo: Optional[str] = None
    text_model: str = "gpt-5-2025-08-07" #"gpt-4o-2024-08-06"
    multimodal_model: str = "gpt-5-2025-08-07" #"gpt-4o-2024-08-06"
    image_model: str = "gpt-image-1" #"dall-e-3"
    fast_llm_model: str = "gpt-5-mini-2025-08-07"
    fast_search: bool = False
    output_path: str = "poster.pptx"
    debug_mode: bool = False
    width: int = 42
    height: int = 28
    url: Optional[str] = None

@app.post("/generate-poster/")
async def generate_poster(request: PosterRequest):
    """
    API endpoint to generate a poster from a paper in GCS.
    """
    try:
        # Create a temporary directory to handle files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Download paper from GCS
            paper_local_path = temp_path / Path(request.pdf_path).name
            download_from_gcs(request.gcs_input_bucket, request.pdf_path, str(paper_local_path))

            # Download logos if provided
            logo_local_path = None
            if request.logo:
                logo_local_path = temp_path / Path(request.logo).name
                download_from_gcs(request.gcs_input_bucket, request.logo, str(logo_local_path))

            aff_logo_local_path = None
            if request.aff_logo:
                aff_logo_local_path = temp_path / Path(request.aff_logo).name
                download_from_gcs(request.gcs_input_bucket, request.aff_logo, str(aff_logo_local_path))

            # Prepare initial state for the workflow
            initial_state = create_state(
                pdf_path=str(paper_local_path),
                text_model=request.text_model,
                vision_model=request.text_model, # Corrected from multimodal_model
                logo_path=str(logo_local_path) if logo_local_path else "",
                aff_logo_path=str(aff_logo_local_path) if aff_logo_local_path else "",
                width=request.width,
                height=request.height,
                url=request.url
            )

            # Create and run the workflow
            graph = create_workflow_graph()
            app_graph = graph.compile()
            final_state = app_graph.invoke(initial_state)

            # Upload the final poster to GCS
            if "output_dir" in final_state and "poster_name" in final_state:
                output_dir = Path(final_state["output_dir"])
                poster_name = final_state["poster_name"]
                output_local_path = output_dir / f"{poster_name}.pptx"
                
                if output_local_path.exists():
                    # The destination path in GCS will be based on the poster name
                    destination_blob_name = f"{poster_name}.pptx"
                    upload_to_gcs(request.gcs_output_bucket, str(output_local_path), destination_blob_name)
                    final_gcs_path = f"gs://{request.gcs_output_bucket}/{destination_blob_name}"
                else:
                    raise HTTPException(status_code=500, detail=f"Generated poster file not found at path: {output_local_path}")
            else:
                # Log the state for debugging if the expected keys are missing
                log_agent_error("main", f"Workflow final state did not contain 'output_dir' or 'poster_name'. State: {final_state}")
                raise HTTPException(status_code=500, detail="Output file could not be determined from workflow state.")

            return {"status": "success", "output_path": final_gcs_path}

    except Exception as e:
        log_agent_error("main", f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def main():
    # This main function is now for local execution and debugging
    # The cloud execution will be handled by the FastAPI app
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
    # The server is started with Uvicorn.
    # The host is set to '0.0.0.0' to be accessible from outside the container.
    # The port is read from the PORT environment variable, which is set by Cloud Run.
    # A default of 8080 is used for local development.
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

