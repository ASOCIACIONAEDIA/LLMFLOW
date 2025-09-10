import os
import asyncio
import secrets
import time
import requests

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
import app.models  # noqa: ensure models are registered
from app.models import User, Organization
from app.core.security import hash_password


BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


async def ensure_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def upsert_verified_user(email: str, password: str, name: str):
    await ensure_tables()
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        # Create org if needed
        org = (await session.execute(select(Organization).limit(1))).scalar_one_or_none()
        if not org:
            org = Organization(name="Jobs Test Org")
            session.add(org)
            await session.flush()

        # Get or create user
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            user = User(
                name=name,
                email=email,
                hashed_password=hash_password(password),
                is_active=True,
                is_verified=True,
                organization_id=org.id,
            )
            session.add(user)
        else:
            user.is_active = True
            user.is_verified = True
            user.hashed_password = hash_password(password)

        await session.commit()


def login(session: requests.Session, email: str, password: str) -> str:
    resp = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password, "remember_me": False},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed: {resp.status_code} {resp.text}")
    return resp.json()["access_token"]


def create_job(session: requests.Session, access_token: str) -> str:
    headers = {"Authorization": f"Bearer {access_token}"}
    body = {
        "sources": [
            {
                "source_type": "trustpilot",
                "brand_name": "Acme",
                "countries": ["us"],
                "number_of_reviews": 10,
                "options": {},
            }
        ]
    }
    r = session.post(
        f"{BASE_URL}/jobs",
        params={"job_type": "review_scraping"},
        json=body,
        headers=headers,
    )
    if r.status_code != 201:
        raise RuntimeError(f"Create job failed: {r.status_code} {r.text}")
    return r.json()["job_id"]


def get_job(session: requests.Session, access_token: str, job_id: str):
    headers = {"Authorization": f"Bearer {access_token}"}
    r = session.get(f"{BASE_URL}/jobs/{job_id}", headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"Get job failed: {r.status_code} {r.text}")
    return r.json()


def list_jobs(session: requests.Session, access_token: str, limit=50, offset=0):
    headers = {"Authorization": f"Bearer {access_token}"}
    r = session.get(f"{BASE_URL}/jobs", params={"limit": limit, "offset": offset}, headers=headers)
    if r.status_code != 200:
        raise RuntimeError(f"List jobs failed: {r.status_code} {r.text}")
    return r.json()


def main():
    email = f"jobs-test+{secrets.token_hex(4)}@example.com"
    password = "SecurePass123!"
    name = "Jobs API Tester"

    # Ensure user exists and is verified/active via DB (async)
    asyncio.run(upsert_verified_user(email, password, name))

    s = requests.Session()
    print(f"Login as {email}")
    access = login(s, email, password)

    print("Create job...")
    job_id = create_job(s, access)
    print(f"Job created: {job_id}")

    print("Fetch job...")
    job = get_job(s, access, job_id)
    print(job)

    print("List jobs...")
    jobs = list_jobs(s, access)
    print(f"Total returned: {len(jobs)}")
    print(jobs[:1])

    time.sleep(2)
    print("Refetch job...")
    print(get_job(s, access, job_id))


if __name__ == "__main__":
    main()