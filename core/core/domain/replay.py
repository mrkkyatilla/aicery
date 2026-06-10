from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, model_validator


class ReplayMode(StrEnum):
    LIVE = "live"
    REPLAY = "replay"


class ReplayContext(BaseModel):
    mode: ReplayMode = ReplayMode.LIVE
    source_run_id: str | None = None
    mock_provider: bool = False
    mock_tools: bool = False
    frozen_step_hashes: list[str] | None = None

    @model_validator(mode="after")
    def _validate_replay(self) -> ReplayContext:
        if self.mode == ReplayMode.REPLAY:
            if not self.source_run_id:
                raise ValueError("source_run_id required when mode is replay")
            self.mock_provider = True
        return self

    @property
    def is_replay(self) -> bool:
        return self.mode == ReplayMode.REPLAY
