from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from toolz.dicttoolz import get_in


def must_get(keys, coll):
    return get_in(keys, coll, no_default=True)


@dataclass
class SearchResponse:
    cmd: str
    code: int
    channel: int
    files: List['SearchResultFile'] = field(default_factory=list)

    @classmethod
    def from_response(cls, resp: dict):
        init_data = {
            "cmd":     resp['cmd'],
            "code":    resp['code'],
            "channel": must_get(['value', 'SearchResult', 'channel'], resp)
            }

        resp_files = []
        for file in must_get(['value', 'SearchResult', 'File'], resp):
            resp_files.append(SearchResultFile._from_file_resp(file))

        init_data['files'] = resp_files
        return SearchResponse(**init_data)


@dataclass
class SearchResultFile:
    EndTime: 'SearchResultTime'
    PlaybackTime: 'SearchResultTime'
    StartTime: 'SearchResultTime'
    frameRate: int
    height: int
    size: int
    type: str
    width: int

    def __repr__(self):
        st = self.StartTime.dt.strftime("%m/%d %I:%M:%S %p")
        pt = self.PlaybackTime.dt.strftime("%m/%d %I:%M:%S %p")
        et = self.EndTime.dt.strftime("%m/%d %I:%M:%S %p")

        return f"{st} :: {pt} :: {et}"

    @classmethod
    def _from_file_resp(cls, file: dict):
        init_data = {
            "EndTime":      SearchResultTime.from_dict(file['EndTime']),
            "PlaybackTime": SearchResultTime.from_dict(file['PlaybackTime']),
            "StartTime":    SearchResultTime.from_dict(file['StartTime']),
            }

        straight_data = {k: file[k] for k in ['frameRate', 'height', 'size', 'type', 'width']}
        merged_data = {**init_data, **straight_data}
        return SearchResultFile(**merged_data)


@dataclass
class SearchResultTime:
    _day: int
    _hour: int
    _min: int
    _sec: int
    _mon: int
    _year: int
    dt: datetime = field(init=False)

    def __repr__(self):
        return self.dt.__repr__()

    def __str__(self):
        return self.dt.__str__()

    @classmethod
    def from_dict(cls, time: dict):
        init_data = {k: time[k[1:]] for k in ["_day", "_hour", "_min", "_sec", "_mon", "_year"]}
        return SearchResultTime(**init_data)

    def __post_init__(self):
        self.dt = datetime(self._year, self._mon, self._day, self._hour, self._min, self._sec)


def dt_string(dt: datetime):
    return f"{dt.year}{dt.month}{dt.day}{dt.hour}{dt.minute}{dt.second}"
