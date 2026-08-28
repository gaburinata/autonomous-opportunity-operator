"""AOO front-door usability contract.

This contract exists because source-order alone was insufficient:
the old two-panel hero still forced the user to scroll before reaching
the primary interaction.

The first product surface must make AOO understandable AND usable:
    promise -> profile -> primary action

Radar telemetry, manual search, and explanatory content are secondary.
"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "src/opportunity_operator/product_home.py"


class FrontDoorUsabilityContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = HOME.read_text(encoding="utf-8")

    def position(self, marker: str) -> int:
        pos = self.source.find(marker)
        self.assertGreaterEqual(
            pos,
            0,
            msg=f"Required marker absent: {marker!r}",
        )
        return pos

    def test_profile_form_is_inside_the_hero_front_door(self):
        hero_start = self.position('<section class="hero')
        hero_end = self.source.find("</section>", hero_start)
        self.assertGreater(hero_end, hero_start)

        form = self.position('<form id="profileForm">')

        self.assertLess(hero_start, form)
        self.assertLess(
            form,
            hero_end,
            "The primary profile interaction must be directly inside the first hero surface.",
        )

    def test_legacy_two_panel_radar_hero_is_gone(self):
        hero_start = self.position('<section class="hero')
        hero_end = self.source.find("</section>", hero_start)
        radar = self.position("Latest stored Radar snapshot")

        self.assertNotIn(
            "Your opportunity inbox,",
            self.source,
            "The old inbox-first hero must not survive the redesign.",
        )

        self.assertGreater(
            radar,
            hero_end,
            "Radar telemetry must be secondary, not half of the hero.",
        )

    def test_primary_action_is_find_for_me_not_manual_search(self):
        primary = self.position("Find what AI can do for me")
        surfaces = self.position('id="productLanes"')
        manual = self.position("Advanced search")

        self.assertLess(primary, surfaces)
        self.assertLess(
            primary,
            manual,
            "The personalized AOO action must precede manual discovery.",
        )

    def test_front_door_explains_the_full_product_thesis(self):
        self.assertIn(
            "build, operate, or pursue for you",
            self.source,
        )
        self.assertIn(
            "Synthesizes latent opportunities",
            self.source,
        )
        self.assertIn(
            "ideas no one posted",
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
