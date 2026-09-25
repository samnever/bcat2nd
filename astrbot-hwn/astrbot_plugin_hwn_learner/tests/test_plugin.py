import json
import shutil
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from astrbot_plugin_hwn_learner.main import HwnLearnerPlugin


class FakePersonaManager:
    def __init__(self):
        self.personas = {}

    async def get_persona(self, persona_id):
        if persona_id not in self.personas:
            raise ValueError("missing")
        return self.personas[persona_id]

    async def create_persona(self, **kwargs):
        persona = SimpleNamespace(**kwargs)
        self.personas[kwargs["persona_id"]] = persona
        return persona

    async def update_persona(self, persona_id, **kwargs):
        persona = self.personas[persona_id]
        for key, value in kwargs.items():
            setattr(persona, key, value)
        return persona


class FakeContext:
    def __init__(self):
        self.persona_manager = FakePersonaManager()

    async def get_current_chat_provider_id(self, umo):
        return "fake-provider"

    async def llm_generate(self, **_kwargs):
        return SimpleNamespace(
            completion_text=json.dumps(
                {
                    "traits": [
                        {
                            "text": "倾向先给结论再补理由",
                            "confidence": 0.95,
                            "evidence_indexes": [0, 1, 2],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        )


class PluginIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_root = Path(__file__).parent / ".tmp" / uuid.uuid4().hex
        self.temp_root.mkdir(parents=True)

    async def asyncTearDown(self):
        shutil.rmtree(self.temp_root, ignore_errors=True)

    async def test_initialize_distill_and_sync(self):
        context = FakeContext()
        config = {
            "enabled": True,
            "owner_user_id": "owner",
            "batch_size": 3,
            "minimum_confidence": 0.8,
            "auto_sync_persona": True,
            "persona_id": "hwn",
        }
        with patch(
            "astrbot_plugin_hwn_learner.main.get_astrbot_data_path",
            return_value=str(self.temp_root),
        ):
            plugin = HwnLearnerPlugin(context, config)
            await plugin.initialize()
            self.assertTrue((self.temp_root / "skills" / "hwn" / "SKILL.md").exists())
            self.assertIn("hwn", context.persona_manager.personas)
            for index in range(3):
                plugin.observations.append(
                    {
                        "message_id": str(index),
                        "text": f"第 {index} 条先说结论的消息",
                    }
                )
            processed, added = await plugin._distill("qq:group:1", force=True)
            self.assertEqual(processed, 3)
            self.assertEqual(added, ["倾向先给结论再补理由"])
            persona = context.persona_manager.personas["hwn"]
            self.assertIn("倾向先给结论再补理由", persona.system_prompt)
            self.assertEqual(persona.skills, ["hwn"])


if __name__ == "__main__":
    unittest.main()
