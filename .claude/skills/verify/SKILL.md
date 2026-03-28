---
name: verify
description: 检查代码质量并运行完整流水线验证输出。用于提交前或修改后的完整验证。
---

执行完整的验证流程：

1. 运行 `ruff check .` 检查代码质量
2. 运行 `ruff format --check .` 检查格式
3. 运行 `python generate_data.py` 生成数据
4. 运行 `python build_map.py` 生成地图

如果任何步骤失败，停下来修复问题后重试。全部通过后告知用户。
