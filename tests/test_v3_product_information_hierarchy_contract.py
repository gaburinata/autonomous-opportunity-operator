"""AOO homepage information-hierarchy contract.

This checks actual source order, not merely the presence of labels.

Primary journey:
    product value proposition
    -> user's decision profile
    -> personalized opportunity surfaces
    -> optional advanced/manual discovery
"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_HOME = ROOT / "src/opportunity_operator/product_home.py"


class ProductInformationHierarchyContractTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source = PRODUCT_HOME.read_text(encoding="utf-8")

    def position(self, marker: str) -> int:
        position = self.source.find(marker)
        self.assertGreaterEqual(
            position,
            0,
            msg=f"Required homepage marker is absent: {marker!r}",
        )
        return position

    def test_primary_journey_is_profile_first(self):
        hero = self.position('<section class="hero')
        profile = self.position("Decision profile")
        surfaces = self.position('id="productLanes"')
        advanced = self.position("Advanced search")

        self.assertLess(
            hero,
            profile,
            "Value proposition must precede the decision profile.",
        )
        self.assertLess(
            profile,
            surfaces,
            "Decision profile must precede personalized opportunity surfaces.",
        )
        self.assertLess(
            surfaces,
            advanced,
            "Advanced/manual discovery must be secondary to the personalized journey.",
        )

    def test_primary_call_to_action_precedes_manual_search(self):
        personalize = self.position("Personalize opportunities")
        manual_search = self.position("Find new opportunities")

        self.assertLess(
            personalize,
            manual_search,
            "Personalization must be primary; manual discovery must be secondary.",
        )

    def test_copy_and_visual_order_tell_the_same_story(self):
        primary_query_copy = self.position(
            "Your profile is the primary query."
        )
        advanced = self.position("Advanced search")

        self.assertLess(
            primary_query_copy,
            advanced,
            "Profile-first copy must appear before advanced search.",
        )


if __name__ == "__main__":
    unittest.main()
