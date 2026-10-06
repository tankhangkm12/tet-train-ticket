# Vòng lặp cải thiện skill (Continuous Skill Improvement)

**Mục tiêu:** mỗi lần một skill Aizen làm chưa tốt, vấn đề được ghi lại; vấn đề lặp lại hoặc nghiêm trọng được
sửa có kiểm chứng (baseline + eval), không sửa vội theo một trường hợp.

`FB` = `uv run "<aizen-skill-creator>/scripts/authoring/feedback.py"` (`<aizen-skill-creator>` = thư mục skill `aizen-skill-creator` đã cài,
vd. `~/.claude/skills/aizen-skill-creator`). Sổ nằm ở `<repo Aizen-Skills>/.aizen/knowledge/feedback/<skill>.jsonl`.

## Khi nào kích hoạt — chỉ khi có tín hiệu

Trong task có dùng một skill Aizen và xảy ra ít nhất một điều:
- người dùng sửa lại / phàn nàn cách skill làm;
- một bước hoặc script của skill lỗi, hoặc hướng dẫn của skill sai so với thực tế (lệnh, đường dẫn, API);
- phải làm tay việc mà skill lẽ ra lo, hoặc gặp trường hợp skill không phủ.

Không có tín hiệu → không làm gì. Không tự đánh giá sau mọi task.

## Bước A — Ghi nhận (luôn làm, không hỏi, không chen ngang task)

Cuối task, mỗi vấn đề một lệnh, rồi báo người dùng một dòng:

```bash
FB log --skill <id> --kind bug|gap|friction|wrong-doc --text "<vấn đề, 1 câu>" \
  --evidence "<lỗi/lệnh/file>" --prompt "<prompt tái hiện được>"
```

Không tìm thấy repo → bỏ qua và nói một dòng; không bao giờ chặn task chính.

## Bước B — Đề xuất sửa (chỉ khi một trong các điều sau đúng)

- người dùng phàn nàn trực tiếp về skill;
- `FB list --skill <id> --open` cho thấy cùng vấn đề `x2` trở lên;
- lỗi làm skill cho ra kết quả sai (không chỉ chậm/vụng).

Đề xuất ≤ 15 dòng: skill, các entry `#id`, file sẽ sửa, diff dự kiến, cách kiểm. Chờ người dùng nói "ok".

## Bước C — Sửa (sau khi được duyệt)

Theo "Workflow — improve an existing skill" của `aizen-skill-creator`: baseline → sửa → bump `manifest.json` → thêm
eval case từ `--prompt` đã ghi → eval với vs không → `npm test` → `node bin/cli.js sync` → commit đúng file đã sửa
→ `FB resolve --skill <id> --id <n> --commit <sha>`. Không `git push` trừ khi người dùng cho phép lần push đó.
