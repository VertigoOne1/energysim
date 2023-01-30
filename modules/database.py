import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from envyaml import EnvYAML
from modules.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

if "CONFIG_FILE" in os.environ:
    logger.info("Loading Production Config")
    config = EnvYAML(os.environ.get('CONFIG_FILE'))
else:
    logger.info("Loading Development Config")
    config = EnvYAML('config.yml')

engine = create_engine(config['sqlalchemy']['db_url'], pool_recycle=3600, pool_pre_ping=True)
db_session = sessionmaker(future=True,
                            autocommit=False,
                            autoflush=False,
                            bind=engine)
Base = declarative_base()
# Base.query = db_session.query_property()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import models
    logger.debug("Init_DB")
    Base.metadata.create_all(bind=engine, checkfirst=True)