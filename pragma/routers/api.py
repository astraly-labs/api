from fastapi import APIRouter

from pragma.routers.endpoints.assertions import app as assertions_router
from pragma.routers.endpoints.offchain import app as offchain_router
from pragma.routers.endpoints.onchain import app as onchain_router
from pragma.routers.endpoints.streaming import app as streaming_router
from pragma.routers.endpoints.tokens import app as tokens_router
from pragma.routers.endpoints.websocket import app as websocket_router

api_router = APIRouter(
    prefix="/v1",
)

api_router.include_router(assertions_router)
api_router.include_router(offchain_router)
api_router.include_router(onchain_router)
api_router.include_router(streaming_router)
api_router.include_router(tokens_router)
api_router.include_router(websocket_router)
