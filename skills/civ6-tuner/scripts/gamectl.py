#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gamectl.py —— 文明6 对局生命周期控制（全部原语 2026-10-02/03 实机验证）。

子命令：
    wait [--timeout N] [--want ingame|inmenu|any]   轮询 4318 直至满足
    save <档名>                                      表参数存档 + 磁盘核对
    load <档名>                                      对局内 LeaveGame+LoadGame，主菜单直接 LoadGame
                                                     → 确认链推进 → 等待重建（主菜单也可用）
    restart                                          Network.RestartGame → 同上确认链
    exit-menu                                        Events.ExitToMainMenu → 等主菜单
    kill / launch                                    按 PID 逐个 taskkill / Popen 直启可执行文件
    host-game [--leader X] [--civ X]                 主菜单无头建局（可选指定领袖/文明）→ 确认链
    end-turn [--force] [--timeout N]                 结束回合并轮询推进；--force 推过被阻塞的回合

退出码：0 成功；1 失败/超时。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import winreg
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_input as GI  # noqa: E402
import tuner_exec as T   # noqa: E402
import tuner_link as TL  # noqa: E402

GAME_BINARIES = Path("Base") / "Binaries" / "Win64Steam" / "CivilizationVI.exe"
GAME_SUBDIR = Path("steamapps") / "common" / "Sid Meier's Civilization VI"
SAVES_TAIL = Path("My Games") / "Sid Meier's Civilization VI" / "Saves" / "Single"
STEAM_ROOTS = (r"F:\Steam", r"C:\Program Files (x86)\Steam", r"D:\Steam")


def steam_library_roots() -> list[str]:
    """从 libraryfolders.vdf 收集全部 Steam 库根；清单缺失即跳过。"""
    roots: list[str] = []
    for steam in STEAM_ROOTS:
        vdf = Path(steam) / "steamapps" / "libraryfolders.vdf"
        if not vdf.is_file():
            continue
        txt = vdf.read_text(encoding="utf-8", errors="replace")
        roots += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', txt)]
    return roots


def resolve_exe() -> Path:
    """定位 CivilizationVI.exe：Steam 库清单优先，随后已知安装根与显式覆盖。"""
    env = os.environ.get("RGN_CIV6_EXE")
    cands = [Path(env)] if env else []
    for root in list(steam_library_roots()) + list(STEAM_ROOTS):
        cands.append(Path(root) / GAME_SUBDIR / GAME_BINARIES)
    for cand in cands:
        if cand.is_file():
            return cand
    raise Fail("找不到 CivilizationVI.exe，请用 launch --exe 显式指定安装路径")


def _documents_dir() -> Path | None:
    """注册表记录的「文档」实际位置；读不到返回 None。"""
    try:
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            return Path(winreg.QueryValueEx(key, "Personal")[0])
    except OSError:
        return None


def _home_dir() -> Path | None:
    """用户主目录；环境变量缺失时返回 None（不抛异常）。"""
    for var in ("USERPROFILE", "HOME"):
        val = os.environ.get(var)
        if val:
            return Path(val)
    try:
        return Path.home()
    except (RuntimeError, OSError):
        return None


def resolve_saves_dir() -> Path:
    """定位单人存档目录：注册表「文档」优先，随后本机已知位置。

    候选逐个求值，缺失的候选返回 None 即跳过；环境变量不全时模块照常导入。
    """
    base = _documents_dir()
    home = _home_dir()
    cands = [base, Path(r"D:\documents"), home / "Documents" if home else None]
    for cand in cands:
        if cand and (cand / SAVES_TAIL).is_dir():
            return cand / SAVES_TAIL
    return (base or (home / "Documents" if home else Path(r"D:\documents"))) / SAVES_TAIL


SAVES_DIR = resolve_saves_dir()


class Fail(Exception):
    pass


_HOST, _PORT = T.DEFAULT_HOST, T.DEFAULT_PORT

