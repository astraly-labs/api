from fastapi import APIRouter

from pragma.routers.endpoints.assertions import app as assertions_router
from pragma.routers.endpoints.candlestick import app as candlestick_router
from pragma.routers.endpoints.onchain import app as onchain_router
from pragma.routers.endpoints.streaming import app as streaming_router

api_router = APIRouter(
    prefix="/v1",
)

api_router.include_router(assertions_router)
api_router.include_router(candlestick_router)
api_router.include_router(onchain_router)
api_router.include_router(streaming_router)
