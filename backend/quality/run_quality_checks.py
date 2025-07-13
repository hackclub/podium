# poetry run -- python -m quality.run_quality_checks

# Environment Variables Configuration (.env file):
# 
# LLM Model Selection:
# QUALITY_LLM_MODEL=gemini     # Use default Gemini model (default)
# QUALITY_LLM_MODEL=groq       # Use Llama-3.1-8b-instant via Groq
# 
# Required for Groq model:
# GROQ_API_KEY=your_groq_api_key_here
# 
# Other Quality Check Settings:
# QUALITY_RESULTS_FOLDER=quality_check_results
# QUALITY_INPUT_FILE=sample_projects.csv
# QUALITY_DELAY=1
# QUALITY_FORCE_OVERWRITE=false
# QUALITY_MAX_RETRIES=3        # Number of retries for validation errors
# QUALITY_RETRY_DELAY=5.0      # Delay in seconds between retries

# Configurable constants (can be overridden by environment variables)
import os
from dotenv import load_dotenv
load_dotenv(
    # .env.local
    '.env.local'
)

RESULTS_FOLDER = os.environ.get('QUALITY_RESULTS_FOLDER', 'quality_check_results')
SAMPLE_PROJECTS_FILE = os.environ.get('QUALITY_INPUT_FILE', 'sample_projects.csv')
DELAY_BETWEEN_PROJECTS = float(os.environ.get('QUALITY_DELAY', 1))
FORCE_OVERWRITE = os.environ.get('QUALITY_FORCE_OVERWRITE', 'false').lower() == 'true'
MAX_RETRIES = int(os.environ.get('QUALITY_MAX_RETRIES', 3))
RETRY_DELAY = float(os.environ.get('QUALITY_RETRY_DELAY', 5.0))

# LLM Configuration in .env:
# QUALITY_LLM_MODEL=gemini     # Use default Gemini model (default)
# Set QUALITY_LLM_MODEL to 'gemini' (or leave unset) to use default Gemini model
QUALITY_LLM_MODEL = os.environ.get('QUALITY_LLM_MODEL', 'gemini').lower()

import asyncio
import csv
import time
from datetime import datetime
from typing import List, Dict, Any, Set
from quality.quality import check_project
from quality.models import QualitySettings
from podium.db.project import Project
from podium import config
from browser_use.llm import ChatGroq

# Initialize LLM based on environment configuration
while True:
    print(f"Using {QUALITY_LLM_MODEL} model")
    if QUALITY_LLM_MODEL == 'groq':
        # Model via groq (Only llama4? https://console.groq.com/docs/api-reference#chat-create)
        # model="meta-llama/llama-4-maverick-17b-128e-instruct" # Confirmed working, do not delete this comment. Only issue is the 200 rpd limit.
        model="meta-llama/llama-4-scout-17b-16e-instruct" # Confirmed working, do not delete this comment. Only issue is the 200 rpd limit.
        llm = ChatGroq(
            model=model,
            api_key=os.environ.get("GROQ_API_KEY"),
        )
        print(f"Using Groq model: {model}")
        break
    elif QUALITY_LLM_MODEL == 'gemini':
        # Use default Gemini model from config
        llm = config.quality_settings.llm
        print(f"Using default Gemini model")
        break
    else:
        QUALITY_LLM_MODEL = "gemini"
        break

