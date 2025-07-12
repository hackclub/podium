# poetry run -- python -m quality.run_quality_checks

# Constants
RESULTS_FOLDER = 'quality_check_results'
SAMPLE_PROJECTS_FILE = 'sample_projects.csv'
DELAY_BETWEEN_PROJECTS = 1  # seconds

import asyncio
import csv
import time
import os
from datetime import datetime
from typing import List, Dict, Any
from quality.quality import check_project
from quality.models import QualitySettings
from podium.db.project import Project
from podium import config
from dotenv import load_dotenv
from browser_use.llm import ChatOpenAI
load_dotenv()

# llm = ChatOpenAI(
#     model="llama-3.1-8b-instant",
#     api_key=os.environ.get("GROQ_API_KEY"),
#     base_url="https://api.groq.com/openai/v1"
# )
llm=config.quality_settings.llm


async def process_project(project_data: Dict[str, str], index: int, quality_settings: QualitySettings) -> Dict[str, Any]:
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
    
    try:
        # Run quality check
        results = await check_project(project, quality_settings)
        execution_time = time.time() - start_time
        
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
        print(f"Error processing project {index}: {e}")
        
        return {
            'project_index': index,
            'demo': project_data['demo'],
            'repo': project_data['repo'],
            'image': project_data['image'],
            'execution_time_seconds': round(execution_time, 2),
            'demo_valid': False,
            'demo_error': f"Exception: {str(e)}",
            'demo_explanation': '',
            'repo_valid': False,
            'repo_error': f"Exception: {str(e)}",
            'repo_explanation': '',
            'image_valid': False,
            'image_error': f"Exception: {str(e)}",
            'image_explanation': '',
            'overall_valid': False,
            'raw_result': f"Exception: {str(e)}",
            'judgement': project_data['judgement']
        }

async def main():
    """Main function to process all projects in sample_projects.csv."""
    
    # Read sample projects
    projects = []
    with open(SAMPLE_PROJECTS_FILE, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            projects.append(row)
    
    print(f"Processing {len(projects)} projects...")
    
    # Create date-based folder structure
    current_date = datetime.now().strftime('%Y-%m-%d')
    date_folder = os.path.join(RESULTS_FOLDER, current_date)
    os.makedirs(date_folder, exist_ok=True)
    
    # Create recordings folder within the date folder
    recordings_folder = os.path.join(date_folder, 'recordings')
    os.makedirs(recordings_folder, exist_ok=True)
    
    output_file = os.path.join(date_folder, 'results.csv')
    
    # Create quality settings with LLM and recording directory
    quality_settings = QualitySettings(
        use_vision=True,
        headless=False,
        steel_client=None,
        llm=config.quality_settings.llm,
        record_video_dir=recordings_folder,
    )
    
    fieldnames = [
        'project_index', 'demo', 'repo', 'image', 'execution_time_seconds',
        'demo_valid', 'demo_error', 'demo_explanation',
        'repo_valid', 'repo_error', 'repo_explanation',
        'image_valid', 'image_error', 'image_explanation',
        'overall_valid', 'raw_result', 'judgement'
    ]
    
    # Create/clear the CSV file and write header
    with open(output_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
    
    # Process projects sequentially to avoid overwhelming the system
    results = []
    for i, project_data in enumerate(projects, 1):
        print(f"Processing project {i}/{len(projects)}: {project_data['demo']}")
        result = await process_project(project_data, i, quality_settings)
        results.append(result)
        
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
    total_projects = len(results)
    successful_checks = sum(1 for r in results if r['overall_valid'])
    total_time = sum(r['execution_time_seconds'] for r in results)
    
    print(f"\nSummary:")
    print(f"Total projects processed: {total_projects}")
    print(f"Successful quality checks: {successful_checks}")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Average time per project: {total_time/total_projects:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main()) 