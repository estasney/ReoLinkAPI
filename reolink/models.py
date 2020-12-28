from datetime import datetime
from psycopg2.extras import DateTimeRange
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import TSRANGE

Base = declarative_base()
Session = sessionmaker()


def get_session(db_url) -> Session:
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session.configure(bind=engine)
    session = Session()
    return session


class MotionRange(Base):
    __tablename__ = 'motionranges'

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('channels.id'))
    channel = relationship("Channel", back_populates="intervals")
    range = Column(TSRANGE())


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(128))
    motion_started = Column(DateTime, nullable=True, default=None)
    motions = relationship("MotionRange", back_populates="channel")

    def handle_detection(self, detection: bool, session: Session, force_new: bool = False):
        """
        Passed a boolean, handles tracking state with MotionInterval.

        Parameters
        ----------
        detection : bool
            Boolean if motion is detected
        session : Session
            session connection
        force_new : bool
            If True, `self.motion_started` is set to `None`

        Returns
        -------
        changed : bool
            If True, session should be committed to track changes

        """
        changed = False

        if force_new:
            if self.motion_started:
                changed = True
            self.motion_started = None

        if self.motion_started is None and detection:
            self.motion_started = datetime.now()
            changed = True
            return changed
        elif self.motion_started is None and not detection:
            return changed
        elif self.motion_started is not None and detection:
            return changed
        elif self.motion_started is not None and not detection:

            md_interval = MotionRange(channel_id=self.id,
                                      range=DateTimeRange(self.motion_started, datetime.now()))
            session.add(md_interval)
            self.motion_started = None
            changed = True
            return changed
        else:
            raise Exception("Logic Error")