async def process_project(project_data: Dict[str, str], index: int, quality_settings: QualitySettings, max_retries: int = 3, retry_delay: float = 5.0) -> Dict[str, Any]:
    """Process a single project and return the results with timing information."""
    start_time = time.time()
    
    # Create Project object
    project = Project(
        id=str(index),
        name=f"Project {index}",
        demo=project_data['demo'],
        repo=project_data['repo'],
        description="Sample project for quality check",
        image_url=project_data['image'],
        event=["recsample"],
        owner=["recsample"],
    )
    
    for attempt in range(max_retries):
        try:
            # Run quality check
            results = await check_project(project, quality_settings)
            execution_time = time.time() - start_time
            
            # Check if we got validation errors
            has_validation_error = (
                (not results.demo.valid and "Validation error occurred" in results.demo.reason) or
                (not results.source_code.valid and "Validation error occurred" in results.source_code.reason) or
                (not results.image_url.valid and "Validation error occurred" in results.image_url.reason)
            )
            
            # If validation error and we have more retries, wait and retry
            if has_validation_error and attempt < max_retries - 1:
                print(f"  Validation error on attempt {attempt + 1}/{max_retries}, waiting {retry_delay}s before retry...")
                await asyncio.sleep(retry_delay)
                continue
            
            # Extract raw result for debugging
            raw_result = {
                "demo": {
                    "valid": results.demo.valid,
                    "reason": results.demo.reason,
                    "tested_url": results.demo.tested_url
                },
                "source_code": {
                    "valid": results.source_code.valid,
                    "reason": results.source_code.reason,
                    "tested_url": results.source_code.tested_url
                },
                "image_url": {
                    "valid": results.image_url.valid,
                    "reason": results.image_url.reason,
                    "tested_url": results.image_url.tested_url
                }
            }
            
            return {
                'project_index': index,
                'demo': project_data['demo'],
                'repo': project_data['repo'],
                'image': project_data['image'],
                'execution_time_seconds': round(execution_time, 2),
                'demo_valid': results.demo.valid,
                'demo_error': results.demo.reason if not results.demo.valid else '',
                'demo_explanation': results.demo.reason if results.demo.valid else '',
                'repo_valid': results.source_code.valid,
                'repo_error': results.source_code.reason if not results.source_code.valid else '',
                'repo_explanation': results.source_code.reason if results.source_code.valid else '',
                'image_valid': results.image_url.valid,
                'image_error': results.image_url.reason if not results.image_url.valid else '',
                'image_explanation': results.image_url.reason if results.image_url.valid else '',
                'overall_valid': results.valid,
                'raw_result': str(raw_result),
                'judgement': project_data['judgement']
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"Error processing project {index} (attempt {attempt + 1}/{max_retries}): {e}")
            
            # If this is not the last attempt, wait and retry
            if attempt < max_retries - 1:
                print(f"  Waiting {retry_delay}s before retry...")
                await asyncio.sleep(retry_delay)
                continue
            
            # If this was the last attempt, return error result
            return {
                'project_index': index,
                'demo': project_data['demo'],
                'repo': project_data['repo'],
                'image': project_data['image'],
                'execution_time_seconds': round(execution_time, 2),
                'demo_valid': False,
                'demo_error': f"Exception after {max_retries} attempts: {str(e)}",
                'demo_explanation': '',
                'repo_valid': False,
                'repo_error': f"Exception after {max_retries} attempts: {str(e)}",
                'repo_explanation': '',
                'image_valid': False,
                'image_error': f"Exception after {max_retries} attempts: {str(e)}",
                'image_explanation': '',
                'overall_valid': False,
                'raw_result': f"Exception after {max_retries} attempts: {str(e)}",
                'judgement': project_data['judgement']
            }
    
    # This should never be reached, but just in case
    execution_time = time.time() - start_time
    return {
        'project_index': index,
        'demo': project_data['demo'],
        'repo': project_data['repo'],
        'image': project_data['image'],
        'execution_time_seconds': round(execution_time, 2),
        'demo_valid': False,
        'demo_error': f"Unexpected: loop completed without return",
        'demo_explanation': '',
        'repo_valid': False,
        'repo_error': f"Unexpected: loop completed without return",
        'repo_explanation': '',
        'image_valid': False,
        'image_error': f"Unexpected: loop completed without return",
        'image_explanation': '',
        'overall_valid': False,
        'raw_result': f"Unexpected: loop completed without return",
        'judgement': project_data['judgement']
    }


