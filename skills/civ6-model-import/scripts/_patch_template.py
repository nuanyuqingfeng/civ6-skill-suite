#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""治标补丁模板：默认关闭、显式开关、自报改动量、写清退出条件。

复制本文件改名为 <你的补丁名>.py，然后：
  1. 填 PURPOSE / BYPASSES / EXIT_WHEN 三个常量（缺一不许合入）；
  2. 在 apply() 里实现**单一**动作（单因单补丁，混装要拆）；
  3. 调用方必须显式传 enable=True 或设置环境变量才生效。

口径见 references/patch-lifecycle.md。
"""

# ---- 合入前必须回答的三件事（准入四问的第 1/2/4 问）----------------------
PURPOSE = "一句话：它修的具体现象是什么（含可复现的判据）"
BYPASSES = "它绕过了哪一层？那一层会不会本来就是错的"
EXIT_WHEN = "什么现象消失后本文件必须删除（写可观测的判据）"

# ---- 开关：默认关闭 ------------------------------------------------------
import os

ENV_FLAG = "PATCH_%s" % "TEMPLATE"   # 改成本补丁的大写名


def enabled(explicit=False):
    """显式参数优先；否则看环境变量（1/true/yes 为开）。"""
    if explicit:
        return True
    return os.environ.get(ENV_FLAG, "").strip().lower() in ("1", "true", "yes", "on")


# ---- 主体 ---------------------------------------------------------------
def apply(target, enable=False, **kwargs):
    """对 target 执行单一修正；返回改动计数。

    target 的具体类型由调用方决定（mesh / 文本 / 字典…）。
    未启用时**不做任何事**，并打印 SKIP，便于在日志里确认它没有被静默执行。
    """
    name = "TEMPLATE"
    if not enabled(enable):
        print("PATCH_SKIP %s" % name)
        return 0

    changed = 0

    # ---- 在这里实现修正 ----
    # 例：
    # for item in target:
    #     if needs_fix(item):
    #         fix(item); changed += 1

    # ---- 必须自报改动量：0 与"未执行"要能区分开 ----
    print("PATCH_APPLIED %s changed=%d" % (name, changed))
    if changed == 0:
        # 改动 0 通常意味着"病灶已经不在了"，提示这时应该考虑删除本补丁
        print("PATCH_NOOP %s 本次没有改动，检查是否已可移除（EXIT_WHEN: %s）"
              % (name, EXIT_WHEN))
    return changed


if __name__ == "__main__":
    # 手工验证入口：默认不生效，必须显式 --enable
    import sys
    dummy = []
    apply(dummy, enable="--enable" in sys.argv)
