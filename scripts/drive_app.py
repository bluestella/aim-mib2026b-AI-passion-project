"""Drive the PWA end to end in a real browser and assert its invariants.

Not part of the pytest suite — it needs Playwright, Chromium, and a running server,
which is a lot of machinery to demand of someone who only wants to change a rule.
But the app's guarantees (§7.8 attribution, the no-market verdict, the override
behaviour) only actually hold in a browser, so this exists to check them there
rather than by reading the code and hoping.

It is also the fastest way to catch the class of bug a unit test structurally
cannot: a render path that throws, a view that never becomes visible, or an
animation whose timers are cancelled by the navigation that triggered it. Both of
those were real bugs found here, not by inspection.

Setup:
    pip install -e ".[browser]"
    python -m playwright install chromium    # skip if PLAYWRIGHT_BROWSERS_PATH is set

Run:
    python -m http.server 8765 --directory app &
    python scripts/drive_app.py
    python scripts/drive_app.py --screenshots ./shots
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_URL = "http://127.0.0.1:8765/index.html"


def chromium_executable() -> str | None:
    """Locate a usable Chromium, tolerating a pinned-version mismatch.

    A preinstalled browser directory often carries a different build number than
    the Playwright package expects, and Playwright then refuses to launch even
    though a perfectly good Chromium is sitting right there. Rather than making
    the caller run a multi-hundred-megabyte download, find the existing binary
    and pass it explicitly. Returns None to let Playwright use its own default.
    """
    override = os.environ.get("DALOY_CHROMIUM")
    if override:
        return override

    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not root or not Path(root).is_dir():
        return None

    candidates = sorted(Path(root).glob("chromium-*/chrome-linux*/chrome"))
    return str(candidates[-1]) if candidates else None

# Portrait phone. The app is used one-handed on a street, and a desktop viewport
# hides every layout problem that actually matters.
VIEWPORT = {"width": 390, "height": 844}


def run(url: str, shots: Path | None) -> int:
    errors: list[str] = []

    def shoot(page, name: str) -> None:
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots / f"{name}.png"), full_page=True)

    with sync_playwright() as p:
        executable = chromium_executable()
        browser = (
            p.chromium.launch(executable_path=executable)
            if executable
            else p.chromium.launch()
        )
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)

        page.on(
            "console",
            lambda m: errors.append(f"console.{m.type}: {m.text}")
            if m.type == "error"
            else None,
        )
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        page.goto(url, wait_until="networkidle")

        # -- Setup: barangay selection replaces GPS entirely ---------------
        assert page.locator("#view-setup").is_visible(), "setup view not shown"
        assert page.locator("#barangay-list .choice").count() == 7
        shoot(page, "01_setup")
        page.locator("#barangay-list .choice", has_text="San Juan").first.click()

        # -- Picker --------------------------------------------------------
        page.wait_for_selector("#view-picker:not([hidden])")
        assert page.locator("#material-list .choice").count() == 11
        shoot(page, "02_picker")

        # -- Sachet: the critical class -------------------------------------
        page.locator("#material-list .choice", has_text="sachet").first.click()
        page.wait_for_selector("#view-modifiers:not([hidden])")
        shoot(page, "03_modifiers")
        page.click("#mod-continue")

        page.wait_for_selector("#view-card:not([hidden])")
        card = page.locator("#card").inner_text()
        assert "Walang bumibili" in card, "sachet card must state there is no market"
        assert "bumabara" in card, "sachet card must carry the creek-clogging flag"
        assert "Hindi pa nabe-verify" in card, "§7.8 disclaimer missing"
        assert "opisyal na pahayag" in card, "§7.8 non-attribution missing"
        shoot(page, "04_card_sachet")

        # -- Flow simulation: every stage must animate in --------------------
        page.click("#act-flow")
        page.wait_for_selector("#view-flow:not([hidden])")
        total = page.locator("#flow-stages li").count()
        assert total >= 3, "leakage path is suspiciously short"
        page.wait_for_function(
            "n => document.querySelectorAll('#flow-stages li.on').length === n",
            arg=total,
            timeout=15000,
        )
        assert "leakage" in page.locator("#flow-stages").get_attribute("class")
        assert "Schematic" in page.locator("#flow-caveat").inner_text()
        shoot(page, "05_flow_leakage")

        # -- PET: recovery path with a price ---------------------------------
        page.click("#flow-back")
        page.click("#act-again")
        page.wait_for_selector("#view-picker:not([hidden])")
        page.locator("#material-list .choice", has_text="bote").first.click()
        page.click("#mod-continue")
        pet = page.locator("#card").inner_text()
        assert "PHP 10-14/kg" in pet, "PET price missing"
        assert "Tinatayang presyo" in pet, "unverified-price caveat missing"
        shoot(page, "06_card_pet")

        # -- Contamination override rewrites verdict AND guidance -------------
        page.click("#back")
        page.wait_for_selector("#view-modifiers:not([hidden])")
        page.locator(".toggle", has_text="dumi ng pagkain").locator("input").check()
        page.click("#mod-continue")
        over = page.locator("#card").inner_text()
        assert "Residual" in over, "contamination override did not apply"
        assert "banlawan at patuyuin" in over, "override did not replace the prep text"
        assert "Tinatayang presyo" not in over, "price caveat shown with no price on screen"
        shoot(page, "07_card_override")

        # Navigating back must show the checkbox that produced that verdict.
        page.click("#back")
        page.wait_for_selector("#view-modifiers:not([hidden])")
        assert (
            page.locator(".toggle", has_text="dumi ng pagkain").locator("input").is_checked()
        ), "modifier state desynced from the verdict"

        # -- Glass: nominal price, usually refused ----------------------------
        page.click("#back")
        page.wait_for_selector("#view-picker:not([hidden])")
        glass = page.locator("#material-list .choice", has_text="salamin").first
        assert "Madalas tinatanggihan" in glass.inner_text(), (
            "glass must not advertise a green price tag"
        )

        # -- Bote Bank ---------------------------------------------------------
        page.locator("#material-list .choice", has_text="lata").first.click()
        page.click("#mod-continue")
        page.click("#act-save")
        page.wait_for_timeout(300)
        page.locator('.tabbar button[data-goto="bank"]').click()
        page.wait_for_selector("#view-bank:not([hidden])")
        totals = page.locator("#bank-totals").inner_text()
        assert "1" in totals
        assert "PHP" not in totals, "bank must not total unverified prices into pesos"
        shoot(page, "08_bank")

        # -- Junkshops: honest empty state --------------------------------------
        page.locator('.tabbar button[data-goto="shops"]').click()
        page.wait_for_selector("#view-shops:not([hidden])")
        shops = page.locator("#shops-body").inner_text()
        assert "Wala pa kaming listahan" in shops
        assert "marami" in shops, "empty state must not imply Cainta has no junkshops"
        shoot(page, "09_shops")

        # -- Persistence and dark mode ------------------------------------------
        page.reload(wait_until="networkidle")
        assert page.locator("#view-picker").is_visible(), "barangay did not persist"

        page.emulate_media(color_scheme="dark")
        page.locator('.tabbar button[data-goto="picker"]').click()
        shoot(page, "10_dark")

        browser.close()

    if errors:
        print("JS errors:")
        for err in errors:
            print("  ", err)
        return 1

    print("All browser assertions passed, no JS errors.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument(
        "--screenshots", type=Path, help="Directory to write one screenshot per screen."
    )
    args = parser.parse_args()

    try:
        return run(args.url, args.screenshots)
    except AssertionError as exc:
        print(f"ASSERTION FAILED: {exc}")
        return 1
    except Exception as exc:
        print(f"FAILED: {exc}")
        print("\nIs the app being served?\n  python -m http.server 8765 --directory app")
        return 1


if __name__ == "__main__":
    sys.exit(main())
