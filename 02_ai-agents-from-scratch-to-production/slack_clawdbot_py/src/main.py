import signal
import sys
import time
from .config import config
from .utils.logger import setup_logger, create_module_logger
from .memory.database import initialize_database, close_database
from .rag import initialize_vector_store, get_document_count, start_indexer, stop_indexer
from .memory_ai import initialize_memory, is_memory_enabled
from .mcp import initialize_mcp, shutdown_mcp, is_mcp_enabled, get_connected_servers
from .tools.scheduler import task_scheduler
from .channels.slack import start_slack_app, stop_slack_app

logger = create_module_logger("main")

def run():
    # Setup global root logger
    setup_logger(config.app.log_level)

    logger.info("=" * 60)
    logger.info("🚀 Starting Slack AI Assistant v2 (Python Edition)")
    logger.info("=" * 60)

    try:
        # 1. Initialize SQLite database
        logger.info("1. Initializing SQLite session database...")
        initialize_database()

        # 2. Initialize RAG vector store & indexer
        if config.rag.enabled:
            logger.info("2. Initializing RAG semantic search system...")
            initialize_vector_store()
            docs_count = get_document_count()
            logger.info(f"   ✅ Vector store active with {docs_count} documents")
            start_indexer()
        else:
            logger.info("2. ⏭️ RAG system disabled")

        # 3. Initialize Mem0 memory system
        if config.memory.enabled:
            logger.info("3. Initializing Mem0 long-term memory...")
            initialize_memory()
            if is_memory_enabled():
                logger.info("   ✅ Memory layer active")
            else:
                logger.info("   ⚠️ Continuing without memory layer")
        else:
            logger.info("3. ⏭️ Long-term memory disabled")

        # 4. Initialize MCP servers
        logger.info("4. Initializing Model Context Protocol (MCP) servers...")
        initialize_mcp()
        if is_mcp_enabled():
            servers = get_connected_servers()
            logger.info(f"   ✅ MCP active with servers: {', '.join(servers)}")
        else:
            logger.info("   ⏭️ No active MCP servers connected")

        # 5. Start task scheduler
        logger.info("5. Starting background task scheduler...")
        task_scheduler.start()

        # 6. Start Slack app
        logger.info("6. Starting Slack Bolt App (Socket Mode)...")
        start_slack_app()

        logger.info("=" * 60)
        logger.info("✨ Slack ClawdBot is ready and listening!")
        logger.info("=" * 60)
        logger.info(f"  • AI Model: {config.ai.default_model}")
        logger.info(f"  • RAG Enabled: {'✅' if config.rag.enabled else '❌'}")
        logger.info(f"  • Memory Enabled: {'✅' if is_memory_enabled() else '❌'}")
        logger.info(f"  • MCP Enabled: {'✅' if is_mcp_enabled() else '❌'}")
        logger.info("=" * 60)
        logger.info("Press Ctrl+C to stop.")

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        shutdown("SIGINT")
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)

def shutdown(signal_name: str = "SIGTERM"):
    logger.info(f"\nReceived {signal_name}, shutting down gracefully...")
    try:
        logger.info("Stopping Slack Bolt connection...")
        stop_slack_app()

        logger.info("Stopping background indexer...")
        if config.rag.enabled:
            stop_indexer()

        logger.info("Stopping task scheduler...")
        task_scheduler.stop()

        logger.info("Shutting down MCP servers...")
        shutdown_mcp()

        logger.info("Closing SQLite database...")
        close_database()

        logger.info("✅ Shutdown complete.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        sys.exit(1)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda s, f: shutdown("SIGTERM"))
    run()
