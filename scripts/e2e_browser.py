"""Experiment 6 (application testing): drive the REAL app in Microsoft Edge with Playwright.

Starts the FastAPI backend (throw-away database) and the Vite dev server, walks through the
main user journeys in English, Telugu and Hindi (desktop + mobile), checks the outcome of each
step and saves screenshots to reports/figures/p9_*.png.

Usage: python scripts/e2e_browser.py          (needs: pip install playwright; Edge installed)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx
from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "reports" / "figures"
APP = "http://127.0.0.1:5173"
RESULTS: list[tuple[str, bool, str]] = []


def wait_for(url: str, timeout: float = 90) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            if httpx.get(url, timeout=2).status_code < 500:
                return
        except httpx.HTTPError:
            time.sleep(0.5)
    raise SystemExit(f"{url} did not start")


def step(name: str, fn) -> None:
    try:
        fn()
        RESULTS.append((name, True, ""))
        print(f"  PASS  {name}")
    except Exception as exc:  # noqa: BLE001 - report every failure and continue
        RESULTS.append((name, False, str(exc).splitlines()[0][:160]))
        print(f"  FAIL  {name}: {RESULTS[-1][2]}")


def answer_all(page: Page) -> None:
    """Generic, conservative answers: 'none of these', age 30, pain 3, second option of radios."""
    for fs in page.locator("fieldset.question").all():
        boxes = fs.locator("input[type=checkbox]")
        if boxes.count():
            boxes.last.check()                       # "None of these" is always last
        num = fs.locator("input[type=number]")
        if num.count():
            legend = fs.locator("legend").inner_text()
            num.fill("3" if re.search(r"0.*10", legend) else "30")
        radios = fs.locator("input[type=radio]")
        if radios.count() > 1:
            radios.nth(1).check()                     # gradual / 1-4 days / no


def shot(page: Page, name: str) -> None:
    page.screenshot(path=str(FIG / f"p9_{name}.png"), full_page=True)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "MEDIGUIDE_DB_URL": f"sqlite:///{tempfile.mkdtemp()}/e2e.db".replace("\\", "/")}
    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8000"],
                               cwd=ROOT / "backend", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    vite = subprocess.Popen(["node", "node_modules/vite/bin/vite.js", "--port", "5173", "--strictPort", "--host", "127.0.0.1"],
                            cwd=ROOT / "frontend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for("http://127.0.0.1:8000/api/health")
        wait_for(APP)
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            desk = browser.new_context(viewport={"width": 1280, "height": 900}, locale="en-IN")
            page = desk.new_page()

            def welcome():
                page.goto(APP)
                expect(page.get_by_role("heading", level=1)).to_contain_text("Describe your symptoms")
                expect(page.get_by_text("Call 112 or 108")).to_be_visible()
                shot(page, "01_welcome_en")
            step("Welcome page (EN) with emergency notice", welcome)

            def telugu_ui():
                page.get_by_role("button", name="తెలుగు").click()
                expect(page.get_by_role("heading", level=1)).to_contain_text("మీ లక్షణాలను")
                shot(page, "02_welcome_te")
                page.get_by_role("button", name="English").click()
            step("Language switch to Telugu", telugu_ui)

            def chest_pain_emergency():
                page.goto(f"{APP}/assess")
                page.locator("#symptoms").fill("I have chest pain")
                page.get_by_role("button", name="Check urgency").click()
                expect(page.get_by_role("heading", name="A few questions")).to_be_visible()
                expect(page.locator(".understood")).to_contain_text("Chest pain")
                shot(page, "03_followup_en")
                page.get_by_label("Pain spreading to arm, jaw, neck or back").check()
                page.get_by_label(re.compile("How old")).fill("50")
                page.get_by_role("button", name="See my result").click()
                expect(page.locator(".emergency-banner")).to_be_visible()
                expect(page.get_by_role("link", name="Call 112")).to_have_attribute("href", "tel:112")
                expect(page.locator(".badge-large")).to_contain_text("Emergency")
                shot(page, "04_result_emergency_en")
            step("EN: chest pain -> follow-up -> EMERGENCY with call buttons", chest_pain_emergency)

            def immediate_emergency():
                page.goto(f"{APP}/assess")
                page.locator("#symptoms").fill("My father's face is drooping and he cannot speak properly")
                page.get_by_role("button", name="Check urgency").click()
                expect(page.locator(".emergency-banner")).to_be_visible()   # no questions page in between
                expect(page.get_by_text("Possible stroke warning signs (FAST)")).to_be_visible()
            step("EN: stroke signs -> EMERGENCY immediately (no questions)", immediate_emergency)

            mob = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            m = mob.new_page()

            def hindi_mobile():
                m.goto(APP)
                m.get_by_role("button", name="हिंदी").click()
                m.goto(f"{APP}/assess")
                m.locator("#symptoms").fill("मुझे दो दिन से बुखार और खांसी है")
                m.get_by_role("button", name="तत्कालता जांचें").click()
                expect(m.get_by_role("heading", name="कुछ सवाल")).to_be_visible()
                shot(m, "05_followup_hi_mobile")
                answer_all(m)
                m.get_by_role("button", name="मेरा नतीजा देखें").click()
                expect(m.locator(".badge-large")).to_be_visible()
                expect(m.locator(".safety-net")).to_contain_text("112")
                shot(m, "06_result_hi_mobile")
            step("HI (mobile): fever + cough -> questions in Hindi -> result with safety-net", hindi_mobile)

            def telugu_text():
                m.goto(APP)
                m.get_by_role("button", name="తెలుగు").click()
                m.goto(f"{APP}/assess")
                m.locator("#symptoms").fill("ఊపిరి అందడం లేదు, పెదవులు నీలంగా మారుతున్నాయి")
                m.get_by_role("button", name="అత్యవసర స్థాయి తెలుసుకోండి").click()
                expect(m.locator(".emergency-banner")).to_contain_text("అత్యవసర")
                shot(m, "07_result_emergency_te_mobile")
            step("TE (mobile): breathing emergency in Telugu", telugu_text)

            def account_history():
                ctx = browser.new_context(viewport={"width": 1280, "height": 900})
                pg = ctx.new_page()
                pg.on("dialog", lambda d: d.accept())
                pg.goto(f"{APP}/register")
                pg.get_by_label("Email").fill(f"e2e-{uuid.uuid4().hex[:6]}@example.com")
                pg.get_by_label("Password").fill("e2e-password-1")
                pg.get_by_role("button", name="Create account").click()
                expect(pg.get_by_role("heading", name="My profile")).to_be_visible()
                pg.get_by_label("Age (years)").fill("25")
                pg.get_by_label("Male", exact=True).check()
                pg.get_by_role("button", name="Save profile").click()
                expect(pg.get_by_text("Profile saved.")).to_be_visible()
                shot(pg, "08_profile")
                pg.goto(f"{APP}/assess")
                pg.locator("#symptoms").fill("runny nose and sneezing")
                pg.get_by_label("Save this assessment to my history").check()
                pg.get_by_role("button", name="Check urgency").click()
                expect(pg.locator(".badge-large")).to_be_visible()
                shot(pg, "09_result_saved")
                pg.get_by_role("link", name="Go to my history").click()
                expect(pg.locator(".history-item")).to_have_count(1)
                expect(pg.locator(".history-item")).to_contain_text("runny nose and sneezing")
                shot(pg, "10_history")
                pg.get_by_role("button", name="Delete", exact=True).click()
                expect(pg.get_by_text("You have no saved assessments yet.")).to_be_visible()
                ctx.close()
            step("Register -> profile -> saved assessment -> history -> delete", account_history)

            def admin_dashboard():
                ctx = browser.new_context(viewport={"width": 1280, "height": 900})
                pg = ctx.new_page()
                email = f"admin-{uuid.uuid4().hex[:6]}@example.com"
                pg.goto(f"{APP}/register")
                pg.get_by_label("Email").fill(email)
                pg.get_by_label("Password").fill("admin-password-1")
                pg.get_by_role("button", name="Create account").click()
                expect(pg.get_by_role("heading", name="My profile")).to_be_visible()
                pg.goto(f"{APP}/admin")                          # not yet an admin -> sent home
                expect(pg.get_by_role("heading", level=1)).not_to_contain_text("Admin")
                subprocess.run([sys.executable, str(ROOT / "scripts" / "create_admin.py"), email],
                               env=env, check=True, capture_output=True)
                pg.goto(f"{APP}/admin")
                expect(pg.get_by_text("Completed assessments")).to_be_visible()
                expect(pg.get_by_role("img", name="Urgency recommendations")).to_be_visible()
                expect(pg.locator("body")).not_to_contain_text("runny nose and sneezing")   # user text never shown (labels are fine)
                shot(pg, "11_admin_dashboard")
                # DEMO data: synthetic test sentences run through the real engine, so the charts have bars
                subprocess.run([sys.executable, str(ROOT / "scripts" / "seed_demo_stats.py")],
                               env=env, check=True, capture_output=True)
                pg.reload()
                expect(pg.get_by_role("img", name="Urgency recommendations")).to_be_visible()
                shot(pg, "12_admin_dashboard_demo_data")
                ctx.close()
            step("Admin: blocked before promotion, dashboard after (no free text shown)", admin_dashboard)

            def keyboard_access():
                page.goto(f"{APP}/assess")
                page.keyboard.press("Tab")
                expect(page.locator(".skip-link")).to_be_focused()
            step("Keyboard: first Tab reaches the skip link", keyboard_access)
            browser.close()
    finally:
        for proc in (vite, backend):
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    passed = sum(ok for _, ok, _ in RESULTS)
    print(f"\nBrowser walk-through: {passed}/{len(RESULTS)} steps passed")
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
