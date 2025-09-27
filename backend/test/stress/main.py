"""Main stress test runner."""

import asyncio
import sys
import os
from typing import Dict, Any

# Handle both relative and absolute imports
try:
    from .client import StressTestClient
    from .config import (
        NUM_EVENTS,
        USERS_PER_EVENT,
        CLEANUP_AFTER_TESTS,
        generate_unique_id,
        generate_test_email,
        generate_test_name
    )
    from .auth_utils import simulate_auth_flow_via_api
    from .reporting import (
        generate_response_time_report,
        create_response_time_graph,
        create_endpoint_comparison_graph,
        print_summary_report,
        save_report_to_file
    )
except ImportError:
    # Fallback to absolute imports when running as script
    from client import StressTestClient
    from config import (
        NUM_EVENTS,
        USERS_PER_EVENT,
        CLEANUP_AFTER_TESTS,
        generate_unique_id,
        generate_test_email,
        generate_test_name
    )
    from auth_utils import simulate_auth_flow_via_api
    from reporting import (
        generate_response_time_report,
        create_response_time_graph,
        create_endpoint_comparison_graph,
        print_summary_report,
        save_report_to_file
    )


async def run_comprehensive_stress_test(
    num_events: int = NUM_EVENTS,
    users_per_event: int = USERS_PER_EVENT,
    cleanup: bool = CLEANUP_AFTER_TESTS
) -> Dict[str, Any]:
    """Run a comprehensive stress test covering all major endpoints."""
    
    print("Starting comprehensive stress test...")
    print(f"Events: {num_events}, Users per event: {users_per_event}")
    print(f"Cleanup after tests: {cleanup}")
    print("-" * 50)
    
    all_response_times = []
    test_results = {
        "api_tests": []
    }
    
    # Create test users and authenticate them
    print("\n1. Creating test users and authenticating...")
    test_users = []
    for i in range(num_events * users_per_event):
        unique_id = generate_unique_id()
        test_email = generate_test_email(unique_id)
        test_name = generate_test_name(unique_id)
        
        async with StressTestClient() as client:
            # 1. Sign up user
            signup_payload = {
                "email": test_email,
                "display_name": test_name,
                "first_name": "Test",
                "last_name": f"User{i}",
                "phone": "1234567890",
                "city": "Test City",
                "state": "TS",
                "country": "Test Country"
            }
            
            signup_response = await client.post("/users/", json=signup_payload)
            if signup_response.status_code == 200:
                all_response_times.extend(client.get_response_times())
                
                # 2. Complete auth flow via API
                auth_data = await simulate_auth_flow_via_api(client, test_email)
                all_response_times.extend(client.get_response_times())
                if auth_data:
                    test_users.append({
                        "email": test_email,
                        "name": test_name,
                        "unique_id": unique_id,
                        "access_token": auth_data["access_token"],
                        "magic_token": auth_data["magic_token"],
                        "user_data": auth_data["user_data"],
                        "authenticated": True
                    })
                else:
                    print(f"   Warning: Failed to authenticate user {test_email}")
                    test_users.append({
                        "email": test_email,
                        "name": test_name,
                        "unique_id": unique_id,
                        "authenticated": False
                    })
    
    authenticated_users = [u for u in test_users if u.get("authenticated", False)]
    print(f"   Created {len(test_users)} test users")
    print(f"   Authenticated {len(authenticated_users)} users with real tokens")
    
    # Create events and get real event IDs
    print("\n2. Creating events...")
    events_data = []
    
    for event_idx in range(num_events):
        # Event owner (first user in this event's group)
        owner_idx = event_idx * users_per_event
        if owner_idx >= len(authenticated_users):
            break
            
        owner = authenticated_users[owner_idx]
        async with StressTestClient() as client:
            # Use real authentication
            client.set_auth_token(owner["access_token"])
            
            # Create event with unique name
            unique_suffix = generate_unique_id()
            event_payload = {
                "name": f"Stress Test Event {event_idx + 1} {unique_suffix}",
                "description": f"Event for stress testing {event_idx + 1} - {unique_suffix}",
                "votable": True,
                "leaderboard_enabled": True,
                "demo_links_optional": True
            }
            
            event_response = await client.post("/events/", json=event_payload)
            all_response_times.extend(client.get_response_times())
            
            if event_response.status_code == 200:
                print(f"   Successfully created event {event_idx + 1}")
                
                # Get the real event ID by fetching user's events
                user_events_response = await client.get("/events/")
                all_response_times.extend(client.get_response_times())
                
                if user_events_response.status_code == 200:
                    user_events_data = user_events_response.json()
                    owned_events = user_events_data.get("owned_events", [])
                    
                    if owned_events:
                        # Get the most recently created event (last in list)
                        latest_event = owned_events[-1]
                        event_id = latest_event["id"]
                        join_code = latest_event.get("join_code", "")
                        
                        events_data.append({
                            "event_id": event_id,
                            "join_code": join_code,
                            "owner": owner,
                            "users": authenticated_users[owner_idx:owner_idx + users_per_event]
                        })
                        print(f"   Retrieved real event ID: {event_id}")
                    else:
                        print("   Warning: No owned events found for user")
            else:
                try:
                    error_detail = event_response.json()
                    print(f"   Warning: Event creation failed with status {event_response.status_code}: {error_detail}")
                except Exception:
                    print(f"   Warning: Event creation failed with status {event_response.status_code}: {event_response.text}")
    
    print(f"   Created {len(events_data)} events with real IDs")
    
    # Make ALL users attend their respective events (including owners!)
    print("\n3. Making users attend events...")
    for event_data in events_data:
        event_id = event_data["event_id"]
        join_code = event_data["join_code"]
        event_users = event_data["users"]
        
        # All users need to attend, including the owner
        for user in event_users:
            async with StressTestClient() as client:
                client.set_auth_token(user["access_token"])
                
                attend_response = await client.post(f"/events/attend?join_code={join_code}&referral=stress_test")
                all_response_times.extend(client.get_response_times())
                
                if attend_response.status_code == 200:
                    print(f"   User {user['name']} attended event {event_id}")
                elif attend_response.status_code == 400:
                    # User already attending (expected for some cases)
                    print(f"   User {user['name']} already attending event {event_id}")
                else:
                    print(f"   Warning: User {user['name']} failed to attend event: {attend_response.status_code}")
    
    # Create projects in each event
    print("\n4. Creating projects in events...")
    all_projects = []
    created_projects = []  # For cleanup
    
    for event_data in events_data:
        event_id = event_data["event_id"]
        event_users = event_data["users"]
        
        # Each user creates a project
        for user_idx, user in enumerate(event_users):
            async with StressTestClient() as client:
                client.set_auth_token(user["access_token"])
                
                project_payload = {
                    "name": f"Project {user_idx + 1} by {user['name']}",
                    "repo": f"https://github.com/stress-test/{user['unique_id']}",
                    "image_url": f"https://example.com/images/{user['unique_id']}.png",
                    "demo": f"https://demo.example.com/{user['unique_id']}",
                    "description": f"Project created by {user['name']}",
                    "event": [event_id],
                    "hours_spent": 10
                }
                
                project_response = await client.post("/projects/", json=project_payload)
                all_response_times.extend(client.get_response_times())
                
                if project_response.status_code == 200:
                    print(f"   User {user['name']} created project successfully")
                    
                    # Project creation also doesn't return data, get real project ID from user's projects
                    user_projects_response = await client.get("/projects/mine")
                    all_response_times.extend(client.get_response_times())
                    
                    if user_projects_response.status_code == 200:
                        user_projects_data = user_projects_response.json()
                        if user_projects_data:
                            # Get the most recently created project (last in list)
                            latest_project = user_projects_data[-1]
                            project_id = latest_project["id"]
                            created_projects.append(project_id)
                            all_projects.append({
                                "project_id": project_id,
                                "event_id": event_id,
                                "owner": user,
                                "join_code": latest_project.get("join_code", "")
                            })
                            print(f"   Retrieved real project ID: {project_id}")
                else:
                    try:
                        error_detail = project_response.json()
                        print(f"   Warning: Project creation failed for {user['name']}: {project_response.status_code}: {error_detail}")
                    except Exception:
                        print(f"   Warning: Project creation failed for {user['name']}: {project_response.status_code}: {project_response.text}")
    
    print(f"   Created {len(all_projects)} projects")
    
    # Run comprehensive API tests
    print("\n5. Running comprehensive API tests...")
    api_results = []
    users_who_voted = set()  # Track who has voted to avoid duplicates
    
    for event_data in events_data:
        event_id = event_data["event_id"]
        event_users = event_data["users"]
        event_projects = [p for p in all_projects if p["event_id"] == event_id]
        
        # Simple concurrent user workflow - focus on load testing
        async def user_workflow(user):
            """Simple user workflow to test concurrent load."""
            results = []
            async with StressTestClient() as client:
                client.set_auth_token(user["access_token"])
                
                # Core user actions
                current_user_response = await client.get("/users/current")
                results.append(("GET /users/current", current_user_response.status_code))
                
                user_events_response = await client.get("/events/")
                results.append(("GET /events/", user_events_response.status_code))
                
                user_projects_response = await client.get("/projects/mine")
                results.append(("GET /projects/mine", user_projects_response.status_code))
                
                event_response = await client.get(f"/events/{event_id}")
                results.append(("GET /events/{event_id}", event_response.status_code))
                
                # Try to vote on other users' projects
                votable_projects = [p for p in event_projects if p["owner"]["unique_id"] != user["unique_id"]]
                if len(votable_projects) >= 1:
                    project_ids = [p["project_id"] for p in votable_projects[:2]]
                    vote_payload = {"projects": project_ids, "event": event_id}
                    vote_response = await client.post("/events/vote", json=vote_payload)
                    results.append(("POST /events/vote", vote_response.status_code))
                    
                    if vote_response.status_code == 200:
                        print(f"   ✓ User {user['name']} voted successfully")
                
                # Get leaderboard (only for event owner via admin endpoint)
                if user == event_users[0]:  # Only event owner can access admin endpoints
                    leaderboard_response = await client.get(f"/events/admin/{event_id}/leaderboard")
                    results.append(("GET /events/admin/{event_id}/leaderboard", leaderboard_response.status_code))
                
                # Get event projects for ranking page
                event_projects_response = await client.get(f"/events/{event_id}/projects?leaderboard=false")
                results.append(("GET /events/{event_id}/projects", event_projects_response.status_code))
                
                # Update own project
                user_projects = [p for p in event_projects if p["owner"]["unique_id"] == user["unique_id"]]
                if user_projects:
                    project_id = user_projects[0]["project_id"]
                    update_payload = {
                        "name": f"Updated {user['name']} Project",
                        "repo": f"https://github.com/updated/{user['unique_id']}",
                        "image_url": f"https://example.com/updated/{user['unique_id']}.png",
                        "demo": f"https://demo.example.com/updated/{user['unique_id']}",
                        "description": f"Updated by {user['name']}",
                        "event": [event_id],
                        "hours_spent": 25
                    }
                    update_response = await client.put(f"/projects/{project_id}", json=update_payload)
                    results.append(("PUT /projects/{project_id}", update_response.status_code))
                
                all_response_times.extend(client.get_response_times())
                return results
        
        # Run concurrent user workflows
        workflow_tasks = [user_workflow(user) for user in event_users]
        workflow_results = await asyncio.gather(*workflow_tasks, return_exceptions=True)
        
        # Process results
        for result in workflow_results:
            if isinstance(result, list):
                for endpoint, status_code in result:
                    api_results.append({
                        "endpoint": endpoint,
                        "status_code": status_code,
                        "success": 200 <= status_code < 300
                    })
        
        # 12. Admin endpoints (event owner only)
        if event_users:
            owner = event_users[0]  # First user is the event owner
            async with StressTestClient() as client:
                client.set_auth_token(owner["access_token"])
                
                # Get admin event details
                admin_event_response = await client.get(f"/events/admin/{event_id}")
                api_results.append({
                    "endpoint": f"GET /events/admin/{event_id}",
                    "status_code": admin_event_response.status_code,
                    "success": 200 <= admin_event_response.status_code < 300
                })
                all_response_times.extend(client.get_response_times())
                
                # Get admin attendees
                admin_attendees_response = await client.get(f"/events/admin/{event_id}/attendees")
                api_results.append({
                    "endpoint": f"GET /events/admin/{event_id}/attendees",
                    "status_code": admin_attendees_response.status_code,
                    "success": 200 <= admin_attendees_response.status_code < 300
                })
                all_response_times.extend(client.get_response_times())
                
                # Get admin leaderboard
                admin_leaderboard_response = await client.get(f"/events/admin/{event_id}/leaderboard")
                api_results.append({
                    "endpoint": f"GET /events/admin/{event_id}/leaderboard",
                    "status_code": admin_leaderboard_response.status_code,
                    "success": 200 <= admin_leaderboard_response.status_code < 300
                })
                all_response_times.extend(client.get_response_times())
                
                # Get admin votes
                admin_votes_response = await client.get(f"/events/admin/{event_id}/votes")
                api_results.append({
                    "endpoint": f"GET /events/admin/{event_id}/votes",
                    "status_code": admin_votes_response.status_code,
                    "success": 200 <= admin_votes_response.status_code < 300
                })
                all_response_times.extend(client.get_response_times())
                
                # Get admin referrals
                admin_referrals_response = await client.get(f"/events/admin/{event_id}/referrals")
                api_results.append({
                    "endpoint": f"GET /events/admin/{event_id}/referrals",
                    "status_code": admin_referrals_response.status_code,
                    "success": 200 <= admin_referrals_response.status_code < 300
                })
                all_response_times.extend(client.get_response_times())
                
                # Remove a user (admin feature) - remove last user if there are multiple
                if len(event_users) > 1:
                    user_to_remove = event_users[-1]  # Remove last user
                    user_id_to_remove = user_to_remove["user_data"]["id"]
                    remove_response = await client.post(f"/events/admin/{event_id}/remove-attendee", json=user_id_to_remove)
                    api_results.append({
                        "endpoint": f"POST /events/admin/{event_id}/remove-attendee",
                        "status_code": remove_response.status_code,
                        "success": 200 <= remove_response.status_code < 300
                    })
                    all_response_times.extend(client.get_response_times())
                    
                    if remove_response.status_code == 200:
                        print(f"   ✓ Admin removed user {user_to_remove['name']}")
                    else:
                        print(f"   Warning: Failed to remove user {user_to_remove['name']}: {remove_response.status_code}")
    
    test_results["api_tests"] = api_results
    print(f"   Completed {len(api_results)} API operations")
    
    # Cleanup (if enabled)
    if cleanup and (created_projects or events_data):
        print("\n6. Cleaning up test data...")
        cleanup_results = []
        
        # Delete projects (each user deletes their own projects)
        for project in all_projects:
            project_owner = project["owner"]
            async with StressTestClient() as client:
                client.set_auth_token(project_owner["access_token"])
                delete_response = await client.delete(f"/projects/{project['project_id']}")
                cleanup_results.append({
                    "endpoint": f"DELETE /projects/{project['project_id']}",
                    "status_code": delete_response.status_code,
                    "success": 200 <= delete_response.status_code < 300
                })
                all_response_times.extend(client.get_response_times())
        
        # Delete events (use event owners)
        for event_data in events_data:
            event_id = event_data["event_id"]
            owner = event_data["owner"]
            async with StressTestClient() as client:
                client.set_auth_token(owner["access_token"])
                delete_response = await client.delete(f"/events/{event_id}")
                cleanup_results.append({
                    "endpoint": f"DELETE /events/{event_id}",
                    "status_code": delete_response.status_code,
                    "success": 200 <= delete_response.status_code < 300
                })
                all_response_times.extend(client.get_response_times())
        
        test_results["cleanup_tests"] = cleanup_results
        print(f"   Cleaned up {len(created_projects)} projects and {len(events_data)} events")
    
    # Generate reports
    print(f"\n{6 if not cleanup else 7}. Generating reports...")
    report = generate_response_time_report(all_response_times)
    
    # Add test results to report
    report["test_results"] = test_results
    
    # Print summary
    print_summary_report(report)
    
    # Generate graphs
    try:
        total_users = num_events * users_per_event
        title_suffix = f" ({num_events} events, {total_users} users)"
        
        graph1 = create_response_time_graph(all_response_times, "response_times.png", title_suffix)
        print(f"\n{graph1}")
        
        graph2 = create_endpoint_comparison_graph(all_response_times, "endpoint_comparison.png", title_suffix)
        print(f"{graph2}")
    except Exception as e:
        print(f"\nGraph generation info: {e}")
    
    # Save report
    report_file = save_report_to_file(report, "stress_test_report.json")
    print(f"\n{report_file}")
    
    return report


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        num_events = int(sys.argv[1])
    else:
        num_events = NUM_EVENTS
    
    if len(sys.argv) > 2:
        users_per_event = int(sys.argv[2])
    else:
        users_per_event = USERS_PER_EVENT
    
    print("Podium API Stress Test")
    print("=" * 30)
    print(f"API: {os.getenv('STRESS_TEST_API_URL', 'http://localhost:8000')}")
    print(f"Events: {num_events}, Users per event: {users_per_event}")
    print()
    
    try:
        await run_comprehensive_stress_test(
            num_events=num_events,
            users_per_event=users_per_event,
            cleanup=CLEANUP_AFTER_TESTS
        )
        
        print("\n" + "="*50)
        print("STRESS TEST COMPLETED")
        print("="*50)
        
        return 0
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
        return 1
    except Exception as e:
        print(f"\nTest failed: {e}")
        return 1


if __name__ == "__main__":
    # Set default API URL if not provided
    if not os.getenv("STRESS_TEST_API_URL"):
        os.environ["STRESS_TEST_API_URL"] = "http://localhost:8000"
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
