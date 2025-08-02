# PosterGen: A Multi-Agent Framework for Aesthetic-Aware Paper-to-Poster Generation

> Zhilin Zhang, Xiang Zhang, Jiaqi Wei, Yiwei Xu, Chenyu You 

![](./resource/method.png)

In this work, we propose a new multi-agent framework that is guided by the design principles. Our multi-agent system adopts a workflow of specialist agents that mirrors a professional design process. It begins with a **Parser Agent** that extracts and structures all content from the source paper. Following this, the **Curator Agent** designs a narrative-based storyboard, which the **Layout Agent** then transforms into a spatially balanced, three-column layout. The **Styling Agents** subsequently apply a harmonious color palette and a hierarchical typographic system to ensure aesthetic coherence. This methodology is designed to generate a well-designed poster that minimizes the need for manual fine-tuning.

## 🚀 Quick Start

### System Requirements
- **Operating System**: Linux or macOS (Windows not supported)
- **Python Version**: 3.11 (required)

### 1. Environment Setup

```bash
# Create and activate conda environment
conda create -n poster python=3.11 -y
conda activate poster
pip install -r requirements.txt
cd PosterGen

# Install marker for PDF parser
git clone https://github.com/Hadlay-Zhang/marker
cd marker && pip install -e . && cd ../
```

### 2. Install LibreOffice (Required for PPTX generation)

```bash
# macOS
brew install --cask libreoffice

# Ubuntu/Linux
sudo apt install libreoffice
```

### 3. API Keys Configuration

Create a `.env` file in the project root with your API keys:

```bash
OPENAI_API_KEY="your_openai_key"     # Primary
ANTHROPIC_API_KEY="your_anthropic_key"
```

## Data Structure Setup

Before running the multi-agent pipeline, organize your files in the `data/` folder:

```
data/
└── <your_paper_name>/
    ├── paper.pdf          # Your research paper (required)
    ├── aff.png           # Affiliation logo for color extraction (required)
    └── logo.png          # Conference logo for poster (required)
```

**Examples (check ``data/`` folder):**
```
data/
└── Neural_Encoding_and_Decoding_at_Scale/
    ├── paper.pdf
    ├── aff.png
    └── logo.png
└── ...
```

## 🎯 Usage

Generate your poster with a single command:

```bash
python -m src.workflow.pipeline \
  --poster_width 54 --poster_height 36 \
  --paper_path ./data/Your_Paper_Name/paper.pdf \
  --text_model gpt-4.1-2025-04-14 \
  --vision_model gpt-4.1-2025-04-14 \
  --logo ./data/Your_Paper_Name/logo.png \
  --aff_logo ./data/Your_Paper_Name/aff.png
```

**Parameters:**
- `--poster_width/height`: Poster dimensions in inches, with aspect ratio (w/h): lower bound 1.4 (ISO A paper size), upper bound 2 (human vision limit)
- `--paper_path`: Path to your PDF paper
- `--text_model`: LLM for text processing (options: "gpt-4.1-2025-04-14" (default), "gpt-4o-2024-08-06", "gpt-4.1-mini-2025-04-14", "claude-sonnet-4-20250514")
- `--vision_model`: Vision model for analysis (same options as text_model)
- `--logo`: Your institution/lab logo
- `--aff_logo`: Affiliation logo (used for color scheme extraction)

## Output Structure

After successful generation, you'll find your results in the `output/` folder:

```
output/
└── <paper_name>/
    ├── <paper_name>.png           # final poster image
    ├── <paper_name>.pptx          # editable PowerPoint file
    ├── assets/                    # extracted content from paper via Marker
    │   ├── figures.json           # figure metadata with aspect ratios
    │   ├── tables.json            # table metadata with aspect ratios
    │   ├── figure-*.png           # individual figures from paper
    │   ├── table-*.png            # individual tables from paper
    │   └── fig_tab_caption_mapping.json  # caption mappings
    └── content/                   # processing artifacts
        ├── raw.md                         # raw text extraction
        ├── structured_sections.json      # organized sections
        ├── classified_visuals.json       # categorized visuals
        ├── narrative_content.json        # paper summary
        ├── story_board.json              # content organization
        ├── initial_layout_data.json      # initial layout
        ├── column_analysis.json          # column usage stats
        ├── optimized_story_board.json    # balanced content
        ├── balancer_decisions.json       # optimization details
        ├── final_column_analysis.json    # final usage metrics
        ├── optimized_layout.json         # balanced layout
        ├── final_design_layout.json      # element coordinates
        ├── color_scheme.json             # color palette
        ├── section_title_design.json     # title styling
        ├── keywords.json                  # highlighted terms
        ├── styled_layout.json            # formatted text
        └── styling_interfaces.json       # typography settings
```

## 🤖 Multi-Agent Pipeline

Our system uses 6 specialized AI agents working together:

1. **Parser Agent**: Extracts and structures content from paper PDF
2. **Curator Agent**: Plans content organization and visual placement  
3. **Layout Agent**: Calculates precise positioning and spacing
    - **Balancer Sub-Agent**: Optimizes column utilization and prevents overflow
5. **Color Agent**: Generates cohesive color schemes from your affiliation logo
7. **Font Agent**: Applies typography and keyword highlighting
8. **Renderer**: Generates final PowerPoint and image files

## Key Features

- **Professional Layout**: CSS-like precision positioning with proper spacing
- **Intelligent Balancing**: Automatic column optimization prevents overflow
- **Color Harmony**: Automatic color scheme generation from your institution branding
- **Typography Excellence**: Professional font choices and keyword highlighting
- **Flexible Output**: Both PNG images and editable PowerPoint files
- **Academic Standards**: Follows poster design best practices for conferences

## Other Configurations

The system supports customization through `config/poster_config.yaml`. You can adjust:

- Layout parameters (margins, padding, spacing)
- Typography settings (fonts, sizes, line spacing)
- Color generation algorithms
- Visual asset sizing constraints
- Content optimization thresholds

## 📊 Example Results

Our system generates professional academic posters with high visual quality. Here are some examples of generated posters:

![Example 1](./resource/neural-encoding.png)

![Example 2](./resource/active-geo.png)

## 🙏 Acknowledgments

This codebase is built upon following open-source projects. We express our sincere gratitude to:

- **[LangGraph](https://github.com/langchain-ai/langgraph)**: Multi-agent workflow orchestration framework;
- **[Marker](https://github.com/datalab-to/marker)**: High-quality PDF parsing library that enables accurate content extraction from research papers in our work.

<!-- ## Quality Evaluation -->

<!-- ## Citation -->