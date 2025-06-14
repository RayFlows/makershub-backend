#init.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
from mongoengine import connect, disconnect
from app.core.db import connect_to_mongodb, disconnect_from_mongodb
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.auth import AuthMiddleware
from app.routes import (
    arrange_router,
    clean_router,
    duty_apply_router,
    duty_record_router,
    event_router,
    publicity_link_router,
    site_borrow_router,
    stuff_router,
    task_router,
    user_router
)