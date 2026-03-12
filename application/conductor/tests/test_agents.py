"""Tests for SDNAC agent factories."""

import pytest
from unittest.mock import patch, MagicMock

from conductor.agents import make_grug_sdnac, make_researcher_sdnac
from conductor.config import GRUG_MODEL, RESEARCHER_MODEL


class TestMakeGrugSdnac:
    @patch("conductor.agents.sdnac")
    @patch("conductor.agents.ariadne")
    @patch("conductor.agents.default_config")
    def test_creates_sdnac_with_correct_config(self, mock_config, mock_ariadne, mock_sdnac):
        mock_config.return_value = MagicMock()
        mock_ariadne.return_value = MagicMock()

        make_grug_sdnac("You are SmartGrug.")

        mock_config.assert_called_once_with(
            name="grug",
            goal="{task}",
            system_prompt="You are SmartGrug.",
            max_turns=10,
            model=GRUG_MODEL,
        )
        mock_ariadne.assert_called_once_with("grug_prep")
        mock_sdnac.assert_called_once_with("grug", mock_ariadne.return_value, mock_config.return_value)

    @patch("conductor.agents.sdnac")
    @patch("conductor.agents.ariadne")
    @patch("conductor.agents.default_config")
    def test_custom_model(self, mock_config, mock_ariadne, mock_sdnac):
        mock_config.return_value = MagicMock()
        mock_ariadne.return_value = MagicMock()

        make_grug_sdnac("prompt", model="custom-model")

        mock_config.assert_called_once_with(
            name="grug",
            goal="{task}",
            system_prompt="prompt",
            max_turns=10,
            model="custom-model",
        )


class TestMakeResearcherSdnac:
    @patch("conductor.agents.sdnac")
    @patch("conductor.agents.ariadne")
    @patch("conductor.agents.default_config")
    def test_creates_sdnac_with_correct_config(self, mock_config, mock_ariadne, mock_sdnac):
        mock_config.return_value = MagicMock()
        mock_ariadne.return_value = MagicMock()

        make_researcher_sdnac("You are Dr. Randy.")

        mock_config.assert_called_once_with(
            name="researcher",
            goal="{phase_prompt}",
            system_prompt="You are Dr. Randy.",
            max_turns=10,
            model=RESEARCHER_MODEL,
        )
        mock_ariadne.assert_called_once_with("researcher_prep")
        mock_sdnac.assert_called_once_with("researcher", mock_ariadne.return_value, mock_config.return_value)

    @patch("conductor.agents.sdnac")
    @patch("conductor.agents.ariadne")
    @patch("conductor.agents.default_config")
    def test_goal_template_uses_phase_prompt(self, mock_config, mock_ariadne, mock_sdnac):
        mock_config.return_value = MagicMock()
        mock_ariadne.return_value = MagicMock()

        make_researcher_sdnac("prompt")

        goal_arg = mock_config.call_args[1]["goal"]
        assert goal_arg == "{phase_prompt}"
