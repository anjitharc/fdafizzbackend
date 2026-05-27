from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, admin, zone_manager, delivery, customer, websocket
# Ensure DeliverySettings and WhatsAppSettings tables are created on startup
from app.models import delivery_settings as _ds_model  # noqa: F401
from app.models import whatsapp_settings as _wa_model   # noqa: F401
from app.database import Base, engine
from sqlalchemy import inspect, text
Base.metadata.create_all(bind=engine)


def ensure_zone_status_column():
    """Add zones.is_enabled for existing databases where create_all cannot alter tables."""
    inspector = inspect(engine)
    if "zones" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("zones")}
    if "is_enabled" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE zones ADD COLUMN is_enabled BOOLEAN DEFAULT TRUE NOT NULL"))


ensure_zone_status_column()

app = FastAPI(
    title="Food Delivery App API",
    description="Backend API for Food Delivery Application",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["Master Admin"])
app.include_router(zone_manager.router, prefix="/api/zone-manager", tags=["Zone Manager"])
app.include_router(delivery.router, prefix="/api/delivery", tags=["Delivery Staff"])
app.include_router(customer.router, prefix="/api/customer", tags=["Customer"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])


@app.get("/", tags=["Root"])
def root():
    return {"message": "Food Delivery App API", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
