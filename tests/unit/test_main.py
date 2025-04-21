import pytest

from config import Settings
from main import TasksSync
from models.habitica import HabiticaDifficulty
from models.todoist import TodoistPriority


class TestGetTaskDifficulty:
    @staticmethod
    @pytest.mark.parametrize(
        "labels",
        [
            pytest.param([], id="labels are not defined"),
            pytest.param(["Urgent"], id="there is no matching label"),
        ],
    )
    def should_use_task_priority_if(labels: list[str]):
        settings = Settings(label_to_difficulty={})
        assert TasksSync._get_task_difficulty(settings, labels, TodoistPriority.P1) == HabiticaDifficulty.HARD

    @staticmethod
    @pytest.mark.parametrize(
        "labels",
        [
            pytest.param(["Urgent"], id="there is a matching label"),
            pytest.param(["Urgent", "Important"], id="there are multiple labels"),
        ],
    )
    def should_use_label_priority_if(labels: list[str]):
        settings = Settings(label_to_difficulty={"urgent": HabiticaDifficulty.HARD})
        assert TasksSync._get_task_difficulty(settings, labels, TodoistPriority.P1) == HabiticaDifficulty.HARD

    @staticmethod
    def should_use_highest_label_priority():
        settings = Settings(
            label_to_difficulty={
                "urgent": HabiticaDifficulty.HARD,
                "important": HabiticaDifficulty.MEDIUM,
            }
        )
        labels = ["Urgent", "Important"]
        assert TasksSync._get_task_difficulty(settings, labels, TodoistPriority.P1) == HabiticaDifficulty.HARD


class TestTaskCompletion:
    @staticmethod
    def should_not_delete_completed_tasks_in_habitica(mocker):
        mocker.patch("habitica_api.HabiticaAPI.delete_task")
        mocker.patch("habitica_api.HabiticaAPI.score_task")
        mocker.patch("todoist_api.TodoistAPI.sync", return_value="2023-01-01T00:00:00Z")
        mocker.patch("todoist_api.TodoistAPI.iter_pop_newly_completed_tasks", return_value=[
            {
                "item_object": {
                    "content": "Test Task",
                    "labels": [],
                    "priority": 1,
                }
            }
        ])

        tasks_sync = TasksSync()
        tasks_sync.run_forever()

        habitica_api = tasks_sync.habitica
        habitica_api.delete_task.assert_not_called()
        habitica_api.score_task.assert_called_once()
