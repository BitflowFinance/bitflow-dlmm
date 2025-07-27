"""
Main FastAPI application for the DLMM Quote Engine.
Entry point for the quote engine service following Grok's modular design.
"""

import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(
    title="DLMM Quote Engine",
    description="Quote engine for Distributed Liquidity Market Maker following Grok's modular design",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logging.info("🚀 DLMM Quote Engine starting up...")
    logging.info("📋 Following Grok's modular design:")
    logging.info("   - build_token_graph() - NetworkX-based routing")
    logging.info("   - enumerate_paths() - Simple path discovery")
    logging.info("   - pre_fetch_shared_data() - Batch Redis operations")
    logging.info("   - compute_quote() - Decimal-precise simulation")
    logging.info("   - find_best_route() - Multi-hop optimization")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logging.info("🛑 DLMM Quote Engine shutting down...")


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 