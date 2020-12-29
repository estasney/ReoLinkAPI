from datetime import datetime, timedelta
from psycopg2.extras import DateTimeRange
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import TSRANGE
from sqlalchemy.sql.expression import func, extract

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
    channel = relationship("Channel", back_populates="motions")
    range = Column(TSRANGE())

    @hybrid_property
    def seconds(self):
        return (self.range.upper - self.range.lower).total_seconds()

    @seconds.expression
    def seconds(cls):
        intv = func.upper(cls.range) - func.lower(cls.range)
        return extract('epoch', intv)

    @classmethod
    def _td(cls, td: timedelta):
        mm, ss = divmod(td.total_seconds(), 60)
        hh, mm = divmod(mm, 60)
        s = "%d:%02d:%02d" % (hh, mm, ss)
        return s

    def __repr__(self):
        if isinstance(self.range.lower, datetime):
            s1 = self.range.lower.strftime("%m/%d %I:%M:%S %p")
        else:
            s1 = " ? "
        if isinstance(self.range.upper, datetime):
            s2 = self.range.upper.strftime("%m/%d %I:%M:%S %p")
        else:
            s2 = " ? "
        if isinstance(self.range.lower, datetime) and isinstance(self.range.upper, datetime):
            td = MotionRange._td((self.range.upper - self.range.lower))
        else:
            td = "?"
        return f"<Channel {self.channel_id}> : [{td}]  ({s1} - {s2})"


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

