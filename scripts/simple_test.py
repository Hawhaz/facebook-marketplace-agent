#!/usr/bin/env python3
"""Simple test script to verify basic functionality."""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_imports():
    """Test that all modules can be imported."""
    logger.info("Testing imports...")
    
    try:
        from app.config import settings
        logger.info("✓ Config imported successfully")
        
        from app.models.database import Property, MarketplaceListing
        logger.info("✓ Database models imported successfully")
        
        from app.db.session import create_tables, get_db_context
        logger.info("✓ Database session imported successfully")
        
        from app.utils.money import fmt_money, m2, plural
        logger.info("✓ Utility functions imported successfully")
        
        from app.core.automation.facebook.housing import fill_marketplace_housing_form
        logger.info("✓ Facebook automation imported successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return False


async def test_database():
    """Test database connection and table creation."""
    logger.info("Testing database...")
    
    try:
        from app.db.session import create_tables, get_db_context
        from app.models.database import Property
        
        # Create tables
        create_tables()
        logger.info("✓ Database tables created")
        
        # Test database session
        with get_db_context() as db:
            # Try to query (should work even if empty)
            count = db.query(Property).count()
            logger.info(f"✓ Database query successful (found {count} properties)")
        
        return True
        
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return False


async def test_config():
    """Test configuration loading."""
    logger.info("Testing configuration...")
    
    try:
        from app.config import settings
        
        logger.info(f"✓ Database URL: {settings.DATABASE_URL}")
        logger.info(f"✓ Debug mode: {settings.DEBUG}")
        logger.info(f"✓ Images directory: {settings.IMAGES_DIR}")
        
        # Check if images directory exists or can be created
        images_path = Path(settings.IMAGES_DIR)
        images_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Images directory ready: {images_path.absolute()}")
        
        return True
        
    except Exception as e:
        logger.error(f"Configuration test failed: {e}")
        return False


async def test_utilities():
    """Test utility functions."""
    logger.info("Testing utilities...")
    
    try:
        from app.utils.money import fmt_money, m2, plural
        
        # Test money formatting
        assert fmt_money(1500000) == "$1,500,000 MXN"
        logger.info("✓ Money formatting works")
        
        # Test area formatting
        assert m2(120) == "120 m²"
        logger.info("✓ Area formatting works")
        
        # Test pluralization
        assert plural(1, "casa", "casas") == "casa"
        assert plural(2, "casa", "casas") == "casas"
        logger.info("✓ Pluralization works")
        
        return True
        
    except Exception as e:
        logger.error(f"Utilities test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("Starting simple tests...")
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Database", test_database),
        ("Utilities", test_utilities),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n--- Test Results ---")
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error("❌ Some tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
