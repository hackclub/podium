# uv run pytest -s
import logging
import os
import sys
import time
import subprocess
from pathlib import Path

import pytest
from pyngrok import ngrok
import httpx
import shutil
from test import APP_PORT, settings
import atexit
import asyncio
from browser_use import BrowserSession
import pytest_asyncio
import steel
from loguru import logger
import uuid
from datetime import timedelta

from podium import db
from podium.routers import auth as auth_router
from test.utils import create_temp_user_tokens


# Reduce verbosity of pyngrok loggers to hide INFO-level noise during tests
for _name in ("pyngrok", "pyngrok.ngrok", "pyngrok.process", "pyngrok.process.ngrok"):
    logging.getLogger(_name).setLevel(logging.WARNING)

def _wait_for_http(url: str, timeout_seconds: int = 60) -> None:
    start = time.time()
    last_error: Exception | None = None
    while time.time() - start < timeout_seconds:
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(url)
                if resp.status_code < 500:
                    return
        except Exception as e:  # noqa: BLE001
            last_error = e
        time.sleep(0.5)
    raise RuntimeError(f"Service at {url} did not become ready in {timeout_seconds}s. Last error: {last_error}")


@pytest.fixture(scope="session")
def app_public_url():
    backend_proc: subprocess.Popen | None = None
    frontend_proc: subprocess.Popen | None = None
    backend_tunnel_url: str | None = None
    frontend_tunnel_url: str | None = None

    try:
        # 1) Start backend on port 8000
        backend_cwd = Path(__file__).resolve().parents[1]
        env_backend = os.environ.copy()
        logger.info("Starting backend server on port 8000...")
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "podium"],
            cwd=str(backend_cwd),
            env=env_backend,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _wait_for_http("http://127.0.0.1:8000/docs", timeout_seconds=90)
        logger.info("Backend is ready on http://127.0.0.1:8000")

        # 2) Expose backend via ngrok and set PUBLIC_API_URL
        ngrok.set_auth_token(settings.ngrok_auth_token)
        backend_tunnel = ngrok.connect(8000)
        backend_tunnel_url = backend_tunnel.public_url
        logger.info(f"Backend public API URL: {backend_tunnel_url}")

        # 3) Start frontend dev server with PUBLIC_API_URL set
        frontend_cwd = backend_cwd.parent / "frontend"
        env_frontend = os.environ.copy()
        env_frontend["PUBLIC_API_URL"] = backend_tunnel_url
        port = int(APP_PORT)
        logger.info(f"Starting frontend on port {port} with PUBLIC_API_URL={backend_tunnel_url}...")
        # Choose runner: prefer bun, then npm, then npx vite
        if shutil.which("bun"):
            cmd = ["bun", "run", "dev", "--", "--port", str(port), "--host", "127.0.0.1", "--strictPort"]
        elif shutil.which("npm"):
            cmd = ["npm", "run", "dev", "--", "--port", str(port), "--host", "127.0.0.1", "--strictPort"]
        else:
            cmd = ["npx", "--yes", "vite", "dev", "--port", str(port), "--host", "127.0.0.1", "--strictPort"]

        frontend_proc = subprocess.Popen(
            cmd,
            cwd=str(frontend_cwd),
            env=env_frontend,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for readiness, but bail early if process exits
        start_time = time.time()
        timeout = 180
        while time.time() - start_time < timeout:
            if frontend_proc.poll() is not None:
                out, err = frontend_proc.communicate(timeout=1) if frontend_proc.stdout else ("", "")
                raise RuntimeError(f"Frontend process exited with code {frontend_proc.returncode}.\nSTDOUT:\n{out[-2000:]}\nSTDERR:\n{err[-2000:]}")
            try:
                _wait_for_http(f"http://127.0.0.1:{port}/", timeout_seconds=2)
                break
            except Exception:
                time.sleep(0.5)
        else:
            # Timed out waiting for readiness; include recent logs
            try:
                out = frontend_proc.stdout.read() if frontend_proc.stdout else ""
                err = frontend_proc.stderr.read() if frontend_proc.stderr else ""
            except Exception:
                out = err = ""
            raise RuntimeError(
                f"Frontend did not become ready on port {port} within {timeout}s.\nSTDOUT tail:\n{out[-2000:]}\nSTDERR tail:\n{err[-2000:]}"
            )
        logger.info(f"Frontend is ready on http://127.0.0.1:{port}")

        # 4) Expose frontend via ngrok and yield for tests
        frontend_tunnel = ngrok.connect(port)
        frontend_tunnel_url = frontend_tunnel.public_url
        logger.info(f"Public URL for the app (frontend): {frontend_tunnel_url}")
        yield frontend_tunnel_url

    finally:
        # Teardown: close ngrok tunnels and processes
        if frontend_tunnel_url:
            try:
                ngrok.disconnect(frontend_tunnel_url)
            except Exception:  # noqa: BLE001
                pass
        if backend_tunnel_url:
            try:
                ngrok.disconnect(backend_tunnel_url)
            except Exception:  # noqa: BLE001
                pass
        try:
            ngrok.kill()
        except Exception:  # noqa: BLE001
            pass

        for proc, name in ((frontend_proc, "frontend"), (backend_proc, "backend")):
            if proc is None:
                continue
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"{name} did not terminate gracefully; killing...")
                    proc.kill()
            except Exception:  # noqa: BLE001
                pass


@pytest_asyncio.fixture
async def browser_session():
    """Yield a connected BrowserSession and ensure proper teardown/release."""
    steel_client = settings.steel_client
    if steel_client is None:
        raise RuntimeError("Steel client is not configured. Ensure STEEL_API_KEY is set.")

    browser_sess = steel_client.sessions.create()
    logger.info(f"Created live session at: {browser_sess.session_viewer_url}")
    browser_cdp_url = (
        f"wss://connect.steel.dev?apiKey={steel_client.steel_api_key}&sessionId={browser_sess.id}"
    )

    browser = BrowserSession(cdp_url=browser_cdp_url)
    # Attach viewer URL for downstream logging
    try:
        setattr(browser, "viewer_url", browser_sess.session_viewer_url)
    except Exception:
        pass

    # Failsafe to release session on interpreter exit in case of hard interrupts
    def _release_session_on_exit(session_id: str):
        try:
            steel_client.sessions.release(session_id)
        except Exception:
            pass

    atexit.register(_release_session_on_exit, browser_sess.id)

    try:
        yield browser
    finally:
        # Close browser (shield to avoid cancellation on Ctrl+C)
        try:
            await asyncio.shield(browser.close())
        except Exception:  # noqa: BLE001
            pass
        # Release Steel session
        try:
            steel_client.sessions.release(browser_sess.id)
        except steel.BadRequestError:
            logger.warning(f"Could not release session {browser_sess.id}")
        except Exception:  # noqa: BLE001
            pass


@pytest.fixture()
def temp_user_tokens(app_public_url):
    """
    Create a temporary user directly in the DB, generate a short-lived access token
    and a magic-link token for browser login. Yields a dict with keys:
    - email, user_id, access_token, magic_link_token, magic_link_url

    Ensures the user is deleted afterwards.
    """
    created_user_id: str | None = None
    email: str | None = None
    
    try:
        # Create user and generate tokens using the utility function
        tokens = create_temp_user_tokens(app_public_url)
        created_user_id = tokens["user_id"]
        email = tokens["email"]
        
        yield tokens
    finally:
        if created_user_id:
            try:
                db.users.delete(created_user_id)
                logger.info(f"Deleted temporary user {email} ({created_user_id})")
            except Exception:
                logger.warning(f"Failed to delete temporary user for {email}")