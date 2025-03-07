# -*- encoding:utf-8 -*-
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import random
import os
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import re
import subprocess
import requests

# 文件路径
PROXIES_FILE = './proxies.txt'
PING_OK_FILE = './ok_ping_ip.txt'
VALID_PROXY_FILE = './ok_daili.txt'

# 创建队列
ip_queue = Queue()
port_queue = Queue()

# 第一部分：爬取代理IP
def get_webpage_content(url, timeout=30000):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()
            time.sleep(random.uniform(1, 3))
            response = page.goto(url, timeout=timeout, wait_until='networkidle')
            
            if response.status != 200:
                raise Exception(f"HTTP状态码异常: {response.status}")
                
            content = page.content()
            if any(keyword in content.lower() for keyword in ["验证码", "访问受限", "access denied"]):
                raise Exception("可能被反爬机制拦截")
                
            browser.close()
            print(f"成功获取 {url} 的内容")
            return content
    except Exception as e:
        print(f"获取 {url} 失败: {str(e)}")
        return None

def extract_ip_port(html_content):
    if not html_content:
        print("HTML内容为空，无法解析")
        return []
        
    proxies = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        table = (soup.find('table', id='list') or
                soup.find('table', {'class': 'table'}) or
                soup.find('table'))
                
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    if ip.count('.') == 3 and port.isdigit():
                        proxies.append({'ip': ip, 'port': port})
        else:
            for tr in soup.select('tr'):
                tds = tr.find_all('td')
                if len(tds) >= 2:
                    ip = tds[0].text.strip()
                    port = tds[1].text.strip()
                    if ip.count('.') == 3 and port.isdigit():
                        proxies.append({'ip': ip, 'port': port})
                        
        print(f"提取到 {len(proxies)} 个代理")
        return proxies
    except Exception as e:
        print(f"解析 HTML 失败: {str(e)}")
        return []

def save_proxies_to_file(proxies, filename=PROXIES_FILE):
    if not proxies:
        print("没有代理可保存")
        return
        
    with open(filename, 'w', encoding='utf-8') as f:
        for proxy in proxies:
            f.write(f"{proxy['ip']}:{proxy['port']}\n")
    print(f"已保存 {len(proxies)} 个代理到 {filename}")

# 第二部分：测试IP可达性
def extract_ip_port_to_queue():
    try:
        with open(PROXIES_FILE, 'r', encoding='utf-8') as fp:
            ip_port_list = fp.read().splitlines()
            
        for line in ip_port_list:
            line = line.strip()
            ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', line)
            port_match = re.search(r':(\d{2,5})', line)
            
            if ip_match and port_match:
                ip = ip_match.group()
                port = port_match.group(1)
                ip_queue.put(ip)
                port_queue.put(port)
                print(f"提取到: {ip}:{port}")
    except Exception as e:
        print(f"读取文件失败: {e}")

def ping_ip(ip, port):
    try:
        result = subprocess.run(
            ['ping', '-n', '2', '-w', '1000', ip],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and "TTL=" in result.stdout:
            return f"{ip}:{port}"
        return None
    except subprocess.TimeoutExpired:
        print(f"{ip}:{port} 超时")
        return None
    except Exception as e:
        print(f"测试 {ip}:{port} 失败: {e}")
        return None

def test_and_save_ping():
    results = []
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = []
        while not ip_queue.empty():
            ip = ip_queue.get()
            port = port_queue.get()
            future = pool.submit(ping_ip, ip, port)
            futures.append(future)
            
        for future in futures:
            result = future.result()
            if result:
                results.append(result)
                print(f"{result} >>> 可达")
                
    if results:
        with open(PING_OK_FILE, 'w', encoding='utf-8') as wp:
            for ip_port in results:
                wp.write(ip_port + '\n')
        print(f"已保存 {len(results)} 个可用的IP到 {PING_OK_FILE}")
    else:
        print("没有找到可用的IP")

# 第三部分：验证代理有效性
def test_proxy(ip, port):
    proxy = f"{ip}:{port}"
    proxies = {
        'http': f'http://{proxy}',
        'https': f'https://{proxy}'
    }
    
    try:
        response = requests.get(
            'http://ipinfo.io/ip',
            proxies=proxies,
            timeout=5,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        if response.status_code == 200:
            returned_ip = response.text.strip()
            if returned_ip == ip:
                print(f"[✓] {proxy} => 有效 (返回IP: {returned_ip})")
                return proxy
        return None
    except requests.RequestException as e:
        print(f"[✗] {proxy} => 不可用 ({str(e)})")
    return None

def load_and_test_proxies():
    results = []
    try:
        with open(PING_OK_FILE, 'r', encoding='utf-8') as wp:
            ip_port_list = [line.strip() for line in wp.readlines() if line.strip()]
            
        if not ip_port_list:
            print("输入文件为空")
            return results
            
        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = []
            for line in ip_port_list:
                if ':' in line:
                    ip, port = line.split(':', 1)
                    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) and port.isdigit():
                        future = pool.submit(test_proxy, ip, port)
                        futures.append(future)
                        
            for future in futures:
                result = future.result()
                if result:
                    results.append(result)
    except Exception as e:
        print(f"读取文件失败: {e}")
    return results

def save_valid_proxies(proxies):
    if not proxies:
        print("没有找到有效的代理")
        return
        
    try:
        with open(VALID_PROXY_FILE, 'w', encoding='utf-8') as fp:
            for proxy in proxies:
                fp.write(proxy + '\n')
        print(f"已保存 {len(proxies)} 个有效代理到 {VALID_PROXY_FILE}")
    except Exception as e:
        print(f"保存文件失败: {e}")

def main():
    # 第一步：爬取代理
    print("开始爬取代理IP...")
    base_url = "https://www.kuaidaili.com/free/inha/{page}"
    pages = 5
    all_proxies = []
    
    for page in range(1, pages + 1):
        url = base_url.format(page=page)
        html_content = get_webpage_content(url)
        if html_content:
            proxies = extract_ip_port(html_content)
            all_proxies.extend(proxies)
        time.sleep(random.uniform(2, 5))
        
    save_proxies_to_file(all_proxies)
    
    # 第二步：测试ping
    print("\n开始测试IP可达性...")
    extract_ip_port_to_queue()
    if ip_queue.empty():
        print("没有找到有效的IP和端口")
        return
    test_and_save_ping()
    
    # 第三步：验证代理
    print("\n开始测试代理可用性...")
    valid_proxies = load_and_test_proxies()
    save_valid_proxies(valid_proxies)
    
    print("\n所有任务完成")

if __name__ == "__main__":
    main()
