from podium.db.db import tables
from podium.db.event import PrivateEvent as PrivateEvent
from podium.db.event import EventCreationPayload as EventCreationPayload
from podium.db.event import UserEvents as UserEvents
from podium.db.event import EventUpdate as EventUpdate
from podium.db.event import Event as Event
from podium.db import user as user
from podium.db.project import ProjectUpdate as ProjectUpdate
from podium.db.project import ProjectBase as ProjectBase
from podium.db.referral import ReferralBase as ReferralBase

events = tables["events"]
users = tables["users"]
projects = tables["projects"]
referrals = tables["referrals"]
