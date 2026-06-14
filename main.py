#!/usr/bin/env python3
"""
世界杯比赛量化分析工具 — CLI

用法:
    # 命令行模式
    python main.py "Argentina" "France"
    python main.py "Argentina" "France" --odds 2.10 3.50 3.80
    python main.py "Argentina" "France" --odds 2.10 3.50 3.80 --location home
    python main.py "Argentina" "France" --a-attack 0.92 --a-defense 0.95  (主力缺席)
    python main.py "Argentina" "France" --mc 100000  (蒙特卡洛模拟)

    # 交互模式
    python main.py --interactive

    # 小组分析
    python main.py --group A

    # 列出所有球队
    python main.py --list
"""

import argparse
import sys
import os
import io
from typing import Optional

# ---- Windows UTF-8 编码修复 ----
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError):
        pass

# 确保能找到 data 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import (
    FIFA_RANKINGS, WORLD_CUP_GROUPS, resolve_team, get_team_data,
    list_teams, get_group_teams, find_team_group,
)
from analyzer import (
    predict_match, monte_carlo_simulation,
    TeamStrength, MatchPrediction, OddsAnalysis,
)


# ============================================================
# 输出格式化
# ============================================================
SEPARATOR = "═" * 72
SEPARATOR_THIN = "─" * 72
SEP_SHORT = "─" * 48

# 颜色代码 (ANSI)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def color_prob(p: float) -> str:
    """根据概率大小着色"""
    if p >= 0.50:
        return f"{Colors.GREEN}{p:.1%}{Colors.RESET}"
    elif p >= 0.30:
        return f"{Colors.YELLOW}{p:.1%}{Colors.RESET}"
    else:
        return f"{Colors.RED}{p:.1%}{Colors.RESET}"


def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{SEPARATOR}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{SEPARATOR}{Colors.RESET}\n")


