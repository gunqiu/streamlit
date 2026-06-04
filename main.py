import os
import time
import subprocess
import requests
from DrissionPage import ChromiumPage, ChromiumOptions

# --- 配置区 ---
URL = "https://g4f.gg/fgmfurni"
TARGET_HOURS = 72
MAX_LOOPS = 20

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_tg_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("TG 环境变量未配置，跳过发送消息。")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"TG 消息发送失败: {e}")

def get_current_ip():
    try:
        return requests.get('https://api.ipify.org', timeout=5).text
    except:
        return "获取失败"

def rotate_warp_ip(old_ip):
    max_retries = 3
    for i in range(max_retries):
        subprocess.run(['warp-cli', '--accept-tos', 'disconnect'], stdout=subprocess.DEVNULL)
        time.sleep(2)
        subprocess.run(['warp-cli', '--accept-tos', 'connect'], stdout=subprocess.DEVNULL)

        time.sleep(8) 
        new_ip = get_current_ip()

        if new_ip == "获取失败" or new_ip == old_ip:
            continue

        print(f"更换 IP 成功: {new_ip}")
        return new_ip

    return get_current_ip()

def get_current_hours(time_text):
    if not time_text:
        return -1
    try:
        parts = time_text.split(':')
        if len(parts) >= 1:
            return int(parts[0])
    except:
        pass
    return -1

# --- 【修改点 1】: 优化 Turnstile 处理逻辑 ---
# 不再尝试复杂的 Shadow DOM 操作，而是通过等待和自动通过机制
def handle_challenge(page):
    print("🛡️ 检测并处理安全挑战...")
    
    # 检查是否出现 Cloudflare 的典型特征
    if "Just a moment..." in page.title or "Checking if the site connection is secure" in page.html:
        print("⚠️ 检测到 Cloudflare 防护，正在等待自动通过...")
        
        # 等待最多 15 秒，看页面是否自动跳转或加载完成
        for _ in range(15):
            time.sleep(2)
            # 如果标题改变或出现目标元素，说明通过了
            if "Just a moment..." not in page.title and page.ele('#countdown', timeout=1):
                print("✅ 验证通过，页面已就绪")
                return True
                
        print("❌ 验证未在预期时间内通过")
        return False
    
    # 检查 Turnstile iframe
    try:
        iframe = page.get_frame('css:iframe[src^="https://challenges.cloudflare.com"]', timeout=3)
        if iframe:
            print("⚠️ 检测到 Turnstile 验证框，尝试自动通过...")
            # 正常情况下，开启 uc 模式后，这个验证框会自动消失或通过
            # 这里只需等待
            time.sleep(5)
            # 刷新页面看是否通过
            page.refresh()
            time.sleep(3)
            return True
    except:
        pass
    
    return False

def main():
    # --- 【修改点 2】: 增强浏览器配置 ---
    co = ChromiumOptions().auto_port()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-blink-features=AutomationControlled') # 隐藏自动化特征
    co.set_argument('--disable-web-security') # 禁用 web 安全限制 (有助于绕过某些检测)
    co.set_argument('--disable-features=IsolateOrigins,site-per-process') # 防止某些隔离策略干扰
    co.set_argument('--disable-component-update') # 防止组件更新干扰
    co.set_argument('--disable-background-networking') # 减少后台网络活动
    
    # 【关键修改】: 启用无头模式并伪装为真实用户
    # DrissionPage 的 ChromiumOptions 也支持类似 uc 的配置，或者你可以直接使用 undetected_chromedriver
    # 这里通过参数尽量模拟真实环境
    co.set_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.6')
    
    page = ChromiumPage(co)
    page.set.timeouts(page_load=20) # 增加超时时间

    loop_count = 0
    success_count = 0
    current_ip = get_current_ip()
    print(f"初始运行 IP: {current_ip}")

    while loop_count < MAX_LOOPS:
        loop_count += 1
        print(f"\n--- 第 {loop_count}/{MAX_LOOPS} 次循环 ---")

        try:
            # 在每次请求前确保页面是干净的
            page.get(URL)
        except Exception as e:
            print(f"页面加载异常: {e}")
        
        # --- 【修改点 3】: 增加挑战处理 ---
        if "Just a moment..." in page.title or "Checking if the site connection is secure" in page.html:
            handle_challenge(page)
            # 处理完挑战后，重新加载目标页面
            try:
                page.get(URL)
            except:
                pass

        countdown_ele = page.ele('#countdown', timeout=10)

        if not countdown_ele:
            print("⚠️ 页面数据未加载或被拦截，尝试更换 IP...")
            current_ip = rotate_warp_ip(current_ip)
            continue

        current_time_text = countdown_ele.text
        current_hours = get_current_hours(current_time_text)
        print(f"当前剩余时间: {current_time_text}")

        if current_hours >= TARGET_HOURS:
            print(f"✅ 已达到目标 ({TARGET_HOURS}h)，准备退出。")
            break

        btn = page.ele('.vote-btn')
        if not btn or not btn.states.is_enabled:
            print("⏳ 按钮冷却或 IP 受限，尝试更换 IP...")
            current_ip = rotate_warp_ip(current_ip)
            continue

        try:
            btn.click(by_js=True)
            print("👉 已发送点击指令...")

            # 点击后等待页面响应
            time.sleep(3)

            # 检查是否出现新的挑战
            if "Just a moment..." in page.title:
                print("🔄 检测到点击后出现验证，正在处理...")
                handle_challenge(page)
            
            # --- 【修改点 4】: 强制刷新页面获取最新数据 ---
            # 不要依赖之前的元素，强制刷新页面以获取最新状态
            try:
                page.refresh()
            except:
                page.get(URL)
            
            time.sleep(3) # 等待刷新后加载

            new_countdown_ele = page.ele('#countdown', timeout=10)
            if new_countdown_ele:
                new_time_text = new_countdown_ele.text
                if current_time_text != new_time_text:
                    print(f"🎉 续期成功！时间更新为 {new_time_text}")
                    success_count += 1
                    # 成功后换 IP
                    current_ip = rotate_warp_ip(current_ip) 
                else:
                    print("⚠️ 时间未改变，可能被限制，更换 IP 重试...")
                    current_ip = rotate_warp_ip(current_ip)
            else:
                print("❌ 无法获取刷新后数据，更换 IP...")
                current_ip = rotate_warp_ip(current_ip)

        except Exception as e:
            print(f"❌ 点击执行异常: {e}")
            current_ip = rotate_warp_ip(current_ip)

    final_time = "获取失败"
    expiry_info = "获取失败"
    try:
        final_time = page.ele('#countdown').text
        expiry_info = page.ele('.countdown-sub').text
    except:
        pass

    page.quit()

    report_msg = (
        f"🎮 <b>G4F-US 服务器续期任务报告</b>\n"
        f"--------------------------\n"
        f"🔄 循环尝试: {loop_count} / {MAX_LOOPS}\n"
        f"✅ 成功续期: {success_count} 次\n"
        f"⏳ 当前时长: <code>{final_time}</code>\n"
        f"📅 到期信息: {expiry_info}\n"
    )
    send_tg_message(report_msg)
    print("任务执行完毕。")

if __name__ == '__main__':
    main()
