from playwright.sync_api import Playwright, sync_playwright
import sys
import os
import time

def check_url_status(page, url):
    max_attempts = 3
    attempt = 0
    
    try:
        print(f"正在访问: {url}")
        page.goto(url, timeout=60000)
        time.sleep(10)
        
        while attempt < max_attempts:
            # 检查页面内容是否包含sleep关键词
            page_content = page.content().lower()
            
            if "sleep" in page_content:
                attempt += 1
                print(f"🔍 检测到sleep状态 (第{attempt}次尝试)")
                sys.stdout.flush()
                
                try:
                    # 尝试多种方式定位唤醒按钮
                    wakeup_clicked = False
                    
                    # 方法1: 通过按钮文本定位
                    try:
                        page.get_by_text("Yes, get this app back up!").click(timeout=5000)
                        wakeup_clicked = True
                        print("✅ 通过文本定位成功点击唤醒按钮")
                    except:
                        pass
                    
                    # 方法2: 通过test-id定位（备用）
                    if not wakeup_clicked:
                        try:
                            page.get_by_test_id("wakeup-button-viewer").click(timeout=5000)
                            wakeup_clicked = True
                            print("✅ 通过test-id定位成功点击唤醒按钮")
                        except:
                            pass
                    
                    # 方法3: 通过CSS选择器定位（备用）
                    if not wakeup_clicked:
                        try:
                            page.locator("button:has-text('Yes, get this app back up!')").click(timeout=5000)
                            wakeup_clicked = True
                            print("✅ 通过CSS选择器成功点击唤醒按钮")
                        except:
                            pass
                    
                    # 方法4: 通过更宽泛的选择器
                    if not wakeup_clicked:
                        try:
                            page.locator("button").filter(has_text="Yes").click(timeout=5000)
                            wakeup_clicked = True
                            print("✅ 通过宽泛选择器成功点击唤醒按钮")
                        except:
                            pass
                    
                    if wakeup_clicked:
                        print("⏳ 已执行唤醒操作，等待30秒后检查状态...")
                        sys.stdout.flush()
                        
                        # 等待30秒后刷新页面
                        time.sleep(30)
                        page.reload()
                        time.sleep(10)  # 等待页面加载
                        
                    else:
                        print("❌ 检测到sleep状态但未能找到唤醒按钮")
                        sys.stdout.flush()
                        break
                        
                except Exception as e:
                    print(f"❌ 第{attempt}次唤醒操作失败: {str(e)}")
                    sys.stdout.flush()
                    
                # 如果达到最大尝试次数
                if attempt >= max_attempts:
                    print(f"❌ 经过{max_attempts}次尝试仍处于sleep状态，唤醒失败!")
                    sys.stdout.flush()
                    return False
                    
            else:
                # 没有检测到sleep关键词，说明应用正常运行
                if attempt > 0:
                    print("🎉 唤醒成功! Streamlit应用现已正常运行")
                    sys.stdout.flush()
                    return True
                else:
                    print("✅ Streamlit应用正在正常运行")
                    sys.stdout.flush()
                    return True
            
    except Exception as e:
        print(f"❌ 访问 {url} 时出错: {str(e)}")
        sys.stdout.flush()
        return False

def run(playwright: Playwright) -> None:
    browser = None
    context = None
    page = None
    
    try:
        print("🚀 启动Firefox浏览器...")
        browser = playwright.firefox.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()
        
        # 从环境变量获取目标URL
        target_url = os.getenv('TARGET_URL', 'https://sheet-tool-zsjsj.streamlit.app')
        print(f"🎯 目标URL: {target_url}")
        
        success = check_url_status(page, target_url)
        
        if success:
            print("✅ 任务完成：应用状态正常")
        else:
            print("⚠️ 任务完成：但可能存在问题")
    
    except Exception as e:
        print(f"💥 运行出错: {str(e)}")
        sys.stdout.flush()
    finally:
        if page:
            page.close()
        if context:
            context.close()
        if browser:
            browser.close()
        print("🔚 浏览器已关闭")

if __name__ == "__main__":
    print("=" * 50)
    print("🔄 Streamlit 自动唤醒脚本启动")
    print("=" * 50)
    
    with sync_playwright() as playwright:
        run(playwright)
    
    print("=" * 50)
    print("🏁 脚本执行完毕")
    print("=" * 50)
