from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config.settings import settings

# Import all routers
from backend.routes.heartbeat import router as heartbeat_router
from backend.routes.consent import router as consent_router
from backend.routes.session import router as session_router
from backend.routes.sync import router as sync_router

# Initialize the main FastAPI application instance
app = FastAPI(title="Markaz Backend API")

# Configure CORS Middleware
# This MUST be added before any routes are registered to ensure OPTIONS requests are handled globally
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all protected routers
# Since the Depends(verify_api_key) dependency is attached at the @router decorator 
# level inside each of these individual files, they remain fully protected.
app.include_router(heartbeat_router)
app.include_router(consent_router)
app.include_router(session_router)
app.include_router(sync_router)

# Root/Health endpoint
# This is attached directly to the main 'app' instance, bypassing the protected routers
@app.get("/health")
async def health_check():
    return {"status": "ok"}
