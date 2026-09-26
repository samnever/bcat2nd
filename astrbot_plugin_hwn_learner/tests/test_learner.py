import json
import shutil
import unittest
import uuid
from pathlib import Path

from astrbot_plugin_hwn_learner.learner import (
    ObservationStore,
    SkillStore,
    normalize_message,
    validate_traits,
)


class LearnerTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(__file__).parent / ".tmp" / uuid.uuid4().hex
        self.temp_root.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_normalize_message_filters_unsafe_sources(self):
        self.assertEqual(normalize_message("[At:bot] 你好啊", "", 100), "你好啊")
        self.assertIsNone(normalize_message("/hwn status", "", 100))
        self.assertIsNone(normalize_message("https://example.com", "", 100))
        self.assertIsNone(normalize_message("正常文字", "[引用消息(x: y)]", 100))

    def test_validate_traits_requires_three_evidence_items(self):
        raw = json.dumps(
            {
                "traits": [
                    {
                        "text": "倾向先给结论再补理由",
                        "confidence": 0.9,
                        "evidence_indexes": [0, 1, 2],
                    },
                    {
                        "text": "证据不足",
                        "confidence": 0.99,
                        "evidence_indexes": [0, 1],
                    },
                ]
            },
            ensure_ascii=False,
        )
        traits = validate_traits(raw, 3, 0.8)
        self.assertEqual([item["text"] for item in traits], ["倾向先给结论再补理由"])

    def test_observation_cursor(self):
        store = ObservationStore(self.temp_root)
        store.append({"message_id": "1", "text": "a"})
        store.append({"message_id": "2", "text": "b"})
        self.assertEqual(len(store.pending()), 2)
        store.mark_processed(1)
        self.assertEqual([item["text"] for item in store.pending()], ["b"])

    def test_skill_updates_and_backs_up(self):
        root = self.temp_root
        seed = root / "seed"
        skill_dir = root / "skills" / "hwn"
        data_dir = root / "data"
        seed.mkdir(parents=True)
        (seed / "SKILL.md").write_text("---\nname: hwn\ndescription: test\n---\n", encoding="utf-8")
        (seed / "self.md").write_text("# Self\n\n## Correction 记录\n\n- 暂无。\n", encoding="utf-8")
        (seed / "persona.md").write_text("# Persona\n\n## Correction 记录\n\n- 暂无。\n", encoding="utf-8")
        (seed / "meta.json").write_text(
            json.dumps({"version": "v1", "memory_sources": []}), encoding="utf-8"
        )
        store = SkillStore(skill_dir, seed, data_dir)
        store.ensure_seeded()
        added = store.append_traits(
            [{"text": "先给结论", "confidence": 0.9, "evidence_indexes": [0, 1, 2]}]
        )
        self.assertEqual(added, ["先给结论"])
        self.assertIn("先给结论", (skill_dir / "persona.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((skill_dir / "meta.json").read_text())["version"], "v2")
        self.assertTrue(any((data_dir / "backups").iterdir()))


if __name__ == "__main__":
    unittest.main()