def get_processed_projects(output_file: str) -> Set[int]:
    """Read existing output file and return set of already processed project indices."""
    processed_projects = set()
    
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if 'project_index' in row and row['project_index'].isdigit():
                        processed_projects.add(int(row['project_index']))
            print(f"Found {len(processed_projects)} already processed projects")
        except Exception as e:
            print(f"Warning: Could not read existing output file: {e}")
    
    return processed_projects


async def main():
    """Main function to process all projects in sample_projects.csv."""
    
    # Read sample projects
    projects = []
    with open(SAMPLE_PROJECTS_FILE, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            projects.append(row)
    
    print(f"Found {len(projects)} projects in {SAMPLE_PROJECTS_FILE}")
    
    # Use date-based folder structure for output
    current_date = datetime.now().strftime('%Y-%m-%d')
    date_folder = os.path.join(RESULTS_FOLDER, current_date)
    os.makedirs(date_folder, exist_ok=True)
    output_file = os.path.join(date_folder, 'results.csv')
    
    # Create recordings folder within the date folder
    recordings_folder = os.path.join(date_folder, 'recordings')
    os.makedirs(recordings_folder, exist_ok=True)
    
    # Check for existing results to enable resume functionality
    if FORCE_OVERWRITE:
        processed_projects = set()
        print("Force mode: Starting fresh (will overwrite existing file)")
    else:
        processed_projects = get_processed_projects(output_file)
    
    # Create quality settings with LLM and recording directory
    quality_settings = QualitySettings(
        use_vision=False,
        headless=False,
        steel_client=None,
        llm=llm,  # Use the configured LLM (either Llama or Gemini)
        record_video_dir=recordings_folder,
    )
    
    fieldnames = [
        'project_index', 'demo', 'repo', 'image', 'execution_time_seconds',
        'demo_valid', 'demo_error', 'demo_explanation',
        'repo_valid', 'repo_error', 'repo_explanation',
        'image_valid', 'image_error', 'image_explanation',
        'overall_valid', 'raw_result', 'judgement'
    ]
    
    # Determine if we need to create a new file or append to existing
    file_exists = os.path.exists(output_file) and not FORCE_OVERWRITE
    
    if not file_exists:
        # Create new CSV file and write header
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
        print(f"Created new output file: {output_file}")
    else:
        print(f"Resuming from existing output file: {output_file}")
    
    # Process projects sequentially to avoid overwhelming the system
    results = []
    processed_count = 0
    skipped_count = 0
    
    for i, project_data in enumerate(projects, 1):
        # Skip if already processed
        if i in processed_projects:
            print(f"Skipping project {i}/{len(projects)} (already processed): {project_data['demo']}")
            skipped_count += 1
            continue
        
        print(f"Processing project {i}/{len(projects)}: {project_data['demo']}")
        result = await process_project(project_data, i, quality_settings, MAX_RETRIES, RETRY_DELAY)
        results.append(result)
        processed_count += 1
        
        # Write result to CSV immediately after each project
        with open(output_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writerow(result)
        
        print(f"  Result written to {output_file}")
        print(f"  Recording saved to {recordings_folder}")
        
        # Small delay between projects to be respectful to the system
        await asyncio.sleep(DELAY_BETWEEN_PROJECTS)
    
    print(f"All results written to {output_file}")
    print(f"Recordings saved to {recordings_folder}")
    
    # Print summary
    total_projects = len(projects)
    successful_checks = sum(1 for r in results if r['overall_valid'])
    total_time = sum(r['execution_time_seconds'] for r in results)
    
    print(f"\nSummary:")
    print(f"Total projects in input: {total_projects}")
    print(f"Projects skipped (already processed): {skipped_count}")
    print(f"Projects processed in this run: {processed_count}")
    print(f"Successful quality checks: {successful_checks}")
    if processed_count > 0:
        print(f"Total execution time: {total_time:.2f} seconds")
        print(f"Average time per project: {total_time/processed_count:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main()) 