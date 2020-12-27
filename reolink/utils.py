from dataclasses import dataclass, field
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
            "cmd": resp['cmd'],
            "code": resp['code'],
            "channel": must_get(['value', 'SearchResult', 'channel'], resp)}

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

    @classmethod
    def _from_file_resp(cls, file: dict):
        init_data = {
            "EndTime": SearchResultTime.from_dict(file['EndTime']),
            "PlaybackTime": SearchResultTime.from_dict(file['PlaybackTime']),
            "StartTime": SearchResultTime.from_dict(file['StartTime']),
            }

        straight_data = {k: file[k] for k in ['frameRate', 'height', 'size', 'type', 'width']}
        merged_data = {**init_data, **straight_data}
        return SearchResultFile(**merged_data)



@dataclass
class SearchResultTime:
    day: int
    hour: int
    min: int
    sec: int
    year: int

    @classmethod
    def from_dict(cls, time: dict):
        init_data = {k: time[k] for k in ["day", "hour", "min", "sec", "year"]}
        return SearchResultTime(**init_data)





