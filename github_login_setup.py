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


def main() -> int:
    print("准备打开浏览器，请完成 GitHub 授权并回到 AgentRouter 页面。")
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            PROFILE,
            channel=CHANNEL,
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(f"{SITE}/login", wait_until="domcontentloaded", timeout=45000)

        print("请在打开的浏览器里点击“使用 GitHub 继续”，完成登录/授权。")
        input("登录完成后，看到 AgentRouter 控制台后回到这里按 Enter 继续...")

        for _ in range(30):
            try:
                has_user = page.evaluate(
                    "() => Boolean(localStorage.getItem('user'))"
                )
                if has_user:
                    break
            except Exception:
                pass
            time.sleep(1)

        try:
            has_user = page.evaluate(
                "() => Boolean(localStorage.getItem('user'))"
            )
        except Exception:
            has_user = False

        context.close()

    if has_user:
        print("GitHub 登录态已保存，可以继续使用签到脚本。")
        return 0

    print("未检测到 AgentRouter 登录态，请重新运行本脚本完成授权。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