# 就绪轮询的探测预算：建连 0.6s、LSQ 1.5s。读档期间 4318 反复拒绝连接，
# 沿用握手默认的 5s+8s+8s 会把单轮代价拉到 20s 以上，按键节拍随之失控。
PROBE_CONNECT = 0.6
PROBE_LSQ = 1.5
POLL_GAP = 0.4

# 推进节拍：两次推进之间的最短间隔。读档界面只需一次确认，连发会把
# 游戏内暂停菜单打出来，因此间隔取到 2 秒以上。
ADVANCE_INTERVAL = 2.0

# 同一相位停滞多久才允许再投一次。相位一旦变化就重置这个计时：
# 连续在同一个相位上投递等于无效果确认地连发，实测会打乱读档流程。
STALL_INTERVAL = 8.0

# 状态表为空的宽限期与投递上限。端口可连但状态表为空表示 Lua VM 已经拆掉、
# 新的还没建好，这段时间按键没有落点：宽限期内只探测，之后才兜底投递，
# 且总次数受限，避免在重建期连发打乱读档流程。
BLANK_GRACE = 12.0
BLANK_MAX_ATTEMPTS = 3

# 完成判定要求的连续 ingame 采样次数。
CONFIRM_SAMPLES = 2


# ---------------------------------------------------------------------------
# 连接与执行
# ---------------------------------------------------------------------------
class Session:
    """一次连接 + 握手；exec() 复用同一连接。"""

    def __init__(self, host=None, port=None):
        self.host, self.port = host or _HOST, port or _PORT
        self.sock = None
        self.states: dict[str, int] = {}
        self.identity = ""

    def connect(self):
        # FireTuner 单连接：先让会话守护进程断开，否则本进程会被拒绝
        T.yield_daemon()
        try:
            self.sock = T.connect(self.host, self.port)
            self.identity, self.states = T.handshake(self.sock)
            return True
        except (OSError, T.LinkClosed):
            self.sock = None
            return False

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def refresh(self) -> bool:
        """在同一连接上重发握手，刷新状态表。

        FireTuner 只允许一条连接：轮询期间要重读状态表，只能复用当前套接字，
        另开一条连接会被拒绝或顶掉自己。
        """
        if not self.sock:
            return self.connect()
        try:
            self.identity, self.states = T.handshake(self.sock)
            return True
        except (OSError, T.LinkClosed):
            self.close()
            return False

    def has(self, name: str) -> bool:
        return name in self.states

    def in_game(self) -> bool:
        return "GameCore_Tuner" in self.states and "InGame" in self.states

    def exec(self, state: str, code: str, timeout: float = 20.0):
        """在指定状态执行 Lua，返回输出行列表；LuaError/TimeoutError 上抛。"""
        if not self.sock and not self.connect():
            raise Fail("无法连接 4318")
        key = state
        if state == "gamecore":
            key = "GameCore_Tuner"
        elif state == "ingame":
            key = "InGame"
        if key not in self.states:
            raise Fail(f"状态 {key} 不存在（当前：{sorted(self.states)[:8]}…）")
        return T.execute(self.sock, self.states[key], code, timeout=timeout)

    def try_exec(self, state: str, code: str, timeout: float = 20.0):
        try:
            return 0, self.exec(state, code, timeout)
        except T.LuaError as e:
            return 2, [f"LUA ERROR: {e}"]
        except TimeoutError as e:
            return 3, [f"TIMEOUT: {e}"]
        except T.LinkClosed as e:
            return 4, [f"CLOSED: {e}"]


def esc_to_game():
    hwnd = GI.find_main_window()
    if not hwnd:
        raise Fail("未找到游戏窗口")
    if not GI.send_key(hwnd, GI.VK_ESCAPE):
        raise Fail("ESC 投递失败：目标窗口可能已关闭")


