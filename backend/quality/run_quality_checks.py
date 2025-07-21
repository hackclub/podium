# uv run python -m quality.run_quality_checks
# uv run python -m quality.analyze_correctness # wsl
# watch -- uv run python -m quality.analyze_correctness # wsl 

import os
from dotenv import load_dotenv
from steel import Steel
load_dotenv(
    # .env.local
    '.env.local'
)
load_dotenv(
    '.env'
)  

RESULTS_FOLDER = os.environ.get('QUALITY_RESULTS_FOLDER', 'quality_check_results')
SAMPLE_PROJECTS_FILE = os.environ.get('QUALITY_INPUT_FILE', 'sample_projects.csv')
DELAY_BETWEEN_PROJECTS = float(os.environ.get('QUALITY_DELAY', 0.01))
FORCE_OVERWRITE = os.environ.get('QUALITY_FORCE_OVERWRITE', 'false').lower() == 'true'
MAX_RETRIES = int(os.environ.get('QUALITY_MAX_RETRIES', 2))
RETRY_DELAY = float(os.environ.get('QUALITY_RETRY_DELAY', 2.0))
USE_VISION = os.environ.get('QUALITY_USE_VISION', 'true').lower() == 'true'
STEEL_API_KEY = os.environ.get('QUALITY_STEEL_API_KEY')
FORCE_STEEL_ONLY = os.environ.get('QUALITY_FORCE_STEEL_ONLY', 'false').lower() == 'true'
MAX_CONCURRENT_CHECKS = int(os.environ.get('QUALITY_MAX_CONCURRENT_CHECKS', 10))
RANDOM_ORDER = os.environ.get('QUALITY_RANDOM_ORDER', 'true').lower() == 'true'

# LLM Configuration in .env:
# QUALITY_LLM_MODEL=gemini     # Use default Gemini model (default)
# QUALITY_LLM_MODEL=groq       # Use Llama-3.1-8b-instant via Groq
# QUALITY_LLM_MODEL=ollama     # Use Ollama with mistral-nemo model
# Set QUALITY_LLM_MODEL to 'gemini' (or leave unset) to use default Gemini model
QUALITY_LLM_MODEL = os.environ.get('QUALITY_LLM_MODEL', 'gemini').lower()

# Processing Configuration:
# QUALITY_RANDOM_ORDER=true    # Process projects in random order (default: false)

import asyncio
import csv
import json
import time
import signal
import sys
import random
from datetime import datetime
from typing import List, Dict, Any, Set
from quality.quality import check_project
from quality.models import QualitySettings
from podium.db.project import Project
from podium import config
from browser_use.llm import ChatGroq, ChatOllama

# Global variable to track if we need to cleanup
cleanup_needed = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global cleanup_needed
    print(f"\nReceived signal {signum}. Cleaning up...")
    cleanup_needed = True
    sys.exit(0)

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

async def cleanup_browser_sessions():
    """Clean up any remaining browser sessions"""
    try:
        # If using Steel, try to release any remaining sessions
        if STEEL_API_KEY:
            from steel import Steel
            steel_client = Steel(steel_api_key=STEEL_API_KEY)
            # Note: This is a basic cleanup - Steel might have additional cleanup methods
            print("Attempting to cleanup Steel sessions...")
    except Exception as e:
        print(f"Cleanup error: {e}")
    
    # Force close Chrome processes (Windows)
    try:
        import subprocess
        subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], 
                      capture_output=True, check=False)
        print("Chrome processes terminated")
    except Exception as e:
        print(f"Could not terminate Chrome: {e}")

