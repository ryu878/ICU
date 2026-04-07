from fastapi import APIRouter

from icu.api.v1 import auth, conversations, users

router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(conversations.router)
