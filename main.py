import os
import time
import subprocess
import requests
from DrissionPage import ChromiumPage, ChromiumOptions


# =========================
# 配置
# =========================
URL = "https://g4f.gg/dsfyos"
TARGET_HOURS = 72
MAX_LOOPS = 20

COOLDOWN_SECONDS = 8
IP_FAIL_THRESHOLD = 3


TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# =========================
# 状态定义
# =========================
STATE_INIT = "INIT"
STATE_LOADING = "LOADING"
STATE_READY = "READY"
STATE_BLOCKED = "BLOCKED"
STATE_COOLDOWN = "COOLDOWN"
STATE_ERROR = "ERROR"


# =========================
# 工具函数
# =========================
def send_tg_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TG 未配置")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print("TG失败:", e)


def get_ip():
    try:
        return requests.get("https://api.ipify.org", timeout=5).text
    except:
        return "UNKNOWN"


def rotate_ip(old_ip):
    """
    只做“尝试切换”，不保证成功
    """
    print("🔄 尝试切换网络出口...")

    for _ in range(2):
        subprocess.run(["warp-cli", "--accept-tos", "disconnect"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

        subprocess.run(["warp-cli", "--accept-tos", "connect"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        time.sleep(5)

        new_ip = get_ip()
        if new_ip != old_ip and new_ip != "UNKNOWN":
            print(f"✅ IP切换: {old_ip} -> {new_ip}")
            return new_ip

    print("⚠️ IP未变化")
    return get_ip()


def parse_hours(text):
    try:
        return int(text.split(":")[0])
    except:
        return -1


# =========================
# 状态机核心
# =========================
class BotStateMachine:
    def __init__(self):
        self.state = STATE_INIT
        self.fail_count = 0
        self.success_count = 0
        self.last_ip = get_ip()

    # ---------- 页面加载 ----------
    def load_page(self, page):
        self.state = STATE_LOADING

        try:
            page.get(URL)
        except:
            pass

        time.sleep(3)

        html = page.html.lower()

        # Cloudflare拦截识别（仅检测）
        if "just a moment" in html or "checking your browser" in html:
            self.state = STATE_BLOCKED
            return None

        ele = page.ele("#countdown", timeout=8)
        if not ele:
            self.fail_count += 1
            return None

        self.state = STATE_READY
        return ele

    # ---------- 决策 ----------
    def decide(self):
        if self.fail_count >= IP_FAIL_THRESHOLD:
            return "ROTATE_IP"

        if self.state == STATE_BLOCKED:
            return "ROTATE_IP"

        if self.state == STATE_READY:
            return "CLICK"

        return "WAIT"

    # ---------- 执行 ----------
    def execute(self, action, page):
        if action == "WAIT":
            time.sleep(3)

        elif action == "ROTATE_IP":
            self.last_ip = rotate_ip(self.last_ip)
            self.fail_count = 0

        elif action == "CLICK":
            btn = page.ele(".vote-btn", timeout=5)

            if not btn:
                print("⚠️ 没有按钮")
                return

            if not btn.states.is_enabled:
                print("⏳ 按钮冷却")
                time.sleep(COOLDOWN_SECONDS)
                return

            try:
                btn.click(by_js=True)
                print("👉 已点击")
                self.state = STATE_COOLDOWN
            except Exception as e:
                print("点击失败:", e)
                self.state = STATE_ERROR


    # ---------- 成功检测 ----------
    def check_success(self, old_text, new_text):
        if old_text and new_text and old_text != new_text:
            self.success_count += 1
            print("🎉 状态更新成功")
            return True
        return False


# =========================
# 主程序
# =========================
def main():
    co = ChromiumOptions().auto_port()
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--disable-dev-shm-usage")

    page = ChromiumPage(co)
    page.set.timeouts(page_load=15)

    bot = BotStateMachine()

    print(f"初始IP: {bot.last_ip}")

    loop = 0

    while loop < MAX_LOOPS:
        loop += 1
        print(f"\n--- LOOP {loop}/{MAX_LOOPS} ---")

        countdown = bot.load_page(page)

        if not countdown:
            print("⚠️ 页面未就绪")
            bot.execute(bot.decide(), page)
            continue

        text = countdown.text
        hours = parse_hours(text)

        print("⏳ 当前时间:", text)

        if hours >= TARGET_HOURS:
            print("✅ 达到目标")
            break

        old_text = text

        bot.execute(bot.decide(), page)

        time.sleep(5)

        try:
            page.get(URL)
            time.sleep(2)

            new_ele = page.ele("#countdown", timeout=8)
            if new_ele:
                bot.check_success(old_text, new_ele.text)

        except:
            pass

    # ---------- 结束 ----------
    try:
        final = page.ele("#countdown").text
    except:
        final = "UNKNOWN"

    page.quit()

    report = (
        f"🎮 任务结束\n"
        f"----------------\n"
        f"🔄 循环: {loop}\n"
        f"✅ 成功: {bot.success_count}\n"
        f"📊 当前: {final}\n"
    )

    print(report)
    send_tg_message(report)


if __name__ == "__main__":
    main()
