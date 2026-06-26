# Raw Source PDFs

这个目录存放解析器选型实测的原始书籍 PDF，因文件过大（最大 146 MB）不进 git。

## 下载清单

### CS（放入 `cs/`）

| 文件名 | 来源 | 下载方式 |
|---|---|---|
| `cpu-intro.pdf` | OSTEP Chapter 4 | https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-intro.pdf |
| `cpu-sched.pdf` | OSTEP Chapter 7 | https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-sched.pdf |
| `threads-intro.pdf` | OSTEP Chapter 26 | https://pages.cs.wisc.edu/~remzi/OSTEP/threads-intro.pdf |
| `vm-paging.pdf` | OSTEP Chapter 18 | https://pages.cs.wisc.edu/~remzi/OSTEP/vm-paging.pdf |

### 临床医学（放入 `clinical/`）

| 文件名 | 来源 | 下载方式 |
|---|---|---|
| `Bookshelf_NBK595000.pdf` | Nursing Pharmacology 2e（NCBI Bookshelf，CC-BY 4.0） | 打开 https://www.ncbi.nlm.nih.gov/books/NBK595000/ → 右上角"PDF"下载全书 |

### 法学（放入 `law/`）

| 文件名 | 来源 | 下载方式 |
|---|---|---|
| `Criminal-Procedure-July2022_0.pdf` | Criminal Procedure（CALI eLangdell，CC-BY-NC-SA） | https://www.cali.org/books/criminal-procedure-trachtenberg-alexander → Download PDF |

## 下载后验证

```bash
# 检查文件是否存在且非空
ls -lh cs/ clinical/ law/
```

预期大小：CS 各章节约 100–130 KB，临床约 146 MB，法学约 7 MB。