def deliver(s: Session, state: str, code: str, timeout: float) -> list[str]:
    """投递生命周期命令：回包丢失不算失败，返回收到的输出行。

    LoadGame / RestartGame / ExitToMainMenu 会在执行中途拆掉 Lua VM 与连接，
    因此 LinkClosed 与 TimeoutError 只提示，不中断后续的确认链；
    调用方凭返回的输出行判断引擎是否明确拒绝（形如 XXX=false）。
    """
    try:
        lines = s.exec(state, code, timeout=timeout)
    except T.LinkClosed as e:
        print(f"[..] 命令执行中连接被对端关闭（{e}），继续等对局重建")
        return []
    except TimeoutError:
        print("[..] 命令未回哨兵（VM 正在拆解），继续等对局重建")
        return []
    for line in lines:
        print(line)
    return lines


def require_ingame(what: str) -> None:
    """确认当前在对局内，否则立即报明确原因。

    主菜单只有 Main State / MainMenu，InGame 与 GameCore_Tuner 都不存在，
    任何依赖这两个态的命令都无从投递。挡在这里，命令立刻给出可操作的提示，
    不会白等一轮轮询再报成含糊的"等待超时"。
    """
    s = Session()
    if not s.connect():
        raise Fail("无法连接 4318：请先 gamectl.py launch，再 gamectl.py wait")
    try:
        if not s.in_game():
            raise Fail(f"当前不在对局内（{len(s.states)} 个状态）："
                       f"{what}需要先进对局，用 gamectl.py load <档名>")
    finally:
        s.close()


