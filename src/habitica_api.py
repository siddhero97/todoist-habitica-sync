import json
import logging
from typing import Any, Final

import requests
from pydantic import BaseModel, ConfigDict, Field

from delay import DelayTimer
from models.habitica import HabiticaDifficulty

_API_URI_BASE: Final[str] = "https://habitica.com/api/v3"
_SUCCESS_CODES = frozenset([requests.codes.ok, requests.codes.created])  # pylint: disable=no-member
_API_CALLS_DELAY: Final[DelayTimer] = DelayTimer(30, "Waiting for {delay:.0f}s between API calls.")
"""https://habitica.fandom.com/wiki/Guidance_for_Comrades#API_Server_Calls"""


class HabiticaAPIHeaders(BaseModel):
    user_id: str = Field(..., alias="x-api-user")
    api_key: str = Field(..., alias="x-api-key")
    client_id: str = Field("fb0ab2bf-675d-4326-83ba-d03eefe24cef-todoist-habitica-sync", alias="x-client")
    content_type: str = Field("application/json", alias="content-type")
    model_config = ConfigDict(populate_by_name=True)


class HabiticaAPI:
    """Access to Habitica API.

    Based on https://github.com/philadams/habitica/blob/master/habitica/api.py
    """

    def __init__(
        self,
        headers: HabiticaAPIHeaders,
        resource: str | None = None,
        aspect: str | None = None,
    ):
        self._resource = resource
        self._aspect = aspect
        self._headers = headers
        self._log = logging.getLogger(self.__class__.__name__)

    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            if not self._resource:
                return HabiticaAPI(headers=self._headers, resource=name)

            return HabiticaAPI(headers=self._headers, resource=self._resource, aspect=name)

    def __call__(self, **kwargs):
        method = kwargs.pop("_method", "get")

        # build up URL... Habitica's api is the *teeniest* bit annoying
        # so either I need to find a cleaner way here, or I should
        # get involved in the API itself and... help it.
        if self._aspect:
            aspect_id = kwargs.pop("_id", None)
            direction = kwargs.pop("_direction", None)
            uri = _API_URI_BASE
            if aspect_id is not None:
                uri = f"{uri}/{self._aspect}/{aspect_id}"
            elif self._aspect == "tasks":
                uri = f"{uri}/{self._aspect}/{self._resource}"
            else:
                uri = f"{uri}/{self._resource}/{self._aspect}"
            if direction is not None:
                uri = f"{uri}/score/{direction}"
        else:
            uri = f"{_API_URI_BASE}/{self._resource}"

        # actually make the request of the API
        http_headers = self._headers.model_dump(by_alias=True)
        _API_CALLS_DELAY()
        if method in ["put", "post", "delete"]:
            res = getattr(requests, method)(uri, headers=http_headers, data=json.dumps(kwargs))
        else:
            res = getattr(requests, method)(uri, headers=http_headers, params=kwargs)

        self._log.info(f"API call: {method.upper()} {uri}")
        self._log.info(f"Request headers: {http_headers}")
        self._log.info(f"Request payload: {kwargs}")
        self._log.info(f"Response status: {res.status_code}")
        self._log.info(f"Response payload: {res.json()}")

        if res.status_code not in _SUCCESS_CODES:
            try:
                res.raise_for_status()
            except requests.HTTPError as exc:
                self._log.error(f"API call error: {exc}, JSON Payload: {res.json()}")
                raise requests.HTTPError(f"{exc}, JSON Payload: {res.json()}", res) from exc

        return res.json()["data"]

    def create_task(self, text: str, priority: HabiticaDifficulty) -> dict[str, Any]:
        """See https://habitica.com/apidoc/#api-Task-CreateUserTasks."""
        self._log.info(f"Creating task: {text} with priority: {priority}")
        return self.user.tasks(type="todo", text=text, priority=priority.value, _method="post")

    def score_task(self, task_id: str, direction: str = "up") -> None:
        """See https://habitica.com/apidoc/#api-Task-ScoreTask."""
        self._log.info(f"Scoring task: {task_id} with direction: {direction}")
        return self.user.tasks(_id=task_id, _direction=direction, _method="post")

    def delete_task(self, task_id: str) -> None:
        """See https://habitica.com/apidoc/#api-Task-DeleteTask."""
        self._log.info(f"Deleting task: {task_id}")
        return self.user.tasks(_id=task_id, _method="delete")
