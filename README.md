# Proxy Scraper and Validator

这是一个用于爬取、测试和验证代理IP的Python工具。它从指定的网站爬取免费代理IP，测试其可达性（ping），并验证其可用性，最终输出有效的代理列表。

## 功能
1. **代理爬取**：从 `https://www.kuaidaili.com/free/inha/` 爬取免费代理IP。
2. **Ping测试**：使用多线程对爬取到的IP进行ping测试，筛选出可达的代理。
3. **代理验证**：通过HTTP请求验证代理的有效性，确保返回的IP与代理IP一致。

## 依赖
- Python 3.7+
- 所需Python库：
  - `playwright`
  - `beautifulsoup4`
  - `requests`

## 安装
1. 克隆或下载本项目：
   ```bash
   git clone <repository-url>
   cd proxy-scraper
2. 安装依赖：
pip install playwright beautifulsoup4 requests
3. 安装Playwright浏览器：
playwright install
运行脚本：
python proxy_scraper.py
脚本将依次执行以下步骤：
爬取代理并保存到 proxies.txt
测试IP可达性并保存到 ok_ping_ip.txt
验证代理有效性并保存到 ok_daili.txt

输出文件
proxies.txt：爬取到的原始代理列表（格式：IP:PORT）
ok_ping_ip.txt：通过ping测试的IP列表（格式：IP:PORT）
ok_daili.txt：最终验证有效的代理列表（格式：IP:PORT）

##注意事项
反爬限制：
脚本包含随机延迟和User-Agent伪装以减少被封禁的可能性，但仍可能因网站策略变化而失败。
如果遇到“验证码”或“访问受限”，请暂停使用或调整爬取频率。
系统兼容性：
Ping测试使用Windows的 ping 命令（-n 和 -w 参数）。Linux/Mac用户需修改为 ping -c 2 -W 1。
网络环境：
代理验证依赖网络连接，建议在稳定的网络环境下运行。
线程数：
默认使用50个线程进行ping和验证，可根据系统性能调整 max_workers 参数。

##自定义修改
爬取页数：修改 main() 函数中的 pages = 5。
目标网站：修改 base_url 为其他代理网站（需调整解析逻辑）。
测试URL：修改 test_proxy() 中的 http://ipinfo.io/ip 为其他测试地址。


本项目仅用于学习和研究目的，请遵守目标网站的使用条款。


