"""Scoped gate view; the frozen segment engine applies split gain once."""
from __future__ import annotations

import math
from copy import copy
import numpy as np

from .common import band


class GateAdapter:
    def __init__(self, parent, law, m, context, events):
        self.parent, self.law, self.m = parent, law, m
        self.context, self.events = dict(context), events

    def predict_proba(self, x):
        parent = self.parent.predict_proba(x)
        result = parent.copy()
        for i, row in enumerate(x):
            r, capacity = float(row[0]), float(row[3])
            theta = self.law.theta[band(r)]
            before = float(parent[i, 1])
            after = before if theta == 0.0 else self.m.sigmoid(self.m.logit(before) + theta)
            if theta != 0.0:
                result[i] = (1.0 - after, after)
            self.events.append(dict(self.context, rstart=r, capacity=capacity, band=band(r),
                                    parent_probability=before, offset=theta, adapted_probability=after,
                                    engine_probability=(self.m.sigmoid(self.m.logit(after) + math.log(self.m.FINAL_SEG_CLOSE_GAIN))
                                                        if self.context['split_end'] else after)))
        return result


def models_view(models, law, m, context, events):
    view = copy(models)
    view.gate = GateAdapter(models.gate, law, m, context, events)
    return view
