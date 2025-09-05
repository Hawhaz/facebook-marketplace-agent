#!/usr/bin/env python3
"""System verification script to check all dependencies and configurations."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def check_python_version() -> bool:
    """Check if Python version is compatible."""
    logger.info("Checking Python version...")
    
    version = sys.version_info
    logger.info(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 8:
        logger.info("✓ Python version is compatible")
        return True
    else:
        logger.error("❌ Python 3.8+ required")
        return False


def check_required_packages() -> bool:
    """Check if all required packages are installed."""
    logger.info("Checking required packages...")
    
    required_packages = [
        'playwright',
        'sqlalchemy',
        'pydantic',
        'python-dotenv',
        'requests',
        'pillow',
        'aiofiles'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✓ {package} is installed")
        except ImportError:
            logger.error(f"❌ {package} is missing")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"Missing packages: {', '.join(missing_packages)}")
        logger.error("Run: pip install -r requirements.txt")
        return False
    
    return True


async def check_playwright_browsers() -> bool:
    """Check if Playwright browsers are installed."""
    logger.info("Checking Playwright browsers...")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            # Try to launch browsers
            browsers_to_check = ['chromium', 'firefox']
            working_browsers = []
            
            for browser_name in browsers_to_check:
                try:
                    browser = getattr(p, browser_name)
                    instance = await browser.launch(headless=True)
                    await instance.close()
                    logger.info(f"✓ {browser_name} is available")
                    working_browsers.append(browser_name)
                except Exception as e:
                    logger.warning(f"⚠ {browser_name} not available: {e}")
            
            if working_browsers:
                logger.info(f"Available browsers: {', '.join(working_browsers)}")
                return True
            else:
                logger.error("❌ No Playwright browsers available")
                logger.error("Run: playwright install")
                return False
                
    except Exception as e:
        logger.error(f"Playwright check failed: {e}")
        return False


def check_environment_file() -> bool:
    """Check if .env file exists and has required variables."""
    logger.info("Checking environment configuration...")
    
    env_file = Path('.env')
    
    if not env_file.exists():
        logger.warning("⚠ .env file not found")
        logger.info("Copy .env.example to .env and configure your settings")
        return False
    
    logger.info("✓ .env file exists")
    
    # Check for critical variables
    try:
        from app.config import settings
        
        critical_checks = [
            ("Database URL", settings.DATABASE_URL),
            ("Images directory", settings.IMAGES_DIR),
        ]
        
        for name, value in critical_checks:
            if value:
                logger.info(f"✓ {name} is configured")
            else:
                logger.warning(f"⚠ {name} is not configured")
        
        return True
        
    except Exception as e:
        logger.error(f"Environment configuration error: {e}")
        return False


def check_directories() -> bool:
    """Check if required directories exist or can be created."""
    logger.info("Checking directories...")
    
    try:
        from app.config import settings
        
        directories = [
            Path(settings.IMAGES_DIR),
            Path('logs'),
            Path('data')
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"✓ Directory ready: {directory}")
            except Exception as e:
                logger.error(f"❌ Cannot create directory {directory}: {e}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Directory check failed: {e}")
        return False


async def check_database_connection() -> bool:
    """Check database connection and table creation."""
    logger.info("Checking database connection...")
    
    try:
        from app.db.session import create_tables, get_db_context
        from app.models.database import Property
        
        # Create tables
        create_tables()
        logger.info("✓ Database tables created/verified")
        
        # Test connection
        with get_db_context() as db:
            count = db.query(Property).count()
            logger.info(f"✓ Database connection successful ({count} properties in database)")
        
        return True
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def main():
    """Run all system verification checks."""
    logger.info("Starting system verification...")
    
    checks = [
        ("Python Version", check_python_version, False),
        ("Required Packages", check_required_packages, False),
        ("Environment File", check_environment_file, False),
        ("Directories", check_directories, False),
        ("Database Connection", check_database_connection, True),
        ("Playwright Browsers", check_playwright_browsers, True),
    ]
    
    results = []
    
    for check_name, check_func, is_async in checks:
        logger.info(f"\n--- {check_name} ---")
        try:
            if is_async:
                result = await check_func()
            else:
                result = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"Check {check_name} crashed: {e}")
            results.append((check_name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("SYSTEM VERIFICATION RESULTS")
    logger.info("="*50)
    
    passed = 0
    for check_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        logger.info(f"{check_name:.<30} {status}")
        if result:
            passed += 1
    
    logger.info(f"\nPassed: {passed}/{len(results)} checks")
    
    if passed == len(results):
        logger.info("\n🎉 System verification completed successfully!")
        logger.info("Your system is ready to run the Facebook Marketplace agent.")
        return True
    else:
        logger.error("\n❌ System verification failed")
        logger.error("Please fix the issues above before running the agent.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
