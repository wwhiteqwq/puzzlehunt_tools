# README

打 puzzle hunt 用到的一些工具，更新中……

大部分代码以及解释性文字由 AI 完成，因此可能会出现逻辑不通、效率低下、命名混乱等一系列问题。

如何使用？如果本地没有 cache/ 文件夹就先运行 `vocabulary_preprocessor.py`，然后直接运行 `start_app.py` 就行！

（注意，如果要用词意查询功能，请自行用下一个 Qwen3-Embedding-0.6B 的 docker，然后跑 `docker run --gpus all -p 8080:80 ghcr.io/huggingface/text-embeddings-inference:1.8 --model-id Qwen/Qwen3-Embedding-0.6B` 启动它。）

目前支持：

- 对角线提取：给定带缺的 feeder 和 index（支持 shuffle feeder 和 index 的顺序），提取所有可能的单词；
- 单词查询：单纯的通配符匹配、按照编辑距离查询、按照给定串作为子串查询；
- 近义词查询：使用了 [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) 模型来计算词的 embedding，然后做 knn 查询。除了词意限制，同样也加上了字数限制和每一个字的限制。
- 和同开弥 solver：支持手动加入限制，限制可以明确位置，也可以作通配，最后输出会按照符合限制条数降序输出；
- 汉字查询：根据笔画数、声母、韵母、声调、偏旁、“第x笔是xxx”等信息查询，结果按照释义长度降序排序。

TODO：

- 对角线提取效率优化；
- 成语查询；
- `ue/ve` 可能区分上有点问题；
- 常用提取工具。

## References

本仓库参考了以下仓库，并使用了仓库内的数据：

- [chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua)
- [cnchar](https://github.com/theajack/cnchar)
- [cipher_machine](https://github.com/philippica/cipher_machine)

本仓库仅供个人使用，无任何商业目的，若造成侵权请联系我删除！