def print_prediction(pred: MatchPrediction):
    """打印完整的预测报告"""

    # ========== 球队对比 ==========
    print_header("📊 球队实力对比")

    sa, sb = pred.strength_a, pred.strength_b

    # 表头
    print(f"{'':<24} {Colors.BOLD}{pred.team_a:<20}{pred.team_b:<20}{Colors.RESET}")
    print(f"{SEPARATOR_THIN}")

    # FIFA排名
    print(f"{'FIFA 世界排名':<24} {sa.fifa_rank:<20} {sb.fifa_rank:<20}")
    print(f"{'FIFA 积分':<24} {sa.fifa_points:<20.0f} {sb.fifa_points:<20.0f}")
    if sa.elo and sb.elo:
        print(f"{'ELO 评分':<24} {sa.elo:<20.0f} {sb.elo:<20.0f}")

    print(f"{SEPARATOR_THIN}")

    # 攻防参数
    print(f"{'进攻系数 (原始)':<24} {sa.attack:<20.3f} {sb.attack:<20.3f}")
    print(f"{'防守系数 (原始)':<24} {sa.defense:<20.3f} {sb.defense:<20.3f}")

    if sa.attack_adj != 1.0 or sa.defense_adj != 1.0:
        print(f"{Colors.YELLOW}{'进攻调整':<24} {sa.attack_adj:<20.3f} {'—':<20}{Colors.RESET}")
        print(f"{Colors.YELLOW}{'防守调整':<24} {sa.defense_adj:<20.3f} {'—':<20}{Colors.RESET}")
    if sb.attack_adj != 1.0 or sb.defense_adj != 1.0:
        print(f"{Colors.YELLOW}{'进攻调整':<24} {'—':<20} {sb.attack_adj:<20.3f}{Colors.RESET}")
        print(f"{Colors.YELLOW}{'防守调整':<24} {'—':<20} {sb.defense_adj:<20.3f}{Colors.RESET}")

    if sa.attack_adj != 1.0 or sa.defense_adj != 1.0 or sb.attack_adj != 1.0 or sb.defense_adj != 1.0:
        print(f"{SEPARATOR_THIN}")
        print(f"{Colors.YELLOW}{'进攻系数 (有效)':<24} {sa.effective_attack:<20.3f} {sb.effective_attack:<20.3f}{Colors.RESET}")
        print(f"{Colors.YELLOW}{'防守系数 (有效)':<24} {sa.effective_defense:<20.3f} {sb.effective_defense:<20.3f}{Colors.RESET}")

    print(f"{SEPARATOR_THIN}")
    print(f"{'预期进球 (xG)':<24} {Colors.BOLD}{pred.lambda_a:<20.2f} {pred.lambda_b:<20.2f}{Colors.RESET}")

    # ========== 胜平负概率 ==========
    print_header("🎯 胜平负概率")

    print(f"  {pred.team_a} 胜:  {Colors.BOLD}{color_prob(pred.prob_a_win)}{Colors.RESET}")
    print(f"  平局:      {Colors.BOLD}{color_prob(pred.prob_draw)}{Colors.RESET}")
    print(f"  {pred.team_b} 胜:  {Colors.BOLD}{color_prob(pred.prob_b_win)}{Colors.RESET}")

    # 概率条形图
    print(f"\n  {Colors.DIM}概率分布:{Colors.RESET}")
    max_bar_width = 50
    bar_a = int(pred.prob_a_win * max_bar_width)
    bar_d = int(pred.prob_draw * max_bar_width)
    bar_b = int(pred.prob_b_win * max_bar_width)

    print(f"  {pred.team_a[:12]:<12} {Colors.GREEN}{'█' * bar_a}{Colors.RESET}{Colors.DIM}{'░' * (max_bar_width - bar_a)}{Colors.RESET} {pred.prob_a_win:.1%}")
    print(f"  {'平局':<12} {Colors.YELLOW}{'█' * bar_d}{Colors.RESET}{Colors.DIM}{'░' * (max_bar_width - bar_d)}{Colors.RESET} {pred.prob_draw:.1%}")
    print(f"  {pred.team_b[:12]:<12} {Colors.RED}{'█' * bar_b}{Colors.RESET}{Colors.DIM}{'░' * (max_bar_width - bar_b)}{Colors.RESET} {pred.prob_b_win:.1%}")

    # ========== 最可能比分 ==========
    print_header("⚽ 最可能比分 (TOP 10)")

    print(f"  {'比分':<10} {'概率':<12} {'累计':<12} {'结果':<20}")
    print(f"  {SEP_SHORT}")
    cum = 0.0
    for i, sp in enumerate(pred.top_scores):
        cum += sp.probability
        result = f"{pred.team_a}胜" if sp.home_goals > sp.away_goals else \
                 (f"{pred.team_b}胜" if sp.home_goals < sp.away_goals else "平局")
        marker = " ◀ 最可能" if i == 0 else ""
        print(f"  {sp.home_goals}-{sp.away_goals:<8} {sp.probability:.2%} {'':<7} {cum:.2%} {'':<7} {result:<20}{marker}")

    # ========== 特殊盘口 ==========
    print_header("📈 大小球 & 特殊盘口")

    print(f"  总进球预期:        {Colors.BOLD}{pred.expected_total_goals:.2f}{Colors.RESET}")
    print(f"  大于 1.5 球:       {color_prob(pred.over_15_prob)}")
    print(f"  大于 2.5 球:       {color_prob(pred.over_25_prob)}")
    print(f"  大于 3.5 球:       {color_prob(pred.over_35_prob)}")
    print(f"  双方进球 (BTTS):   {color_prob(pred.btts_prob)}")

    # ========== 赔率分析 ==========
    if pred.odds_analysis:
        print_header("💰 赔率分析")
        oa = pred.odds_analysis

        print(f"  原始赔率 (1X2):  {oa.raw_odds['home_win']:.2f} / {oa.raw_odds['draw']:.2f} / {oa.raw_odds['away_win']:.2f}")
        print(f"  抽水率:          {oa.overround:.2%}")
        print()
        print(f"  {'':<16} {'胜':<16} {'平':<16} {'负':<16}")
        print(f"  {SEP_SHORT}")
        print(f"  {'隐含概率':<16} {oa.implied_probs['home_win']:.2%} {'':<10} {oa.implied_probs['draw']:.2%} {'':<10} {oa.implied_probs['away_win']:.2%}")
        print(f"  {'公允概率':<16} {oa.fair_probs['home_win']:.2%} {'':<10} {oa.fair_probs['draw']:.2%} {'':<10} {oa.fair_probs['away_win']:.2%}")
        print(f"  {'模型概率':<16} {pred.prob_a_win:.2%} {'':<10} {pred.prob_draw:.2%} {'':<10} {pred.prob_b_win:.2%}")

        if pred.blended_probs:
            print(f"  {Colors.CYAN}{'融合概率':<16} {pred.blended_probs['home_win']:.2%} {'':<10} {pred.blended_probs['draw']:.2%} {'':<10} {pred.blended_probs['away_win']:.2%}{Colors.RESET}")

        # 价值投注
        if oa.value_bets:
            print(f"\n  {Colors.GREEN}{Colors.BOLD}💎 价值投注发现:{Colors.RESET}")
            for vb in oa.value_bets:
                edge_pct = vb['edge'] * 100
                print(f"  → {vb['outcome']}: 模型{vb['model_prob']:.1%} vs 市场{vb['market_prob']:.1%} "
                      f"(优势 {edge_pct:.1f}%) @ {vb['odds']:.2f} [{vb['recommendation']}]")
        else:
            print(f"\n  {Colors.DIM}未发现明显价值投注 (模型与市场基本一致){Colors.RESET}")

    # ========== 综合比分推荐 ==========
    print_header("🏆 综合比分预测")

    # 融合概率 (如果可用) 否则用模型概率
    if pred.blended_probs:
        a_win = pred.blended_probs['home_win']
        draw = pred.blended_probs['draw']
        b_win = pred.blended_probs['away_win']
    else:
        a_win = pred.prob_a_win
        draw = pred.prob_draw
        b_win = pred.prob_b_win

    # 最可能结果
    probs_sorted = [
        (f"{pred.team_a} 胜", a_win),
        ("平局", draw),
        (f"{pred.team_b} 胜", b_win),
    ]
    probs_sorted.sort(key=lambda x: x[1], reverse=True)

    print(f"  最可能结果: {Colors.BOLD}{Colors.GREEN}{probs_sorted[0][0]}{Colors.RESET} (概率 {probs_sorted[0][1]:.1%})")
    print(f"  最可能比分: {Colors.BOLD}{Colors.CYAN}{pred.most_likely_score}{Colors.RESET}")

    # 条件期望比分
    if a_win > 0.10:
        print(f"  若{pred.team_a}胜, 期望比分: {Colors.DIM}{pred.exp_a_goals_if_win:.1f} - {pred.exp_b_goals_if_win:.1f}{Colors.RESET}")
    if draw > 0.10:
        # 从比分矩阵中找到最可能的平局比分
        draw_scores = [(ga, gb) for (ga, gb) in pred.score_matrix if ga == gb and ga > 0]
        if draw_scores:
            # 找最大概率的平局比分
            best_draw = max(draw_scores, key=lambda s: pred.score_matrix[s])
            print(f"  最可能平局比分: {Colors.DIM}{best_draw[0]}-{best_draw[1]}{Colors.RESET}")
    if b_win > 0.10:
        print(f"  若{pred.team_b}胜, 期望比分: {Colors.DIM}{pred.exp_a_goals_if_lose:.1f} - {pred.exp_b_goals_if_lose:.1f}{Colors.RESET}")

    print()