def wait_until(fn, timeout: float, interval: float, what: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if fn():
            return
        time.sleep(interval)
    raise Fail(f"等待超时（{timeout:.0f}s）：{what}")


def poll_session(want: str, timeout: float) -> Session:
    """反复重连，直到会话满足 want（ingame/inmenu/any）。

    inmenu 以 MainMenu 态出现为判据：冷启动期会先出现只含 "Main State" 的两三条状态，
    那不是可用的主菜单，投递建局命令会落进半初始化的上下文。
    """
    start = time.monotonic()
    deadline = start + timeout
    last = "尚未开始"
    last_report = 0.0
    while time.monotonic() < deadline:
        s = Session()
        if s.connect():
            if want == "any":
                return s
            if want == "ingame" and s.in_game():
                return s
            # 主菜单就绪以 MainMenu 出现为准：冷启动期先出现只有 "Main State" 的两三条状态，
            # 此时投递建局命令会落进半初始化的上下文。
            if want == "inmenu" and (not s.in_game()) and "MainMenu" in s.states:
                return s
            last = f"已连上但状态不满足 {want}（{len(s.states)} 个状态）"
            s.close()
        else:
            last = "4318 未监听（启动中或切换期）"
            if not GI._find_game_pids() and time.monotonic() - start > 10.0:
                raise Fail("游戏进程不存在：请先 launch 或手工启动游戏")
        if time.monotonic() - last_report > 15.0:
            last_report = time.monotonic()
            print(f"[..] 等待 {want} {time.monotonic() - start:.0f}s：{last}")
        time.sleep(3.0)
    raise Fail(f"等待 {want} 超时（{timeout:.0f}s）：{last}")


def try_direct_loadscreen_close(s: Session) -> bool:
    """溯源路线：读档/建局后的"点击进入"界面，官方 ESC 处理体是
    LoadScreen 态的 OnActivateButtonClicked()（LoadScreen.lua:42，核心命令
    Events.LoadScreenClose()）。该态在 LSQ 可达时直接调用，绕过按键注入。

    调用方传入已建立的会话：FireTuner 只允许一条连接，本函数另开一条会把
    调用方自己的连接顶掉，溯源路线因此永远走不通。返回是否成功。
    """
    if not s.refresh():
        return False
    for name in s.states:
        if "loadscreen" in name.lower():
            rc, out = s.try_exec(
                name,
                'if OnActivateButtonClicked ~= nil then '
                'OnActivateButtonClicked(); print("LS_CLOSED") '
                'else print("LS_NOFN") end',
                timeout=8.0)
            return rc == 0 and any("LS_CLOSED" in l for l in out)
    return False


def _advance_past_loadscreen(s: Session, last_flag: list) -> None:
    """确认链的单步推进：溯源路线优先，失败退回按键兜底。"""
    if try_direct_loadscreen_close(s):
        last_flag[0] = "direct"
        return
    esc_to_game()
    last_flag[0] = "esc"


def _dismiss_options_menu(s: Session, rounds: int = 3) -> None:
    """确认链收尾：按键推进的 ESC 过冲会把游戏内菜单（InGameTopOptionsMenu）留在屏上，
    遮挡后续画面观察并吞掉下一次投键。按状态表判定，重复投递 ESC 直到菜单关闭；
    连不上或退出对局即停，交回上层处理。"""
    for _ in range(rounds):
        if "InGameTopOptionsMenu" not in s.states:
            return
        try:
            esc_to_game()
        except Fail:
            return
        time.sleep(1.5)
        if not s.refresh() or not s.in_game():
            return


def read_turn(s: Session) -> int | None:
    """用已建立的会话读 gamecore 当前回合号；读不到返回 None。

    复用调用方的连接：FireTuner 只允许一条连接，另开一条会把自己这条顶掉。
    """
    rc, out = s.try_exec("gamecore", "print(Game.GetCurrentGameTurn())", timeout=8.0)
    if rc or not out:
        return None
    try:
        return int(out[-1])
    except ValueError:
        return None


def _probe_phase(states: dict[str, int] | None) -> str:
    """把一次探测结果归成五种相位。

    down     端口拒绝连接（Lua VM 正在拆解或重建）
    blank    端口可连但状态表为空（前端上下文已拆、新的还没建好）
    loadscreen  读档界面的上下文已出现，可直接调官方处理体
    ingame   两个引擎沙箱态齐备
    front    前端态（MainMenu / Main State）或其他非对局上下文

    blank 与 down 都表示"还在切换中、界面在等一次确认"，两者都必须推进；
    早先把 blank 归进 other 且不推进，实测在读档后空转 103 秒直到进程退出。
    """
    if states is None:
        return "down"
    if not states:
        return "blank"
    if "GameCore_Tuner" in states and "InGame" in states:
        return "ingame"
    if any("loadscreen" in n.lower() for n in states):
        return "loadscreen"
    return "front"


def enter_confirm_chain(timeout: float = 180.0):
    """重载/建局后的确认链：探测相位 → 单次推进 → 效果确认 → 连续采样判完成。

    探测用短超时的一二级链路（建连 0.5s + LSQ 1.5s），不持常驻连接：
    FireTuner 只允许一条连接，轮询期间另开连接会被拒绝或顶掉自己。
    推进每 2 秒最多一次，且只在读档界面可达（直调官方处理体）、端口关闭
    （按键兜底），或状态表持续为空超过宽限期时才发生；其余时刻不做任何投递，
    避免过冲把游戏内暂停菜单打出来。

    完成判定三条同时满足：已见过复位（端口关闭或读档界面出现）、连续两次
    采样都是 ingame、gamecore 能读出当前回合号。只看状态名会在旧 VM 尚未
    拆解时误判完成。
    """
    start = time.monotonic()
    deadline = start + timeout
    reset_seen = False
    advances = 0
    last_advance = 0.0
    last_flag = "-"
    advance_phase = ""
    last_report = 0.0
    last_phase = ""
    hits = 0
    blank_since = 0.0
    blank_attempts = 0
    last_states: dict[str, int] | None = None

    while time.monotonic() < deadline:
        states = TL.probe(_HOST, _PORT, PROBE_CONNECT, PROBE_LSQ)
        last_states = states
        phase = _probe_phase(states)
        if phase != last_phase:
            print(f"[..] 相位 {last_phase or '起始'} -> {phase}"
                  f"（{len(states) if states else 0} 个状态，"
                  f"{time.monotonic() - start:.0f}s）")
            last_phase = phase

        if phase == "ingame":
            hits += 1
            if hits >= CONFIRM_SAMPLES and reset_seen:
                s = Session()
                if not s.connect():
                    raise Fail("确认链：对局已就绪但连接建立失败")
                turn = read_turn(s)
                if turn is not None:
                    if last_flag == "esc":
                        _dismiss_options_menu(s)
                    print(f"[..] 确认链完成：回合 {turn}，推进 {advances} 次"
                          f"（最近方式：{last_flag}），{time.monotonic() - start:.1f}s")
                    return s
                s.close()
            time.sleep(POLL_GAP)
            continue

        hits = 0
        if phase in ("down", "blank", "loadscreen"):
            reset_seen = True
        if phase == "blank":
            if blank_since == 0.0:
                blank_since = time.monotonic()
        else:
            blank_since = 0.0
            blank_attempts = 0

        if phase in ("down", "blank") and not GI._find_game_pids():
            raise Fail("游戏进程已退出：确认链中止")

        # 按键只在有落点的时候投：down（端口拒绝、界面在等一次确认）与读档界面
        # 直接投；blank 表示 Lua VM 已拆、新的还没建好，先等满 BLANK_GRACE 再兜底，
        # 且总次数不超过 BLANK_MAX_ATTEMPTS。
        if phase in ("loadscreen", "down"):
            can_advance = True
        elif phase == "blank":
            can_advance = (time.monotonic() - blank_since >= BLANK_GRACE
                           and blank_attempts < BLANK_MAX_ATTEMPTS)
        else:
            can_advance = False
        # 效果确认：相位变化即认可上一发起了作用，允许立刻推进；相位没变则
        # 至少等满 STALL_INTERVAL 才允许重投，避免对同一界面连发。
        idle = time.monotonic() - last_advance
        due = idle >= ADVANCE_INTERVAL and (phase != advance_phase or idle >= STALL_INTERVAL)
        if can_advance and due:
            try:
                if phase == "loadscreen":
                    s = Session()
                    if s.connect():
                        try:
                            _advance_past_loadscreen(s, [last_flag])
                            last_flag = "direct"
                        finally:
                            s.close()
                    else:
                        esc_to_game()
                        last_flag = "esc"
                else:
                    esc_to_game()
                    last_flag = "esc"
                advances += 1
                last_advance = time.monotonic()
                advance_phase = phase
                if phase == "blank":
                    blank_attempts += 1
            except Fail as e:
                if not GI._find_game_pids():
                    raise Fail("游戏进程已退出：确认链中止") from e

        if time.monotonic() - last_report > 20.0:
            last_report = time.monotonic()
            print(f"[..] 确认链 {time.monotonic() - start:.0f}s"
                  f"（相位 {phase}，推进 {advances} 次，最近方式：{last_flag}）")
        time.sleep(POLL_GAP)

    detail = (f"已用 {time.monotonic() - start:.0f}s，相位 {last_phase or '未知'}，"
              f"状态 {len(last_states) if last_states else 0} 个，"
              f"推进 {advances} 次（最近方式：{last_flag}），"
              f"端口{'可用' if last_states is not None else '不可达'}")
    raise Fail(f"确认链超时：对局未进入（{detail}）")


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------
def require_ingame(cmd: str) -> Session:
    """要求当前在对局内；否则立即报明确原因，不进入轮询。

    主菜单没有 InGame 态，store / restart / exit-menu 都无从投递：
    此时若直接 poll_session("ingame", 60)，会在主菜单白等一整轮，
    最终报成含糊的"等待 ingame 超时"，掩盖真实原因。
    """
    s = Session()
    if not s.connect():
        raise Fail("无法连接 4318：请先 gamectl.py launch 并 wait")
    if not s.in_game():
        s.close()
        raise Fail(f"当前不在对局内（{len(s.states)} 个状态）：{cmd} 需要先 "
                   f"gamectl.py load <档名> 进入对局")
    return s


def cmd_wait(a):
    s = poll_session(a.want, a.timeout)
    print(f"[OK] {a.want} 就绪：{len(s.states)} 个状态，GameCore_Tuner={s.has('GameCore_Tuner')}")
    s.close()
    return 0


def cmd_save(a):
    """存档：要求当前在对局内。

    主菜单没有 InGame 态，存档命令无从投递：此时立即报明确原因，
    不进入 60 秒轮询（否则会在主菜单白等一轮，报成含糊的"等待超时"）。
    """
    require_ingame("存档")
    s = poll_session("ingame", 60)
    try:
        code = ('local gf={Name="%s",Location=SaveLocations.LOCAL_STORAGE,'
                'Type=SaveTypes.SINGLE_PLAYER,FileType=SaveFileTypes.GAME_STATE};'
                'local rc=Network.SaveGame(gf); print("SAVE_RC="..tostring(rc))') % a.name
        lines = s.exec("ingame", code, timeout=60.0)
        print("\n".join(lines))
        if "true" not in "".join(lines):
            raise Fail("SaveGame 未返回 true")
        target = SAVES_DIR / f"{a.name}.Civ6Save"
        wait_until(lambda: target.exists(), 20, 1.0, f"{target} 出现")
        print(f"[OK] 存档落盘：{target}")
    finally:
        s.close()
    return 0


def cmd_load(a):
    """读档：对局中先 LeaveGame，主菜单直接 LoadGame。

    Network.LoadGame 在主菜单同样可用，因此读档入口不要求当前已在对局中，
    冷启动后也能一条命令进入对局。前端尚未就绪（LSQ 状态表为空，游戏停在
    加载或切换过程中）时先等前端态出现，命令不会落进空上下文。
    """
    s = Session()
    if not s.connect():
        raise Fail("无法连接 4318")
    try:
        if not s.in_game() and "MainMenu" not in s.states and "Main State" not in s.states:
            s.close()
            s = poll_session("inmenu", a.timeout)
        if s.in_game():
            state, leave = "ingame", "Network.LeaveGame();"
        elif "MainMenu" in s.states:
            state, leave = "MainMenu", ""
        else:
            state, leave = "Main State", ""
        # 前端态（MainMenu / Main State）没有 ServerType 枚举，带第二个参数会抛
        # "attempt to index a nil value"；对局内才需要 SERVER_TYPE_NONE。
        server_arg = ", ServerType.SERVER_TYPE_NONE" if state == "ingame" else ""
        code = (leave +
                'local gf={Name="%s",Location=SaveLocations.LOCAL_STORAGE,'
                'Type=SaveTypes.SINGLE_PLAYER,FileType=SaveFileTypes.GAME_STATE};'
                'local rc=Network.LoadGame(gf%s);'
                'print("LOAD_RC="..tostring(rc))') % (a.name, server_arg)
        out = deliver(s, state, code, 60.0)
        if any("LOAD_RC=false" in ln for ln in out):
            raise Fail(f"LoadGame 被拒（存档名不存在或存档已损坏）：{a.name}")
    finally:
        s.close()
    s2 = enter_confirm_chain(a.timeout)
    print(f"[OK] 读档完成：{len(s2.states)} 个状态，GameCore_Tuner 就绪")
    s2.close()
    return 0


def cmd_restart(a):
    require_ingame("重开")
    s = poll_session("ingame", 60)
    try:
        out = deliver(s, "ingame", 'local rc=Network.RestartGame(); print("RESTART_RC="..tostring(rc))', 60.0)
        if any("RESTART_RC=false" in ln for ln in out):
            raise Fail("RestartGame 被拒")
    finally:
        s.close()
    s2 = enter_confirm_chain(a.timeout)
    print(f"[OK] 重开完成：GameCore_Tuner 就绪")
    s2.close()
    return 0


def cmd_exitmenu(a):
    require_ingame("退主菜单")
    s = poll_session("ingame", 60)
    try:
        deliver(s, "ingame", "Events.ExitToMainMenu(); print('EXIT_SENT')", 30.0)
    finally:
        s.close()
    poll_session("inmenu", a.timeout)
    print("[OK] 已回主菜单")
    return 0


def cmd_endturn(a):
    """结束回合并轮询回合推进。

    默认投递 UI 的 END_TURN 操作；--force 改发 REASON="UserForced"（Shift+Enter 等价，
    可推过被阻塞的回合）。推进与否以 gamecore 的 GetCurrentGameTurn 为准，
    轮询期间连接短暂不可达（AI 回合处理）按常态跳过。
    """
    s = require_ingame("结束回合")
    turn_code = "print(Game.GetCurrentGameTurn())"
    try:
        rc, out = s.try_exec("gamecore", turn_code, timeout=10.0)
        if rc:
            raise Fail(f"读取当前回合失败：{out}")
        before = int(out[-1])
        if a.force:
            code = ("UI.RequestAction(ActionTypes.ACTION_ENDTURN, {REASON='UserForced'}); "
                    "print('END_FORCED')")
        else:
            code = ("UI.RequestPlayerOperation(Game.GetLocalPlayer(), PlayerOperations.END_TURN, {}); "
                    "print('END_SENT')")
        s.exec("ingame", code, timeout=15.0)
        deadline = time.monotonic() + a.timeout
        while time.monotonic() < deadline:
            time.sleep(a.interval)
            # 复用同一条连接重发握手：另开连接会被拒绝，或把手里这条顶掉。
            if not s.refresh() or not s.in_game():
                continue
            rc2, out2 = s.try_exec("gamecore", turn_code, timeout=10.0)
            if rc2 == 0 and out2:
                try:
                    now = int(out2[-1])
                except ValueError:
                    continue
                if now != before:
                    print(f"[OK] 回合推进：{before} -> {now}")
                    return 0
        raise Fail(f"回合未推进（仍为 {before}）：可能存在阻塞项（试 --force）或 AI 回合处理中")
    finally:
        s.close()
    return 0


def cmd_kill(a):
    """结束游戏进程：按实际 PID 终止，覆盖 DX12 可执行文件与启动器子进程。"""
    pids = sorted(GI._find_game_pids())
    if not pids:
        print("[OK] 游戏进程不存在")
        return 0
    for pid in pids:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    wait_until(lambda: not GI._find_game_pids(), 30, 1.0, "游戏进程退出")
    print(f"[OK] 已结束游戏进程：{pids}")
    return 0


def cmd_close(a):
    """收尾流程：可选存档 → taskkill → 确认进程消失。"""
    if a.save:
        cmd_save(argparse.Namespace(name=a.save))
    cmd_kill(argparse.Namespace())
    print("[OK] 游戏已退出（收尾完成）")
    return 0


def cmd_launch(a):
    """直接拉起游戏进程。

    不经 PowerShell，路径里的空格与撇号原样传入，不存在引号被剥离后
    参数被拆成位置参数的问题。已在运行时直接拒绝：单实例游戏会静默退出，
    旧写法会把"本来就在跑的那个进程"当成启动成功。
    """
    exe = Path(a.exe) if a.exe else resolve_exe()
    if not exe.is_file():
        raise Fail(f"找不到可执行文件：{exe}")
    before = GI._find_game_pids()
    if before:
        raise Fail(f"游戏已在运行（pid={sorted(before)}），无需重复拉起")
    proc = subprocess.Popen(
        [str(exe)], cwd=str(exe.parent), close_fds=True,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    wait_until(lambda: bool(GI._find_game_pids()), 20, 1.0, "游戏进程出现")
    print(f"[OK] 已启动 {exe}（pid={proc.pid}），随后用 wait 等待 4318")
    return 0


def cmd_host_game(a):
    want_menu = poll_session("inmenu", 120)
    menu_key = "MainMenu"
    want_menu.close()
    s = Session()
    if not s.connect():
        raise Fail("连接失败")
    try:
        lid = a.leader or ""
        cid = a.civ or ""
        set_leader = ""
        if lid:
            set_leader = 'pcall(function() PlayerConfigurations[0]:SetLeaderTypeName("%s") end);' % lid
        if cid:
            set_leader += 'pcall(function() PlayerConfigurations[0]:SetCivilizationTypeName("%s") end);' % cid
        steps = [
            ('GameConfiguration.SetToDefaults()', "defaults"),
            ('GameConfiguration.SetValue("RULESET", nil)', "ruleset_nil"),
            ('BuildHeadlessGameSetup()', "headless"),
            ('RebuildPlayerParameters(true)', "rebuild"),
            ('GameSetup_RefreshParameters()', "refresh"),
            ('ReleasePlayerParameters()', "release"),
            ('HideGameSetup()', "hide"),
        ]
        for code, name in steps:
            rc, out = s.try_exec(menu_key, code, timeout=90.0)
            if rc:
                raise Fail(f"{name} 失败：{out}")
            print(f"[..] {name}: ok")
        if set_leader:
            rc, out = s.try_exec(menu_key, set_leader +
                                 'print("LEADER="..tostring(PlayerConfigurations[0]:GetLeaderTypeName()))', timeout=60.0)
            if rc:
                raise Fail(f"领袖设定失败：{out}")
            print(f"[..] leader: {out}")
        rc, out = s.try_exec(menu_key, 'Network.HostGame(ServerType.SERVER_TYPE_NONE); print("HOST_SENT")', timeout=60.0)
        if rc:
            raise Fail(f"HostGame 失败：{out}")
        print(f"[..] host: {out}")
    finally:
        s.close()
    s2 = enter_confirm_chain(a.timeout)
    print(f"[OK] 对局已进入（{len(s2.states)} 个状态）")
    s2.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="文明6 对局生命周期控制")
    ap.add_argument("--host", default=T.DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=T.DEFAULT_PORT)
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("wait"); p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--want", choices=["ingame", "inmenu", "any"], default="ingame")
    p.set_defaults(fn=cmd_wait)

    p = sub.add_parser("save"); p.add_argument("name"); p.set_defaults(fn=cmd_save)
    p = sub.add_parser("load"); p.add_argument("name")
    p.add_argument("--timeout", type=float, default=240.0); p.set_defaults(fn=cmd_load)
    p = sub.add_parser("restart"); p.add_argument("--timeout", type=float, default=240.0)
    p.set_defaults(fn=cmd_restart)
    p = sub.add_parser("exit-menu"); p.add_argument("--timeout", type=float, default=90.0)
    p.set_defaults(fn=cmd_exitmenu)
    p = sub.add_parser("end-turn")
    p.add_argument("--force", action="store_true", help="改发 REASON=UserForced，推过被阻塞的回合")
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--interval", type=float, default=5.0)
    p.set_defaults(fn=cmd_endturn)
    sub.add_parser("kill").set_defaults(fn=cmd_kill)
    p = sub.add_parser("close")
    p.add_argument("--save", default="", help="退出前先存的档名（留空跳过存档）")
    p.set_defaults(fn=cmd_close)
    p = sub.add_parser("launch")
    p.add_argument("--exe", default=None, help="可执行文件路径；缺省时自动解析安装位置")
    p.set_defaults(fn=cmd_launch)
    p = sub.add_parser("host-game")
    p.add_argument("--leader", default="")
    p.add_argument("--civ", default="")
    p.add_argument("--timeout", type=float, default=300.0)
    p.set_defaults(fn=cmd_host_game)

    args = ap.parse_args()
    if args.cmd is None:
        ap.print_help()
        return 1
    global _HOST, _PORT
    _HOST, _PORT = args.host, args.port
    try:
        return args.fn(args)
    except Fail as e:
        print(f"[FAIL] {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
