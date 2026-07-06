# 书籍管理设计

## 核心模型

**书（Book）是由用户定义的容器。** 系统不自动推断哪些文件属于同一本书，也不根据文件名或内容判断书籍边界——这个决定完全交给用户。

当前定义/管理书籍的入口是 `scripts/ingest.py`（`--book-id` 指定书、`--file`/`--dir` 加文件）；面向终端用户的图形前端是独立的后续子项目，本文档只描述与存储无关的书籍管理语义，不预设交互形态。

## book_id

- 创建书籍时由用户命名，作为 `book_id`
- 一旦确定不可更改：**`book_id` 直接用作 ChromaDB 的 collection 名**，一本书的所有 chunk 存在这个以 `book_id` 命名的独立 collection 里（每本书一个物理独立 collection，天然隔离；`book_id` 同时冗余写入每条 chunk 的 metadata 便于溯源）
- 命名规则：用户自定义，系统侧不做格式限定，但建议简短无空格（如 `ostep`、`civil-law-2024`）

## 添加文件

- 归入同一 `book_id` 的所有文件，均视为这本书的内容
- 支持 PDF、EPUB、音频（MP3/WAV/FLAC）、图片（PNG/JPG/SVG）等所有解析层支持的格式，混合添加没有限制
- 文件只能追加，不支持单独删除某个文件

## 删除

整本书删除（`client.delete_collection(book_id)`）当前 `ChromaStore` 尚未实现，以下为设计约定，落地时按 collection-per-book 模型执行：

- **最小删除单位是整本书**：删除一本书 = 丢弃该 `book_id` 对应的整个 collection（`client.delete_collection(book_id)`）
- 如果用户上传了错误的文件，只能删整本书后重新上传全部文件
- **文件级别删除在技术上可行**（在该 `book_id` 的 collection 内按 `source_file` 过滤删除对应 chunk，不影响同一本书里的其他文件）——底层能力已经实现为 `ChromaStore.delete_by_source(book_id, source_file)`，目前只被 `scripts/ingest.py` 内部用于失败回滚（见 issue #6 设计）；接入到"用户主动删除某个文件"这个产品功能仍预留为未来工作，还需要同步清理 manifest 里对应的 sha 记录、大概率还需要用户确认

## 检索边界

检索永远锚定单一 `book_id`：查询直接打对应的 collection（`collection(book_id).query(...)`），不跨书。"跨整个书库全局检索"不在当前设计内——collection-per-book 模型下如需该能力，要循环各 collection 分别查询再合并，属未来若明确需要再评估的方向。

## 关于"书"与"章节"的边界

系统不做自动区分。用户可以把一本书的多个 PDF 章节文件都添加进同一个 `book_id` 容器，也可以把每章单独建一个 book——这是用户的选择，系统侧透明处理。
