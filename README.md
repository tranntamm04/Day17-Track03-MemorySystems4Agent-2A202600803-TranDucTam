# Chào mừng các bạn đến với Giai đoạn 2, Track 3, Day 17: Memory Systems for AI Agent

Trong Day 17 này, các bạn sẽ tập trung vào một câu hỏi rất thực tế: làm sao để AI agent **không chỉ trả lời tốt trong một lượt chat**, mà còn **nhớ đúng thông tin quan trọng qua nhiều phiên làm việc** mà vẫn kiểm soát được chi phí token.

Trong bài lab này, các bạn sẽ xây dựng và so sánh hai agent:

- `Baseline Agent`: chỉ có short-term memory trong cùng một thread
- `Advanced Agent`: có short-term memory, `User.md` bền vững, và compact memory để nén hội thoại dài

Mục tiêu cuối cùng không phải chỉ là “agent nhớ nhiều hơn”, mà là hiểu rõ trade-off giữa:

- độ nhớ dài hạn
- chất lượng phản hồi
- chi phí token
- độ phức tạp của hệ thống memory

## Các bạn sẽ làm gì trong track này?

Sau khi hoàn thành, các bạn cần có khả năng:

- phân biệt `short-term memory`, `persistent memory`, và `compact memory`
- xây dựng agent baseline và advanced trên cùng một benchmark
- lưu hồ sơ người dùng bằng `User.md`
- kích hoạt compact memory khi hội thoại dài vượt ngưỡng
- benchmark hai agent bằng cùng một bộ dữ liệu tiếng Việt
- đọc kết quả benchmark theo các chỉ số recall, token, memory growth, chất lượng phản hồi

## Cấu trúc codebase

Repo này được chia thành ba phần rõ ràng:

- `src/`: bản scaffold dành cho sinh viên, chứa pseudocode và TODO để hoàn thiện
- `data/`: dữ liệu benchmark ở root để dùng cho cả benchmark chuẩn và stress benchmark

## Provider hỗ trợ

Trong bản solved lab, runtime hỗ trợ các provider sau:

- `openai`
- `custom` (OpenAI-compatible base URL)
- `gemini`
- `anthropic`
- `ollama`
- `openrouter`

Điều này quan trọng vì memory system không nên bị khóa vào một provider duy nhất.

## Chỉ số benchmark cần hiểu

Khi hoàn thiện bài, benchmark nên cho các cột sau:

- `Agent tokens only`: token sinh ra trực tiếp trong hội thoại của agent
- `Prompt tokens processed`: lượng ngữ cảnh agent phải kéo theo qua các lượt
- `Cross-session recall`: khả năng nhớ facts qua thread hoặc session mới
- `Response quality`: chất lượng phản hồi
- `Memory growth (bytes)`: tốc độ phình của file memory
- `Compactions`: số lần compact memory đã nén lịch sử cũ

Điểm quan trọng nhất của track này là:

- ở hội thoại ngắn, `Advanced` có thể tốn hơn `Baseline` về token usage
- ở hội thoại rất dài, compact memory nên giúp `Advanced` xử lý ngữ cảnh hiệu quả hơn đáng kể + tiết kiệm usage.

## Cách dùng repo này

## Setup môi trường

Các bạn cần chuẩn bị môi trường Python `>= 3.11` và cài các package cần thiết cho LangChain, LangGraph, provider SDK, `python-dotenv`, `tabulate`, và `pytest`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install langchain langgraph langchain-openai langchain-google-genai langchain-anthropic langchain-ollama langchain-openrouter python-dotenv tabulate pytest
```

Sau đó làm việc trực tiếp với `src/` và `data/` ở root repo.

Nếu các bạn là sinh viên:

- làm bài trong `src/`
- dùng `data/` làm benchmark input

Nếu các bạn là giảng viên hoặc reviewer:

- dùng `src/` để đánh giá scaffold giao cho sinh viên và kết quả hoàn thiện cuối cùng

## Tài liệu nên đọc tiếp

- `Guide.md`: hướng dẫn từng bước để hoàn thành lab
- `Rubric.md`: tiêu chí chấm điểm và bonus

Track này được thiết kế để các bạn không chỉ “dùng agent”, mà còn bắt đầu nghĩ như một người thiết kế **memory system** cho agent production.

## Trang thai bai lam

Phien ban hien tai hoan thien lab theo huong offline-first. Khong can API key de chay test, benchmark, demo memory, hay nop bai.

### Chay test

Tren Windows PowerShell:

```powershell
$base = ".tmp\pytest-$([guid]::NewGuid().ToString('N'))"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp $base
```

Ket qua ky vong:

```text
10 passed
```

### Chay benchmark

```powershell
.\.venv\Scripts\python.exe src\benchmark.py
```

Benchmark in hai bang: Standard Benchmark va Long-Context Stress Benchmark. Moi bang co du cac cot rubric yeu cau: `Agent tokens only`, `Prompt tokens processed`, `Cross-session recall`, `Response quality`, `Memory growth (bytes)`, `Compactions`.

### Xem demo memory profile

```powershell
.\.venv\Scripts\python.exe src\demo_memory_profile.py
```

Demo nay in ra `User.md` mau, gom stable facts co metadata, conflict history, decay report, va cross-session recall tren thread moi.

## API key

Khong can API key cho offline mode. API key chi can khi muon thu live model qua provider that.

Vi du cau hinh DeepSeek trong `.env`:

```env
LLM_PROVIDER=custom
LLM_MODEL=deepseek-v4-flash
CUSTOM_BASE_URL=https://api.deepseek.com
CUSTOM_API_KEY=your_key_here
```

## Bonus 90-100 da lam

- Confidence threshold: chi ghi fact khi confidence du cao.
- Structured entity extraction: tach facts thanh `Name`, `Location`, `Profession`, `Response style`, `Favorite drink`, `Favorite food`, `Pet`, `Interests`.
- Conflict handling: fact moi thay the fact cu va ghi vao `Conflict history`.
- Memory decay: co `decayed_confidence()` va `decay_report()` de giam uu tien fact cu theo thoi gian.
- Noise guardrail: cau hoi, cau mo ho, hoac cau dua khong overwrite stable facts.
- Bonus tests: `src/test_agents.py` co test rieng cho threshold, correction, metadata/decay, noise, repeated mentions.