def print_group_analysis(group: str):
    """打印小组分析"""
    teams = get_group_teams(group)
    if not teams:
        print(f"未找到小组: {group}")
        print(f"可用小组: {', '.join(sorted(WORLD_CUP_GROUPS.keys()))}")
        return

    print_header(f"🏆 小组 {group.upper()} 球队分析")

    # 球队实力排序
    team_strengths = []
    for team in teams:
        data = get_team_data(team)
        if data:
            from analyzer import build_team_strength
            ts = build_team_strength(team)
            if ts:
                team_strengths.append((team, data['rank'], data['points'], ts.attack, ts.defense))
            else:
                team_strengths.append((team, data['rank'], data['points'], 0, 0))

    team_strengths.sort(key=lambda x: x[1])  # 按排名升序

    print(f"  {'球队':<20} {'FIFA排名':<10} {'积分':<10} {'进攻':<10} {'防守':<10}")
    print(f"  {SEP_SHORT}")
    for name, rank, pts, att, def_ in team_strengths:
        print(f"  {name:<20} {rank:<10} {pts:<10.0f} {att:<10.3f} {def_:<10.3f}")

    # 所有对阵预测
    print(f"\n  {Colors.BOLD}📅 小组赛对阵预测:{Colors.RESET}\n")

    matches = []
    n = len(teams)
    for i in range(n):
        for j in range(i + 1, n):
            try:
                pred = predict_match(teams[i], teams[j], location='neutral')
                matches.append((teams[i], teams[j], pred))
            except Exception as e:
                print(f"  {Colors.RED}预测 {teams[i]} vs {teams[j]} 失败: {e}{Colors.RESET}")

    for t1, t2, pred in matches:
        print(f"  {Colors.BOLD}{t1} vs {t2}{Colors.RESET}")
        print(f"    胜平负: {pred.prob_a_win:.1%} / {pred.prob_draw:.1%} / {pred.prob_b_win:.1%}")
        print(f"    最可能比分: {pred.most_likely_score}  |  xG: {pred.lambda_a:.2f} - {pred.lambda_b:.2f}")
        print()


