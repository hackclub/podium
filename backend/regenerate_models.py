#!/usr/bin/env python3
"""
Simple script to regenerate review factory models
"""

import httpx
import json
import subprocess
import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Regenerate review factory models from OpenAPI spec")
    parser.add_argument(
        "--url", 
        "-u", 
        type=str, 
        default="https://review-factory-backend.hackclub.com/openapi.json",
        help="OpenAPI spec URL (default: https://review-factory-backend.hackclub.com/openapi.json)"
    )
    args = parser.parse_args()
    
    url = args.url
    print(f"Downloading OpenAPI spec from {url}...")
    
    # Download the OpenAPI spec
    try:
        with httpx.Client() as client:
            response = client.get(url)
            response.raise_for_status()
            openapi_spec = response.json()
    except Exception as e:
        print(f"Error downloading OpenAPI spec: {e}")
        sys.exit(1)
    
    # Write to temp file
    with open("temp_openapi.json", "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    try:
        # Generate models
        cmd = [
            "uv", "run", "datamodel-codegen",
            "--input", "temp_openapi.json",
            "--input-file-type", "openapi",
            "--output", "podium/generated/review_factory_models.py",
            "--output-model-type", "pydantic_v2.BaseModel"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        print("Models generated successfully!")
        
    except subprocess.CalledProcessError as e:
        print(f"Error generating models: {e}")
        sys.exit(1)
    finally:
        # Clean up
        if os.path.exists("temp_openapi.json"):
            os.remove("temp_openapi.json")

if __name__ == "__main__":
    main() 