# [Podium](https://podium.hackclub.com/), a peer-judging platform for hackathons

## For Attendees

### Overview

Podium allows you, and your team members, to submit the project you’ve spent the past ~24 hours on. To get started, head over to [Podium](https://podium.hackclub.com) (podium.hackclub.com) and create an account. After you sign up, you’ll receive an email with a link, valid for fifteen minutes, allowing you to login.

### Joining

To join an event, enter the join code given to you by the event organizer(s). It’s a ~4-character case-insensitive code that looks like “**AMXU**” or “**-PWJ**” and can be entered on the homepage. Upon joining the event, you’re now able to create a project.

### Creating a project

You can create a project from the homepage, just fill out your project’s information and press “**Create Project”**. For everyone else on your team, they just have to enter the project’s join code, found in your project dashboard, into their project dashboard.

Please keep in mind that the hours field is just for statistics, so please be honest when filling it out. Also include your team members' hours!

### Updating projects

Made a mistake when creating your project? Decided to remake your project two hours before voting? No problem! Go to the project dashboard to update your event.

### Voting

To experience other attendees’ projects, and to vote on them, go to the events dashboard click on the “**Rank Projects**” button. From here, you’ll be able to visit project demos and view their repositories. To begin voting, select the top two or three projects (depending on the size of the event) that you like most. Then, submit your vote. Order doesn’t matter!

### Leaderboard

Want to see current project standings? Head over to the leaderboard for the event you’re attending by going to the event dashboard and then pressing the “**Leaderboard”** button.

## For Organizers

As an organizer, Podium streamlines the competitive aspect of your hackathon by allowing for attendees to seamlessly submit projects and vote on them. To get started, head over to [Podium](https://podium.hackclub.com/) and create an account. After you sign up, you’ll receive an email with a link, valid for fifteen minutes, allowing you to login.

To set up your event, go to the events dashboard from the homepage, and create an event. You should see a join code, a ~4-character case-insensitive code that looks like “AMXU” or “-PWJ”, in the list below. Distribute this code to attendees to allow them to join!

## Development

There's a SvelteKit frontend and a FastAPI backend.

#### Frontend

```zsh
cd frontend
bun install
bun dev
```

#### Backend

```zsh
cd backend
uv sync
uv run podium
```

For secrets, you need the following as environment variables or in the `backend/` folder in `.secrets.toml` or `.env` files:

- `airtable_token`
- `jwt_secret`
- `sendgrid_api_key`

Airtable is heavily relied upon but it's rather difficult to easily import/export schemas. If you're in Hack Club, just message @Angad Behl or ask in #podium for dev creds. Otherwise, you might be able go through the `db` module in the backend to get the mandatory fields. `settings.toml` has the table IDs and configuration that isn't sensitive. To set secrets, you can use `.secrets.toml`. You can also use environment variables or `.env` files, just remember to prefix them with `PODIUM_`.  
If running the project evaluation locally, ensure you run `poetry run playwright install`.

<!-- * Users
    * `email` - primary, email
    * `first_name` - single line text
    * `last_name` - single line text
    * `phone` - phone number
    * `owned_event` - link to another record in the Events table
    * `attending_events` - link to another record in the Events table, multiple can be linked
    * `projects` - link to another record in the Projects table, multiple can be linked
    * `votes` - link to another record in the Events table, multiple can be linked
    * `street`, `street_2`, `city`, `state`, `zip`, and `country` - single line text
    * `dob` - date
    * `referrals` - link to another record in the referrals table, multiple can be linked
* Events
    * `name` - single line text
    * `description` - long text
    * `owner` - link to another record in the Users table
    `attendees` - link to another record in the Users table, multiple can be linked
    * `join_code` - single line text
    * `projects` - link to another record in the Projects table, multiple can be linked
    * `voters` - link to another record in the Users table, multiple can be linked
    * `referrals` - link to another record in the referrals table, multiple can be linked
* Projects
    * `name` - single line text
    * `owner` - link to another record in the Users table
    * `readme`- URL
    * `repo` - URL
    * `demo` - URL
    * `points` - number
    * `description` - long text
    * `image_url` - URL
    * `event` - link to another record in the Events table
    * `join_code` - single line text
    * `collaborators` - link to another record in the Users table, multiple can be linked
    * `hours_spent` - number
* referrals
    * `content` - single line text
    * `user` - link to another record in the Users table
    * `event` - link to another record in the Events table -->

# Quality evaluation

Podium includes automated quality evaluation. It utilizes a multimodal browser agent to ensure the project demo and repository are valid. However, it can also be used as a standalone CLI tool or as a library. It's found in `backend/quality` and can be installed directly with `pip install git+https://github.com/hackclub/podium.git@main#egg=podium&subdirectory=backend`. This command will install the entire Podium backend, but also the `quality` module, which is what you need.  
The image is simply checked by ensuring it's a URL pointing to a raw image file.

To use it as a CLI, you can run the following command:

```bash
quality --demo "https://podium.hackclub.com" --repo "https://github.com/hackclub/podium" --image "https://assets.hackclub.com/icon-rounded.png" --gemini-api-key <GEMINI_API_KEY>
```

(you can optionally pass `--headless` to run the browser in headless mode, this may, however, be detected by some sites and cause issues)

## Using as a library

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from podium.db.project import Project
from quality.models import QualitySettings
from quality.quality import check_project
import rich

GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

quality_settings = QualitySettings(
        # You should be able to use most Langchain LLMs here
        llm=ChatGoogleGenerativeAI(
            api_key=GEMINI_API_KEY,
            model="gemini-2.0-flash-lite",
        ),
        use_vision=True,  # Setting to true will use the multimodal capabilities the LLM. Disable if the model does not support multimodal input.
        headless=False, # Set to True to run the browser in headless mode
        session_semaphore=asyncio.Semaphore(2), # This limits the max number of browser sessions. Steel's free tier, at the time of writing, allows 2 concurrent sessions.


        # prompts=YourClass(), # You can customize the prompts used for evaluation by creating a class that inherits from `backend.quality.models.Prompts` and overriding the fields
        # steel_client=Steel(steel_api_key=settings.steel_api_key),             # Optionally, you can use steel.dev to spin up a browser running in the cloud for each evaluation. Ensure you import it with `from steel import Steel`.
    )

project = Project(
    id="recPLACEHOLDER",
    name="placeholder",
    demo="https://podium.hackclub.com", # replace with the demo URL to evaluate
    repo="https://github.com/hackclub/podium", # replace with the repository URL to evaluate
    description="placeholder",
    image_url="https://assets.hackclub.com/flag-standalone.svg", # replace with the image URL to evaluate
    event=["recPLACEHOLDER"],
    owner=["recPLACEHOLDER"],
)

# Run the evaluation and pretty print the results as JSON
results = await check_project(project, config=quality_settings)

# Print the results
rich.print_json(
    json=results.model_dump_json(),
)
```
