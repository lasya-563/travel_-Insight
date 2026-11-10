"""Per-process model cache that refreshes itself when the DB version counters change.

Gunicorn runs several worker processes; each keeps its own models. An admin action bumps
`rec_version` / `seg_version` in the DB and every worker rebuilds on its next request.
"""
import threading

from ..db import get_meta
from ..services import repo
from .recommender import Recommender
from .segmentation import Segmenter


class ModelStore:
    def __init__(self, segment_k=0):
        self.segment_k = segment_k
        self._lock = threading.Lock()
        self._rec = self._seg = None
        self._rec_v = self._seg_v = None

    def ensure_fresh(self, db):
        rec_v, seg_v = get_meta(db, "rec_version"), get_meta(db, "seg_version")
        if self._rec is None or rec_v != self._rec_v or self._seg is None or seg_v != self._seg_v:
            with self._lock:
                if self._rec is None or rec_v != self._rec_v:
                    df = repo.destinations_df(db)
                    self._rec = Recommender(df) if len(df) else None
                    self._rec_v = rec_v
                if self._seg is None or seg_v != self._seg_v:
                    self._seg = Segmenter(self.segment_k).fit(repo.visitors_df(db))
                    self._seg_v = seg_v

    def recommender(self, db):
        self.ensure_fresh(db)
        return self._rec

    def segmenter(self, db):
        self.ensure_fresh(db)
        return self._seg
