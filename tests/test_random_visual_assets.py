from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from xml.etree import ElementTree

from variants import (
    ALL_VARIANTS,
    C2V,
    CATALOGUED_VARIANT_ICON,
    CATALOGUED_VARIANTS,
    SVG_VARIANT_ICONS,
    VARIANT_ICONS,
    ServerVariants,
    register_catalogued_server_variant,
)

ROOT = Path(__file__).resolve().parents[1]


class RandomVisualAssetsTest(TestCase):
    def test_server_icon_keys_have_svg_masks_and_local_assets(self) -> None:
        css = (ROOT / "static/random-icons.css").read_text(encoding="utf-8")
        self.assertEqual(len(set(SVG_VARIANT_ICONS.values())), len(SVG_VARIANT_ICONS))
        for name, icon in SVG_VARIANT_ICONS.items():
            with self.subTest(variant=name):
                self.assertEqual(len(icon), 1)
                self.assertIn(f'[data-icon="\\{ord(icon):x}"]', css)
                filename = {
                    "rifle-chess": "riflechess",
                    "spell-chess": "spellchess",
                }.get(name, name)
                self.assertIn(f"url('icons/{filename}.svg')", css)
                root = ElementTree.parse(ROOT / f"static/icons/{filename}.svg").getroot()
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_catalogued_pack_variants_use_their_own_icon(self) -> None:
        with (
            patch.dict(CATALOGUED_VARIANTS),
            patch.dict(ALL_VARIANTS),
            patch.dict(VARIANT_ICONS),
            patch.dict(C2V),
        ):
            for name, icon in SVG_VARIANT_ICONS.items():
                if name in ("losers", "randomdice"):
                    continue
                with self.subTest(variant=name):
                    variant = register_catalogued_server_variant(name, name)
                    self.assertEqual(variant.icon, icon)
                    self.assertEqual(VARIANT_ICONS[name], icon)
            unknown = register_catalogued_server_variant("unknown-pack-test", "Unknown")
            self.assertEqual(unknown.icon, CATALOGUED_VARIANT_ICON)
        self.assertEqual(ServerVariants.LOSERS.icon, SVG_VARIANT_ICONS["losers"])
