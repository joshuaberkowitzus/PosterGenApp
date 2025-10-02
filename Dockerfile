# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install uv, the python package installer
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    sh -c "$(curl -LsSf https://astral.sh/uv/install.sh)" && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.local/bin:$PATH"

# Install system dependencies, including LibreOffice and git
RUN apt-get update && apt-get install -y \
    libreoffice \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the application
CMD ["python", "-m", "src.workflow.pipeline"]
