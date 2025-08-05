# README

打 puzzle hunt 用到的一些工具，更新中……

大部分代码以及解释性文字由 AI 完成，因此可能会出现逻辑不通、效率低下、命名混乱等一系列问题。

目前支持：

- 对角线提取：给定带缺的 feeder 和 index（支持 shuffle feeder 和 index 的顺序），提取所有可能的单词；
- 单词查询：单纯的通配符匹配、按照编辑距离查询、按照给定串作为子串查询；
- 汉字查询：根据笔画数、声母、韵母、声调、偏旁、“第x笔是xxx”等信息查询，结果按照释义长度降序排序。

TODO：

- 对角线提取效率优化；
- 汉字查询中加入字义排序；
- 词语、成语查询；
- 常用提取工具。

## References

本仓库参考了以下仓库，并使用了仓库内的数据：

- [chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua)
- [cnchar](https://github.com/theajack/cnchar)
- [cipher_machine](https://github.com/philippica/cipher_machine)

本仓库仅供个人使用，无任何商业目的，若造成侵权请联系我删除！