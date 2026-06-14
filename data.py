"""
2026 世界杯球队数据
包含 FIFA 排名、实力参数、小组赛分组等信息
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List

# ============================================================
# FIFA 世界排名数据 (近似2026年5月排名)
# ============================================================
# 格式: { 队名: { 'rank': 排名, 'points': FIFA积分, 'confederation': 洲际, 'elo': ELO分 } }

FIFA_RANKINGS: Dict[str, dict] = {
    # 顶级强队 (Tier 1)
    'Argentina':      {'rank': 1,  'points': 1885, 'confederation': 'CONMEBOL', 'elo': 2135},
    'France':          {'rank': 2,  'points': 1863, 'confederation': 'UEFA',     'elo': 2110},
    'Spain':           {'rank': 3,  'points': 1850, 'confederation': 'UEFA',     'elo': 2095},
    'England':         {'rank': 4,  'points': 1835, 'confederation': 'UEFA',     'elo': 2080},
    'Brazil':          {'rank': 5,  'points': 1820, 'confederation': 'CONMEBOL', 'elo': 2070},
    'Portugal':        {'rank': 6,  'points': 1805, 'confederation': 'UEFA',     'elo': 2055},
    'Netherlands':     {'rank': 7,  'points': 1790, 'confederation': 'UEFA',     'elo': 2040},
    'Germany':         {'rank': 8,  'points': 1775, 'confederation': 'UEFA',     'elo': 2030},
    'Italy':           {'rank': 9,  'points': 1760, 'confederation': 'UEFA',     'elo': 2015},
    'Colombia':        {'rank': 10, 'points': 1745, 'confederation': 'CONMEBOL', 'elo': 2000},

    # 劲旅 (Tier 2)
    'Uruguay':         {'rank': 11, 'points': 1730, 'confederation': 'CONMEBOL', 'elo': 1985},
    'Croatia':         {'rank': 12, 'points': 1715, 'confederation': 'UEFA',     'elo': 1970},
    'Morocco':         {'rank': 13, 'points': 1700, 'confederation': 'CAF',      'elo': 1955},
    'Japan':           {'rank': 14, 'points': 1685, 'confederation': 'AFC',      'elo': 1940},
    'USA':             {'rank': 15, 'points': 1670, 'confederation': 'CONCACAF', 'elo': 1925},
    'Mexico':          {'rank': 16, 'points': 1660, 'confederation': 'CONCACAF', 'elo': 1910},
    'Senegal':         {'rank': 17, 'points': 1645, 'confederation': 'CAF',      'elo': 1895},
    'Switzerland':     {'rank': 18, 'points': 1635, 'confederation': 'UEFA',     'elo': 1885},
    'Denmark':         {'rank': 19, 'points': 1625, 'confederation': 'UEFA',     'elo': 1875},
    'Belgium':         {'rank': 20, 'points': 1615, 'confederation': 'UEFA',     'elo': 1865},

    # 中坚力量 (Tier 3)
    'Iran':            {'rank': 21, 'points': 1600, 'confederation': 'AFC',      'elo': 1845},
    'Austria':         {'rank': 22, 'points': 1590, 'confederation': 'UEFA',     'elo': 1835},
    'Korea Republic':  {'rank': 23, 'points': 1580, 'confederation': 'AFC',      'elo': 1825},
    'Australia':       {'rank': 24, 'points': 1570, 'confederation': 'AFC',      'elo': 1815},
    'Ukraine':         {'rank': 25, 'points': 1560, 'confederation': 'UEFA',     'elo': 1805},
    'Egypt':           {'rank': 26, 'points': 1550, 'confederation': 'CAF',      'elo': 1795},
    'Nigeria':         {'rank': 27, 'points': 1540, 'confederation': 'CAF',      'elo': 1785},
    'Serbia':          {'rank': 28, 'points': 1530, 'confederation': 'UEFA',     'elo': 1775},
    'Chile':           {'rank': 29, 'points': 1520, 'confederation': 'CONMEBOL', 'elo': 1765},
    'Poland':          {'rank': 30, 'points': 1510, 'confederation': 'UEFA',     'elo': 1755},

    # 中下游 (Tier 4)
    'Czech Republic':  {'rank': 31, 'points': 1500, 'confederation': 'UEFA',     'elo': 1745},
    'Hungary':         {'rank': 32, 'points': 1490, 'confederation': 'UEFA',     'elo': 1735},
    'Scotland':        {'rank': 33, 'points': 1480, 'confederation': 'UEFA',     'elo': 1725},
    'Canada':          {'rank': 34, 'points': 1470, 'confederation': 'CONCACAF', 'elo': 1715},
    'Peru':            {'rank': 35, 'points': 1460, 'confederation': 'CONMEBOL', 'elo': 1705},
    'Greece':          {'rank': 36, 'points': 1450, 'confederation': 'UEFA',     'elo': 1695},
    'Qatar':           {'rank': 37, 'points': 1440, 'confederation': 'AFC',      'elo': 1685},
    'Saudi Arabia':    {'rank': 38, 'points': 1430, 'confederation': 'AFC',      'elo': 1675},
    'Costa Rica':      {'rank': 39, 'points': 1420, 'confederation': 'CONCACAF', 'elo': 1665},
    'Mali':            {'rank': 40, 'points': 1410, 'confederation': 'CAF',      'elo': 1655},
    'Jamaica':         {'rank': 41, 'points': 1400, 'confederation': 'CONCACAF', 'elo': 1645},
    'Panama':          {'rank': 42, 'points': 1390, 'confederation': 'CONCACAF', 'elo': 1635},
    'United Arab Emirates': {'rank': 43, 'points': 1380, 'confederation': 'AFC', 'elo': 1625},
    'China PR':        {'rank': 44, 'points': 1370, 'confederation': 'AFC',      'elo': 1615},

    # 下游球队 (Tier 5)
    'Iraq':            {'rank': 45, 'points': 1355, 'confederation': 'AFC',      'elo': 1590},
    'South Africa':    {'rank': 46, 'points': 1340, 'confederation': 'CAF',      'elo': 1570},
    'New Zealand':     {'rank': 47, 'points': 1320, 'confederation': 'OFC',      'elo': 1540},
    'Bahrain':         {'rank': 48, 'points': 1300, 'confederation': 'AFC',      'elo': 1510},
    'Burkina Faso':    {'rank': 49, 'points': 1280, 'confederation': 'CAF',      'elo': 1490},
    'Congo DR':        {'rank': 50, 'points': 1260, 'confederation': 'CAF',      'elo': 1470},
    'Oman':            {'rank': 51, 'points': 1240, 'confederation': 'AFC',      'elo': 1450},
    'Slovenia':        {'rank': 52, 'points': 1220, 'confederation': 'UEFA',     'elo': 1430},
    'Honduras':        {'rank': 53, 'points': 1200, 'confederation': 'CONCACAF', 'elo': 1410},
    'Curacao':         {'rank': 82, 'points': 1280, 'confederation': 'CONCACAF', 'elo': 1470},
    'Curaçao':         {'rank': 82, 'points': 1280, 'confederation': 'CONCACAF', 'elo': 1470},
}

# 别名映射 (处理常见缩写和不同拼写)
TEAM_ALIASES = {
    'usa': 'USA',
    'us': 'USA',
    'united states': 'USA',
    'united states of america': 'USA',
    'korea': 'Korea Republic',
    'south korea': 'Korea Republic',
    'korea republic': 'Korea Republic',
    'korea dpr': 'Korea Republic',
    'dpr korea': 'Korea Republic',
    'uae': 'United Arab Emirates',
    'united arab emirates': 'United Arab Emirates',
    'china': 'China PR',
    'china pr': 'China PR',
    'dr congo': 'Congo DR',
    'congo': 'Congo DR',
    'nz': 'New Zealand',
    'new zealand': 'New Zealand',
    'saudi': 'Saudi Arabia',
    'ksa': 'Saudi Arabia',
    'dutch': 'Netherlands',
    'holland': 'Netherlands',
    'azurri': 'Italy',
    'three lions': 'England',
    'les bleus': 'France',
    'la roja': 'Spain',
    'selecao': 'Brazil',
    'canarinho': 'Brazil',
    'albiceleste': 'Argentina',
    'die mannschaft': 'Germany',
    'socceroos': 'Australia',
    'all whites': 'New Zealand',
    'atlas lions': 'Morocco',
    'super eagles': 'Nigeria',
    'pharaohs': 'Egypt',
    'regragui': 'Morocco',
}

# ============================================================
# 2026 世界杯小组赛分组
# ============================================================
# 注: 请根据实际抽签结果更新

WORLD_CUP_GROUPS: Dict[str, List[str]] = {
    'A': ['Canada', 'Mexico', 'Hungary', 'Saudi Arabia'],
    'B': ['Argentina', 'Uruguay', 'Iran', 'Ukraine'],
    'C': ['France', 'USA', 'South Africa', 'United Arab Emirates'],
    'D': ['Brazil', 'Switzerland', 'Senegal', 'China PR'],
    'E': ['England', 'Croatia', 'Japan', 'New Zealand'],
    'F': ['Portugal', 'Netherlands', 'Morocco', 'Panama'],
    'G': ['Germany', 'Colombia', 'Egypt', 'Jamaica'],
    'H': ['Spain', 'Belgium', 'Nigeria', 'Iraq'],
    'I': ['Italy', 'Denmark', 'Chile', 'Australia'],
    'J': ['Austria', 'Serbia', 'Costa Rica', 'Qatar'],
    'K': ['Poland', 'Czech Republic', 'Scotland', 'Mali'],
    'L': ['Greece', 'Korea Republic', 'Peru', 'Slovenia'],
}

# ============================================================
# 主场优势参数
# ============================================================
LOCATION_FACTORS = {
    'home': 1.25,      # 真正主场 (在北美举办的比赛，美/加/墨享有)
    'neutral': 1.0,    # 中立场地 (大多数世界杯比赛)
    'away': 0.80,      # 客场
}

# 2026世界杯主办国 (享有实际主场优势的比赛)
HOST_NATIONS = {'USA', 'Canada', 'Mexico'}

# ============================================================
# 世界平均数据 (用于归一化)
# ============================================================
WORLD_AVERAGE_GOALS = 1.35        # 国际比赛场均进球
WORLD_AVERAGE_FIFA_POINTS = 1500  # FIFA积分世界均值

# ============================================================
# 模型参数 (可调校)
# ============================================================
# 攻防幂律指数 — 控制强队与弱队之间的差距程度
# 指数越大, 强队优势越明显; 指数越小, 比赛越"公平"
ATTACK_EXPONENT = 1.6    # 进攻系数指数 (推荐 1.3~2.0)
DEFENSE_EXPONENT = 1.1   # 防守系数指数 (推荐 0.8~1.5)
# 注: 1.6/1.1 组合下, 顶级队对下游队胜率约70-75%, 符合国际比赛实际
#      若偏保守可降至 1.2/0.8, 偏激进可升至 2.0/1.5

# ============================================================
# 球队别名解析函数
# ============================================================
def resolve_team(name: str) -> Optional[str]:
    """根据各种拼写/别名解析为标准队名"""
    # 精确匹配
    if name in FIFA_RANKINGS:
        return name
    # 大小写不敏感精确匹配
    name_lower = name.lower().strip()
    for team in FIFA_RANKINGS:
        if team.lower() == name_lower:
            return team
    # 别名匹配
    if name_lower in TEAM_ALIASES:
        return TEAM_ALIASES[name_lower]
    # 模糊匹配 (包含)
    for team in FIFA_RANKINGS:
        if name_lower in team.lower() or team.lower() in name_lower:
            return team
    return None


def get_team_data(team_name: str) -> Optional[dict]:
    """获取球队完整数据"""
    resolved = resolve_team(team_name)
    if resolved:
        return {'name': resolved, **FIFA_RANKINGS[resolved]}
    return None


def list_teams(confederation: Optional[str] = None) -> List[str]:
    """列出所有球队"""
    if confederation:
        return [name for name, data in FIFA_RANKINGS.items()
                if data['confederation'].upper() == confederation.upper()]
    return sorted(FIFA_RANKINGS.keys())


def get_group_teams(group: str) -> List[str]:
    """获取某小组的球队"""
    return WORLD_CUP_GROUPS.get(group.upper(), [])


def find_team_group(team_name: str) -> Optional[str]:
    """查找球队所在小组"""
    resolved = resolve_team(team_name)
    if not resolved:
        return None
    for group, teams in WORLD_CUP_GROUPS.items():
        if resolved in teams:
            return group
    return None


# ============================================================
# 球员影响因子 (关键球员缺席的调整)
# ============================================================
# 可根据实际情况扩展
PLAYER_IMPACT = {
    # 阿根廷
    'Messi': {'team': 'Argentina', 'impact': 0.92},       # 缺席时进攻×0.92
    'Lautaro': {'team': 'Argentina', 'impact': 0.95},
    'Enzo': {'team': 'Argentina', 'impact': 0.97},
    # 法国
    'Mbappe': {'team': 'France', 'impact': 0.90},
    'Griezmann': {'team': 'France', 'impact': 0.94},
    # 英格兰
    'Bellingham': {'team': 'England', 'impact': 0.92},
    'Kane': {'team': 'England', 'impact': 0.93},
    # 巴西
    'Vinicius': {'team': 'Brazil', 'impact': 0.91},
    'Rodrygo': {'team': 'Brazil', 'impact': 0.94},
    # 葡萄牙
    'Ronaldo': {'team': 'Portugal', 'impact': 0.90},
    'Bruno': {'team': 'Portugal', 'impact': 0.94},
    # 可继续添加...
}