def print_team_list():
    """列出所有球队"""
    print_header("📋 球队数据库")

    teams_by_confed = {}
    for name, data in FIFA_RANKINGS.items():
        conf = data['confederation']
        if conf not in teams_by_confed:
            teams_by_confed[conf] = []
        teams_by_confed[conf].append((name, data['rank'], data['points']))

    for conf in sorted(teams_by_confed.keys()):
        print(f"\n  {Colors.BOLD}{conf}{Colors.RESET}")
        print(f"  {'球队':<24} {'排名':<8} {'积分':<8}")
        print(f"  {SEP_SHORT}")
        for name, rank, pts in sorted(teams_by_confed[conf], key=lambda x: x[1]):
            # 标记是否为2026世界杯参赛队
            group = find_team_group(name)
            marker = f" [小组{group}]" if group else ""
            print(f"  {name:<24} {rank:<8} {pts:<8.0f}{marker}")


def interactive_mode():
    """交互模式"""
    print_header("🌍 世界杯量化分析工具 — 交互模式")
    print("  输入 'q' 退出, 'list' 列出球队, 'group X' 查看小组\n")

    while True:
        try:
            cmd = input(f"{Colors.CYAN}> {Colors.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        if not cmd:
            continue

        if cmd.lower() in ('q', 'quit', 'exit'):
            print("再见!")
            break

        if cmd.lower() in ('list', 'ls', 'teams'):
            print_team_list()
            continue

        if cmd.lower().startswith('group '):
            group = cmd.split()[1].upper()
            print_group_analysis(group)
            continue

        # 解析比赛: "TeamA vs TeamB" 或 "TeamA, TeamB"
        import re

        # 检查是否包含赔率: "TeamA vs TeamB odds:2.10/3.50/3.80"
        odds_match = re.search(r'odds\s*[:：]\s*([\d.]+)\s*[/,]\s*([\d.]+)\s*[/,]\s*([\d.]+)', cmd)
        odds_a = float(odds_match.group(1)) if odds_match else None
        odds_draw = float(odds_match.group(2)) if odds_match else None
        odds_b = float(odds_match.group(3)) if odds_match else None

        # 去除赔率部分
        clean_cmd = re.sub(r'odds\s*[:：].*$', '', cmd).strip()

        # 解析球队
        teams = re.split(r'\s+(?:vs|v|VS|V|Vs|vS)\s+', clean_cmd)
        if len(teams) != 2:
            teams = re.split(r'\s*[,，]\s*', clean_cmd)

        if len(teams) != 2:
            print(f"{Colors.RED}请使用格式: TeamA vs TeamB [odds:2.10/3.50/3.80]{Colors.RESET}")
            continue

        team_a, team_b = teams[0].strip(), teams[1].strip()

        # 询问额外信息
        loc = input(f"  场地 [{Colors.DIM}home/neutral/away, 默认neutral{Colors.RESET}]: ").strip().lower()
        location = loc if loc in ('home', 'away') else 'neutral'

        # 主力缺席
        adj_a = input(f"  {team_a} 主力缺席? [{Colors.DIM}进攻调整系数 默认1.0{Colors.RESET}]: ").strip()
        a_att = float(adj_a) if adj_a else 1.0
        adj_d = input(f"  {team_a} 防守调整? [{Colors.DIM}默认1.0{Colors.RESET}]: ").strip()
        a_def = float(adj_d) if adj_d else 1.0

        adj_b = input(f"  {team_b} 主力缺席? [{Colors.DIM}进攻调整系数 默认1.0{Colors.RESET}]: ").strip()
        b_att = float(adj_b) if adj_b else 1.0
        adj_bd = input(f"  {team_b} 防守调整? [{Colors.DIM}默认1.0{Colors.RESET}]: ").strip()
        b_def = float(adj_bd) if adj_bd else 1.0

        # 执行预测
        try:
            pred = predict_match(
                team_a, team_b,
                location=location,
                odds_a=odds_a, odds_draw=odds_draw, odds_b=odds_b,
                a_attack_adj=a_att, a_defense_adj=a_def,
                b_attack_adj=b_att, b_defense_adj=b_def,
            )
            print_prediction(pred)
        except ValueError as e:
            print(f"{Colors.RED}错误: {e}{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}预测失败: {e}{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description='世界杯比赛量化分析工具 — 结合博彩赔率与数据模型的比分预测',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py Argentina France
  python main.py "Argentina" "France" --odds 2.10 3.50 3.80
  python main.py Brazil Germany --odds 2.50 3.20 2.80 --location neutral
  python main.py England Spain --a-attack 0.90 --a-defense 0.95  (英格兰进攻核心缺席)
  python main.py --group A
  python main.py --interactive
  python main.py --list
  python main.py Argentina France --mc 100000
        """
    )

    parser.add_argument('team_a', nargs='?', help='球队A名称')
    parser.add_argument('team_b', nargs='?', help='球队B名称')
    parser.add_argument('--odds', '-o', nargs=3, type=float, metavar=('WIN', 'DRAW', 'LOSE'),
                        help='欧洲盘赔率 (A胜 平 B胜)')
    parser.add_argument('--location', '-l', choices=['home', 'neutral', 'away'],
                        default='neutral', help='场地 (从球队A视角, 默认neutral)')
    parser.add_argument('--a-attack', type=float, default=1.0,
                        help='A队进攻调整系数 (<1=主力缺席, >1=状态火热)')
    parser.add_argument('--a-defense', type=float, default=1.0,
                        help='A队防守调整系数')
    parser.add_argument('--b-attack', type=float, default=1.0,
                        help='B队进攻调整系数')
    parser.add_argument('--b-defense', type=float, default=1.0,
                        help='B队防守调整系数')
    parser.add_argument('--model-weight', '-w', type=float, default=0.40,
                        help='模型权重 (0-1, 默认0.4; 1=纯模型, 0=纯赔率)')
    parser.add_argument('--mc', type=int, metavar='N',
                        help='蒙特卡洛模拟次数 (如 100000)')
    parser.add_argument('--group', '-g', help='分析整个小组')
    parser.add_argument('--list', action='store_true', help='列出所有球队')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互模式')

    args = parser.parse_args()

    # 交互模式
    if args.interactive:
        interactive_mode()
        return

    # 列出球队
    if args.list:
        print_team_list()
        return

    # 小组分析
    if args.group:
        print_group_analysis(args.group)
        return

    # 单场比赛分析
    if not args.team_a or not args.team_b:
        parser.print_help()
        print(f"\n{Colors.YELLOW}提示: 请指定两支球队, 或使用 --interactive 进入交互模式{Colors.RESET}")
        sys.exit(1)

    # 解析赔率
    odds_a, odds_draw, odds_b = None, None, None
    if args.odds:
        odds_a, odds_draw, odds_b = args.odds

    # 执行预测
    try:
        pred = predict_match(
            args.team_a, args.team_b,
            location=args.location,
            odds_a=odds_a, odds_draw=odds_draw, odds_b=odds_b,
            a_attack_adj=args.a_attack, a_defense_adj=args.a_defense,
            b_attack_adj=args.b_attack, b_defense_adj=args.b_defense,
            model_weight=args.model_weight,
        )
        print_prediction(pred)

        # 蒙特卡洛验证
        if args.mc:
            print_header("🎲 蒙特卡洛模拟验证")
            mc_result = monte_carlo_simulation(pred.lambda_a, pred.lambda_b, args.mc)
            print(f"  模拟次数: {mc_result['n_simulations']:,}")
            print(f"  解析解:    {pred.prob_a_win:.2%} / {pred.prob_draw:.2%} / {pred.prob_b_win:.2%}")
            print(f"  模拟解:    {mc_result['home_win']:.2%} / {mc_result['draw']:.2%} / {mc_result['away_win']:.2%}")
            print(f"\n  {Colors.DIM}模拟最可能比分:{Colors.RESET}")
            for s in mc_result['top_scores'][:5]:
                print(f"    {s['score']}: {s['prob']:.2%}")

    except ValueError as e:
        print(f"{Colors.RED}错误: {e}{Colors.RESET}")
        print(f"\n可用球队: {', '.join(sorted(FIFA_RANKINGS.keys()))}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}预测失败: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == '__main__':
    main()
