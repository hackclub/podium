from datetime import datetime, timedelta, timezone

# import smtplib
# from email.mime.text import MIMEText
from typing import Annotated

from podium import db, settings

from fastapi import APIRouter, HTTPException, Query, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from podium.db.user import CurrentUser
from pydantic import BaseModel, StringConstraints
import jwt
from jwt.exceptions import PyJWTError

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

router = APIRouter(tags=["auth"])

SECRET_KEY = settings.jwt_secret
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes
MAGIC_LINK_EXPIRE_MINUTES = 15


DEBUG_EMAIL = "angad+debug@hackclub.com"


class User(BaseModel):
    # Might be better to use EmailStr here, but this is more convenient
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True)]


def create_access_token(
    data: dict, expires_delta: timedelta | None = None, token_type: str = "access"
):
    to_encode = data.copy()

    # Set the token type. Otherwise, a magic link could be used as an access token. Probably not the end of the world, but would mess with stuff like 2FA
    # Potentially, a version could be set that once incremented would invalidate all old tokens
    to_encode.update({"token_type": token_type})
    # Set the expirationt ime
    # Not sure if this needs to be UTC, but why not?
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=MAGIC_LINK_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def send_magic_link(email: str, redirect: str = ""):
    token_data = {"sub": email}
    token = create_access_token(
        data=token_data, expires_delta=timedelta(minutes=15), token_type="magic_link"
    )

    magic_link = f"{settings.production_url}/login?token={token}"
    if redirect:
        magic_link += f"&redirect={redirect}"

    message = Mail(
        from_email=settings.sendgrid_from_email,
        to_emails=email,
        subject="Magic link for Podium",
        # html_content=f"Click <a href='{magic_link}'>here</a> to log in to Podium",
        html_content=magic_link_email_content(magic_link=magic_link)["html"],
        plain_text_content=magic_link_email_content(magic_link=magic_link)["text"],
    )

    try:
        sg = SendGridAPIClient(settings.sendgrid_api_key)
        _ = sg.send(message)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send auth email")

    print(
        f"Token for {email}: {token} | magic_link: {settings.production_url}/login?token={token} | local magic_link: http://localhost:5173/login?token={token}"
    )


@router.post("/request-login")
# https://fastapi.tiangolo.com/tutorial/query-param-models/
async def request_login(user: User, redirect: Annotated[str, Query()]):
    """Send a magic link to the user's email. If the user has not yet signed up, an error will be raised"""
    # Check if the user exists
    if db.user.get_user_record_id_by_email(user.email) is None:
        raise HTTPException(status_code=404, detail="User not found")
        return  # not needed
    await send_magic_link(user.email, redirect=redirect)


class MagicLinkVerificationResponse(BaseModel):
    access_token: str
    token_type: str
    email: str


@router.get("/verify")
async def verify_token(token: Annotated[str, Query()]) -> MagicLinkVerificationResponse:
    """Verify a magic link and return an access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("token_type")
        # Check if the token is a magic link, otherwise it's invalid
        # Otherwise a JWT that's about to expire might be used as an access token
        if email is None or token_type != "magic_link":
            raise HTTPException(status_code=400, detail="Invalid token")
    except PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
    # Check if the user exists
    if db.user.get_user_record_id_by_email(email) is None:
        raise HTTPException(status_code=404, detail="User not found")
    access_token = create_access_token(
        data={"sub": email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )
    return MagicLinkVerificationResponse(
        access_token=access_token, token_type="access", email=email
    )


# This serves two purposes: it checks if the token is valid and returns the user's email
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> CurrentUser:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("token_type")
        if email is None or token_type != "access":
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    return CurrentUser(email=email)


class CheckAuthResponse(BaseModel):
    email: str


@router.get("/protected-route")
async def protected_route(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CheckAuthResponse:
    # Check if the user exists
    if db.user.get_user_record_id_by_email(current_user.email) is None:
        raise HTTPException(status_code=404, detail="User not found")
    return CheckAuthResponse(email=current_user.email)


if __name__ == "__main__":
    # create a dev access JWT and  a magic link JWT
    debug_access = create_access_token(
        data={"sub": DEBUG_EMAIL},
        expires_delta=timedelta(days=365),  # Token valid for 1 year
        token_type="access",
    )
    debug_verify = create_access_token(
        data={"sub": DEBUG_EMAIL},
        expires_delta=timedelta(days=365),  # Token valid for 1 year
        token_type="magic_link",
    )
    # print the access token on one line and on the next line the magic link
    # print(
    #     f"Access token for {DEBUG_EMAIL}: {debug_access}\nMagic link: http://localhost:5173/login?token={debug_verify}"
    # )


def magic_link_email_content(magic_link: str) -> dict:
    html = f"""
 <html>
      <head>
      <style>
        .wrapper {{
          padding: 1rem;
          margin: 0 auto;
          max-width: 600px;
          font-family: 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Fira Sans', 'Oxygen', 'Ubuntu', 'Helvetica Neue', sans-serif;
        }}
    
        .container {{
          padding: 0;
          margin: 0;
          width: 100%;
          max-width: 100%;
        }}
    
        a {{
          color: #8492a6;
        }}
    
        .section {{
          padding: 0.5rem 1rem;
        }}
    
        .footer {{
          font-size: 0.8rem;
          line-height: 1.2rem;
          color: #606a79;
    
          background-position: center;
          background-size: cover;
          background-repeat: repeat-x;
        }}
    
        .footer p {{
          margin-block-start: 0.5rem;
          margin-block-end: 0.5rem;
        }}
    
        .footer a {{
          color: #646464;
        }}
      </style>
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
      </head>
      <body>
      <div class="wrapper">
        <div class="container">
          <table>
            <thead>
            <tr>
              <th>
                <div class="section" style="text-align: left;">
                  <a
                    href="https://hackclub.com"
                    target="_blank"
                  >
                    <img
                      src="https://assets.hackclub.com/icon-rounded.png"
                      alt="Hack Club Logo"
                      style="width: 2.5rem"
                    />
                  </a>
                </div>
              </th>
            </tr>
            </thead>
            <tbody>
            <tr>
              <td>
                <div
                  class="section"
                >
                <p>👋 Hey! </p>
                <p>You requested a magic link for Podium. It's here:</p>
                <p><a href="{magic_link}">{magic_link}</a></p>
                <p>- Hack Club</p>
                </div>
              </td>
            </tr>
            <tr>
              <td>
                <div
                  class="footer section"
                  style="background-image: url('https://hackclub.com/pattern.svg');"
                >
                  <p>
                    Hack Club |
                    <a href="mailto:team@hackclub.com">team@hackclub.com</a>
                    |
                    <a href="tel:+1855625HACK">1-855-625-HACK</a>
                  </p>
                  <p>
                    Hack Club is an
                    <a href="https://hackclub.com/opensource" target="_blank">open source</a>
                    and
                    <a href="https://hcb.hackclub.com/hq" target="_blank"
                      >financially transparent</a
                    >
                    501(c)(3) nonprofit. Our EIN is 81-2908499. By the students, for the
                    students.
                  </p>
                </div>
            </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      </body>
</html>
"""
    text = """
👋 Hey, \n\n
      
You requested a login link for Podium. It's here!
      
- Hack Club`
"""

    return {"html": html, "text": text}
