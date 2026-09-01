#!/usr/bin/env python3
import os
import sys
import time

from playwright.sync_api import sync_playwright


SITE = os.getenv("SITE_URL") or "https://agentrouter.org"
PROFILE = os.getenv("BROWSER_PROFILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".github-browser",
)
CHANNEL = os.getenv("BROWSER_CHANNEL") or "msedge"
HEADLESS = os.getenv("HEADLESS", "1").lower() in ("1", "true", "yes")


def format_balance(quota) -> str:
    if quota is None:
        return "N/A"
    return f"{float(quota) / 500000:.2f}$"


def fetch_quota(page) -> dict:
    return page.evaluate(
        """
        async () => {
            try {
                const userStr = localStorage.getItem('user');
                if (!userStr) {
                    return { success: false, error: 'USER_NOT_FOUND' };
                }

                const user = JSON.parse(userStr);
                if (!user.id) {
                    return { success: false, error: 'USER_ID_INVALID' };
                }

                const response = await fetch('/api/user/self', {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json, text/plain, */*',
                        'New-API-User': String(user.id)
                    },
                    credentials: 'include',
                    cache: 'no-store'
                });

                const payload = await response.json();

                return {
                    success: response.ok && payload.success === true,
                    status: response.status,
                    error: payload.success === false ? payload.message : null,
                    quota: payload.data && payload.data.quota
                };
            } catch (err) {
                return { success: false, error: 'API_ERROR' };
            }
        }
        """
    )


def wait_for_user(page, timeout_ms: int = 45000) -> bool:
    deadline = time.time() + timeout_ms / 1000.0
    while time.time() < deadline:
        try:
            has_user = page.evaluate(
                "() => Boolean(localStorage.getItem('user'))"
            )
            if has_user:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main() -> int:
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            PROFILE,
            channel=CHANNEL,
            headless=HEADLESS,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(f"{SITE}/login", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)

        if not wait_for_user(page, timeout_ms=10000):
            github_button = page.get_by_text("使用 GitHub 继续")
            if github_button.count() > 0:
                github_button.first.click(timeout=10000)

            for _ in range(30):
                if "github.com" in page.url:
                    break
                page.wait_for_timeout(1000)

            if "github.com" in page.url:
                body = page.locator("body").inner_text(timeout=5000)
                login_prompt = (
                    "Sign in to GitHub" in body
                    or "password" in body.lower()
                    or "two-factor" in body.lower()
                    or "2fa" in body.lower()
                )
                if login_prompt:
                    print("GitHub 未登录或需要验证，请先运行 github_login_setup.py")
                    context.close()
                    return 2

                authorize = page.locator(
                    "button:has-text('Authorize'), button:has-text('授权')"
                )
                if authorize.count() > 0:
                    authorize.first.click(timeout=10000)

        ok = wait_for_user(page, timeout_ms=45000)

        if not ok:
            print("签到失败：未获取到 AgentRouter 登录态")
            context.close()
            return 1

        result = fetch_quota(page)
        context.close()

        if result.get("success"):
            print(f"当前余额 {format_balance(result.get('quota'))}")
            return 0

        print(
            "签到失败：",
            result.get("error") or result.get("status") or "UNKNOWN",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