# Initialize LLM based on environment configuration
while True:
    print(f"Using {QUALITY_LLM_MODEL} model")
    if QUALITY_LLM_MODEL == 'groq':
        # Model via groq (Only llama4? https://console.groq.com/docs/api-reference#chat-create)
        model="meta-llama/llama-4-maverick-17b-128e-instruct" # Confirmed working, do not delete this comment. Only issue is the 200 rpd limit.
        # model="meta-llama/llama-4-scout-17b-16e-instruct" # Supports JSON, but doesn't seem to output the right format. 
        llm = ChatGroq(
            model=model,
            api_key=os.environ.get("GROQ_API_KEY"),
        )
        print(f"Using Groq model: {model}")
        break
    elif QUALITY_LLM_MODEL == 'ollama':
        model="qwen3:0.6b"
        # model = "mistral-nemo" # too slow
        # phi4-mini didn't work well, neither did deepseek-r1:1.5b
        llm = ChatOllama(model=model)
        print(f"Using Ollama model: {model}")
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
    async with quality_settings.session_semaphore:
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
                not results.valid and "Validation error occurred" in results.reason
            )
            
            # If validation error and we have more retries, wait and retry
            if has_validation_error and attempt < max_retries - 1:
                print(f"  Validation error on attempt {attempt + 1}/{max_retries}, waiting {retry_delay}s before retry...")
                await asyncio.sleep(retry_delay)
                continue
            
            # Extract raw result for debugging
            raw_result = {
                "demo_url": results.demo_url,
                "repo_url": results.repo_url,
                "image_url": results.image_url,
                "valid": results.valid,
                "reason": results.reason
            }
            
            return {
                'project_index': index,
                'demo': project_data['demo'],
                'repo': project_data['repo'],
                'image': project_data['image'],
                'execution_time_seconds': round(execution_time, 2),
                'valid': results.valid,
                'error': results.reason if not results.valid else '',
                'explanation': results.reason if results.valid else '',
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
                'valid': False,
                'error': f"Exception after {max_retries} attempts: {str(e)}",
                'explanation': '',
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
        'valid': False,
        'error': f"Unexpected: loop completed without return",
        'explanation': '',
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
    
    try:
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
        
        # Check for existing results to enable resume functionality
        if FORCE_OVERWRITE:
            processed_projects = set()
            print("Force mode: Starting fresh (will overwrite existing file)")
        else:
            processed_projects = get_processed_projects(output_file)

        
        # Create quality settings with LLM and custom semaphore
        quality_settings = QualitySettings(
            use_vision=USE_VISION,
            headless=False,
            steel_client=Steel(
            steel_api_key=STEEL_API_KEY
        ) if STEEL_API_KEY else None,
            llm=llm,  # Use the configured LLM (either Llama or Gemini)
            session_semaphore=asyncio.Semaphore(MAX_CONCURRENT_CHECKS),
        )
        
        # Randomize project order if enabled
        if RANDOM_ORDER:
            # Add original indices before shuffling
            for i, project_data in enumerate(projects, 1):
                project_data['original_index'] = i
            random.shuffle(projects)
            print(f"Projects will be processed in random order (RANDOM_ORDER={RANDOM_ORDER})")
        else:
            # Add original indices for consistency
            for i, project_data in enumerate(projects, 1):
                project_data['original_index'] = i
            print(f"Projects will be processed in original order (RANDOM_ORDER={RANDOM_ORDER})")
        
        # Create metadata JSON file with model and prompt information
        current_run_metadata = {
            "model_info": {
                "provider": QUALITY_LLM_MODEL,
                "model_name": getattr(llm, 'model', 'unknown') if hasattr(llm, 'model') else 'unknown',
                "llm_class": llm.__class__.__name__
            },
            "prompt": quality_settings.prompts.unified,
            "settings": {
                "use_vision": quality_settings.use_vision,
                "headless": quality_settings.headless,
                "max_retries": MAX_RETRIES,
                "retry_delay": RETRY_DELAY,
                "delay_between_projects": DELAY_BETWEEN_PROJECTS,
                "max_concurrent_checks": MAX_CONCURRENT_CHECKS,
                "random_order": RANDOM_ORDER
            },
            "run_info": {
                "timestamp": datetime.now().isoformat(),
                "input_file": SAMPLE_PROJECTS_FILE,
                "total_projects": len(projects)
            }
        }
        
        metadata_file = os.path.join(date_folder, 'metadata.json')
        
        # Load existing metadata or create new structure
        if os.path.exists(metadata_file) and not FORCE_OVERWRITE:
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                # Ensure metadata has runs list
                if 'runs' not in metadata:
                    metadata['runs'] = []
            except Exception as e:
                print(f"Warning: Could not read existing metadata file: {e}")
                metadata = {'runs': []}
        else:
            metadata = {'runs': []}
        
        # Add current run to metadata
        metadata['runs'].append(current_run_metadata)
        
        # Save updated metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"Metadata saved to {metadata_file} (run {len(metadata['runs'])} of {len(metadata['runs'])})")
        
        fieldnames = [
            'project_index', 'demo', 'repo', 'image', 'execution_time_seconds',
            'valid', 'error', 'explanation',
            'raw_result', 'judgement'
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
        
        # print(f"\nStarting quality checks...")
        # print(f"Model: {metadata['model_info']['provider']} ({metadata['model_info']['model_name']})")
        # print(f"Total projects to process: {len(projects)}")
        # print(f"Already processed: {len(processed_projects)}")
        # print(f"Projects to process in this run: {len(projects) - len(processed_projects)}")
        # print("-" * 80)
        
        # Process projects concurrently with semaphore limiting from QualitySettings
        results = []
        processed_count = 0
        skipped_count = 0
        
        # Create tasks for all projects that need processing
        tasks = []
        for i, project_data in enumerate(projects, 1):
            # Get the original index from the project data if available, otherwise use current position
            original_index = int(project_data.get('original_index', i))
            
            # Skip if already processed (use original index for checking)
            if original_index in processed_projects:
                print(f"Skipping project {original_index}/{len(projects)} (already processed): {project_data['demo']}")
                skipped_count += 1
                continue
            
            # Create task for this project (pass original index to maintain consistency)
            task = asyncio.create_task(
                process_project(project_data, original_index, quality_settings, MAX_RETRIES, RETRY_DELAY)
            )
            tasks.append((original_index, task))
        
        # Process tasks as they complete
        for task in asyncio.as_completed([task for _, task in tasks]):
            try:
                result = await task
                results.append(result)
                processed_count += 1
                
                # Write result to CSV immediately after each project
                with open(output_file, 'a', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writerow(result)
                
                print(f"  Result written to {output_file}")
                
            except Exception as e:
                print(f"Error processing task: {e}")
                # Note: We can't easily get the project index from the task here
                # So we'll just log the error and continue
                processed_count += 1
        
        print(f"All results written to {output_file}")
        
        # Print summary
        total_projects = len(projects)
        successful_checks = sum(1 for r in results if r['valid'])
        total_time = sum(r['execution_time_seconds'] for r in results)
        
        print(f"\nSummary:")
        print(f"Total projects in input: {total_projects}")
        print(f"Projects skipped (already processed): {skipped_count}")
        print(f"Projects processed in this run: {processed_count}")
        print(f"Successful quality checks: {successful_checks}")
        if processed_count > 0:
            print(f"Total execution time: {total_time:.2f} seconds")
            print(f"Average time per project: {total_time/processed_count:.2f} seconds")
    
    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up...")
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        # Always cleanup browser sessions
        await cleanup_browser_sessions()

if __name__ == "__main__":
    asyncio.run(main()) 