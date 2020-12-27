from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, Boolean, DateTime, String, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
Session = sessionmaker()


def get_session(db_url) -> Session:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session.configure(bind=engine)
    session = Session()
    return session


class MotionDetection(Base):
    __tablename__ = 'motions'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('channels.id'))
    channel = relationship("Channel", back_populates="detections")
    detected = Column(Boolean)
    dt = Column(DateTime, default=datetime.now())


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(128))
    detections = relationship("MotionDetection", back_populates="channel", order_by="desc(MotionDetection.dt)")

    @hybrid_property
    def last_state(self) -> Optional[bool]:
        detect = self.detections
        if detect:
            return detect[0].detected
        return None
