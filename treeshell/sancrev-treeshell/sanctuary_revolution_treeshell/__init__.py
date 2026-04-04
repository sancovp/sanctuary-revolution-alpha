"""Sanctuary Revolution TreeShell - MCP wrapper for sanctuary-revolution."""
import json
from pathlib import Path
from heaven_tree_repl.shells import TreeShell
from heaven_tree_repl.system_config_loader_v2 import SystemConfigLoader


# Sancrev's configs dir acts as dev layer on top of heaven-tree-repl's system configs
SANCREV_CONFIGS_DIR = str(Path(__file__).parent / "configs")


class SancrevTreeShell(TreeShell):
    """Sanctuary Revolution TreeShell - game interface."""
    def __init__(self, user_config_path: str = None):
        # Store on self so base get_shortcuts() can find it
        self.system_config_loader = SystemConfigLoader(config_types=["base", "base_zone_config", "base_shortcuts", "user_shortcuts"])
        self.dev_config_path = SANCREV_CONFIGS_DIR
        final_config = self.system_config_loader.load_and_validate_configs(dev_config_path=SANCREV_CONFIGS_DIR)

        # Load families (sancrev families add on top of base families)
        families = self.system_config_loader.load_families(dev_config_path=SANCREV_CONFIGS_DIR)
        final_config['_loaded_families'] = families

        # Load nav config (sancrev's overrides base)
        nav_config = self.system_config_loader.load_nav_config(dev_config_path=SANCREV_CONFIGS_DIR)
        if nav_config:
            final_config['nav_config'] = nav_config

        # Stash config warnings so they survive init (viewable via 'health' command)
        final_config['_config_warnings'] = self.system_config_loader.get_validation_warnings()

        super().__init__(final_config)

        # Override root node description with quick-start guide
        if "0" in self.nodes:
            self.nodes["0"]["description"] = (
                "Quick Start:\n"
                "  nav          — See full tree structure\n"
                "  lang         — TreeShell language reference\n"
                "  jump cf_home — HOME HUD (orientation, skills, course state)\n"
                "  jump sancrev — Sanctuary Revolution game\n"
                "  jump gnosys  — GNOSYS tools & MCPs\n"
                "  jump skills  — Skill manager\n"
                "\n"
                "Use `jump <name>` to navigate, `<name>.exec {\"args\"}` to execute."
            )


__all__ = ["SancrevTreeShell"]
