"""SKILL.md frontmatter stays loadable: hosts drop or truncate descriptions over 1024 characters."""

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "illustrate" / "SKILL.md"


class SkillFrontmatter(unittest.TestCase):
    def test_description_is_valid_and_bounded(self):
        text = SKILL.read_text(encoding="utf-8")
        match = re.match(r"---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(match, "SKILL.md must open with a frontmatter block")
        fields = dict(re.findall(r"^(\w+): (.*)$", match.group(1), re.M))
        self.assertEqual(fields.get("name"), "illustrate")
        description = fields.get("description", "")
        if description.startswith('"'):
            self.assertTrue(description.endswith('"'), "quoted description must close its quote")
            description = description[1:-1].replace('\\"', '"')
        else:
            self.assertNotIn(": ", description, "unquoted ': ' breaks YAML; quote the description")
        self.assertLessEqual(len(description), 1024)
        for trigger in ("diagram", "chart", "illustrat", ".drawio", ".excalidraw"):
            self.assertIn(trigger, description)


class SkillEntry(unittest.TestCase):
    """The entry file stays procedure-first and small; every link it and the references carry resolves."""

    REFERENCES = SKILL.parent / "references"
    LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)\s]*)?\)")

    def test_entry_is_small(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 200)
        self.assertLessEqual(len(text.encode("utf-8")), 12_500)
        procedure, index = text.find("To create a new diagram"), text.find("Choosing the type")
        self.assertTrue(0 < procedure < index, "the create procedure comes before the type section")

    def test_links_resolve(self):
        for document in (SKILL, *sorted(self.REFERENCES.glob("*.md"))):
            for target in self.LINK.findall(document.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                with self.subTest(document=document.name, target=target):
                    self.assertTrue((document.parent / target).exists())

    def test_type_index_lists_every_type_reference_once(self):
        index = (self.REFERENCES / "type-index.md").read_text(encoding="utf-8")
        listed = re.findall(r"\]\((type-[a-z0-9-]+\.md)\)", index)
        shipped = sorted(p.name for p in self.REFERENCES.glob("type-*.md") if p.name != "type-index.md")
        self.assertEqual(sorted(listed), shipped)
        self.assertIn("references/type-index.md", SKILL.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
