"""
Generate Airtable automation scripts for each table.

Creates 5 separate files (one per table) in cache/generated/ directory
with TABLE_NAME pre-configured for easy copy-pasting into Airtable.

Usage:
    python -m podium.cache.generate_automation_scripts
"""

from pathlib import Path

TABLES = ["Users", "Events", "Projects", "Votes", "Referrals"]


def generate_scripts():
    """Generate automation scripts for each table."""
    # Read template
    template_file = Path(__file__).parent / "airtable_automation_template.js"
    if not template_file.exists():
        print(f"Error: Template file not found: {template_file}")
        return
    
    template = template_file.read_text()
    
    # Create output directory
    output_dir = Path(__file__).parent / "generated"
    output_dir.mkdir(exist_ok=True)
    
    print("Generating Airtable automation scripts...")
    print(f"Template: {template_file.name}")
    print(f"Output: {output_dir}")
    print()
    
    for table in TABLES:
        # Generate script with table name substituted
        script = template.replace("{{TABLE_NAME}}", table)
        
        # Write to file
        output_file = output_dir / f"{table.lower()}_automation.js"
        output_file.write_text(script)
        
        print(f"✓ Generated: {output_file.name}")
    
    print()
    print("=" * 60)
    print("Copy-paste instructions:")
    print("=" * 60)
    for table in TABLES:
        filename = f"{table.lower()}_automation.js"
        print(f"{table:12} → cache/generated/{filename}")
    print()
    print("Each file has TABLE_NAME pre-configured for that table.")
    print("Just copy the entire file content into Airtable's script editor!")


def main():
    """Entry point."""
    generate_scripts()


if __name__ == "__main__":
    main()
