"""
世界杯比赛量化分析引擎

核心模型:
1. Poisson 分布 — 比分预测的基础概率模型
2. Dixon-Coles 简化模型 — 预期进球计算
3. 赔率转换 — 博彩赔率 → 隐含概率 → 去水 → 公允概率
4. 贝叶斯融合 — 模型概率 + 市场概率 → 综合预测

参考文献:
- Dixon & Coles (1997) "Modelling Association Football Scores"
- Maher (1982) "Modelling association football scores"
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from collections import defaultdict

from data import (
    FIFA_RANKINGS, WORLD_AVERAGE_GOALS, WORLD_AVERAGE_FIFA_POINTS,
    LOCATION_FACTORS, HOST_NATIONS, resolve_team,
    ATTACK_EXPONENT, DEFENSE_EXPONENT
)


# ============================================================
# Poisson 分布工具
# ============================================================
def poisson_pmf(k: int, lam: float) -> float:
    """Poisson 概率质量函数 P(X=k)"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def poisson_cmf(k: int, lam: float) -> float:
    """Poisson 累积分布函数 P(X <= k)"""
    return sum(poisson_pmf(i, lam) for i in range(k + 1))


def poisson_sf(k: int, lam: float) -> float:
    """Poisson 生存函数 P(X > k)"""
    return 1.0 - poisson_cmf(k, lam)


# ============================================================
# 球队实力评级
# ============================================================
@dataclass
class TeamStrength:
    """球队攻防实力参数"""
    name: str
    fifa_rank: int
    fifa_points: float
    elo: float = 0.0
    attack: float = 1.0       # 进攻系数 (均值=1.0, 越高越强)
    defense: float = 1.0      # 防守系数 (均值=1.0, 越低越强)
    attack_adj: float = 1.0    # 进攻调整乘数 (伤病等)
    defense_adj: float = 1.0   # 防守调整乘数 (伤病等)

    @property
    def effective_attack(self) -> float:
        """有效进攻系数"""
        return self.attack * self.attack_adj

    @property
    def effective_defense(self) -> float:
        """有效防守系数"""
        return self.defense * self.defense_adj

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'fifa_rank': self.fifa_rank,
            'fifa_points': self.fifa_points,
            'elo': self.elo,
            'attack': round(self.attack, 3),
            'defense': round(self.defense, 3),
            'attack_adj': round(self.attack_adj, 3),
            'defense_adj': round(self.defense_adj, 3),
            'effective_attack': round(self.effective_attack, 3),
            'effective_defense': round(self.effective_defense, 3),
        }


def build_team_strength(team_name: str,
                        attack_adj: float = 1.0,
                        defense_adj: float = 1.0) -> Optional[TeamStrength]:
    """
    从 FIFA 排名构建球队攻防参数

    核心思想:
    - FIFA积分越高的球队, 进攻越强, 防守越好
    - 使用幂函数将积分映射到攻防系数
    - 系数围绕 1.0 分布 (世界均值)
    """
    resolved = resolve_team(team_name)
    if not resolved:
        return None

    data = FIFA_RANKINGS[resolved]
    pts = data['points']
    mean_pts = WORLD_AVERAGE_FIFA_POINTS

    # 攻防系数: 以世界均值为基准的幂律映射
    # attack: 积分高于均值 → >1.0, 低于均值 → <1.0
    # defense: 积分高于均值 → <1.0 (失球少), 低于均值 → >1.0 (失球多)
    attack = (pts / mean_pts) ** ATTACK_EXPONENT
    defense = (mean_pts / pts) ** DEFENSE_EXPONENT

    return TeamStrength(
        name=resolved,
        fifa_rank=data['rank'],
        fifa_points=pts,
        elo=data.get('elo', 0.0),
        attack=attack,
        defense=defense,
        attack_adj=attack_adj,
        defense_adj=defense_adj,
    )


# ============================================================
# 预期进球模型
# ============================================================
def expected_goals(team_attack: float, opponent_defense: float,
                   location_factor: float = 1.0,
                   league_avg: float = WORLD_AVERAGE_GOALS) -> float:
    """
    计算预期进球 λ

    λ = league_avg × attack_i × defense_j × location_factor

    参数:
        team_attack: 进攻方的有效进攻系数
        opponent_defense: 防守方的有效防守系数
        location_factor: 场地因素 (主场/中立/客场)
        league_avg: 联赛平均进球数
    """
    return league_avg * team_attack * opponent_defense * location_factor


# ============================================================
# 比分概率计算
# ============================================================
@dataclass
class ScoreProb:
    """单个比分的概率"""
    home_goals: int
    away_goals: int
    probability: float

    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals

    @property
    def result(self) -> str:
        if self.home_goals > self.away_goals:
            return 'home_win'
        elif self.home_goals == self.away_goals:
            return 'draw'
        else:
            return 'away_win'


@dataclass
class MatchPrediction:
    """比赛预测结果"""
    team_a: str
    team_b: str
    lambda_a: float            # 球队A预期进球
    lambda_b: float            # 球队B预期进球
    prob_a_win: float          # A胜概率
    prob_draw: float           # 平局概率
    prob_b_win: float          # B胜概率
    top_scores: List[ScoreProb]  # 最可能比分 TOP-N
    expected_total_goals: float   # 预期总进球
    over_15_prob: float        # 大于1.5球概率
    over_25_prob: float        # 大于2.5球概率
    over_35_prob: float        # 大于3.5球概率
    btts_prob: float           # 双方进球概率
    most_likely_score: str     # 最可能比分
    exp_a_goals_if_win: float = 0.0   # A胜条件期望进球
    exp_b_goals_if_win: float = 0.0   # B胜条件期望进球 (A的对手进球)
    exp_a_goals_if_lose: float = 0.0  # A负条件期望进球
    exp_b_goals_if_lose: float = 0.0  # B胜条件期望进球 (A的对手进球)
    score_matrix: Optional[Dict] = None  # 完整比分矩阵 (内部使用)
    strength_a: Optional[TeamStrength] = None
    strength_b: Optional[TeamStrength] = None
    odds_analysis: Optional['OddsAnalysis'] = None
    blended_probs: Optional[Dict[str, float]] = None


@dataclass
class OddsAnalysis:
    """赔率分析结果"""
    raw_odds: Dict[str, float]           # 原始赔率
    implied_probs: Dict[str, float]      # 隐含概率 (未去水)
    fair_probs: Dict[str, float]         # 公允概率 (去水后)
    overround: float                     # 抽水率
    value_bets: List[Dict]               # 价值投注


def calculate_score_matrix(lambda_a: float, lambda_b: float,
                           max_goals: int = 8) -> Dict[Tuple[int, int], float]:
    """
    计算完整比分概率矩阵
    P(score_a=x, score_b=y) = Poisson(x|λ_a) × Poisson(y|λ_b)
    假设两队进球相互独立 (简化假设，实践中效果不错)
    """
    matrix = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_pmf(i, lambda_a) * poisson_pmf(j, lambda_b)
            matrix[(i, j)] = prob
    return matrix


def get_top_scores(matrix: Dict[Tuple[int, int], float],
                   n: int = 10) -> List[ScoreProb]:
    """获取概率最高的 N 个比分"""
    sorted_scores = sorted(matrix.items(), key=lambda x: x[1], reverse=True)
    return [
        ScoreProb(home_goals=ga, away_goals=gb, probability=prob)
        for (ga, gb), prob in sorted_scores[:n]
    ]


def calculate_outcome_probs(matrix: Dict[Tuple[int, int], float]) -> Tuple[float, float, float]:
    """从比分矩阵计算胜平负概率"""
    prob_a = 0.0
    prob_draw = 0.0
    prob_b = 0.0

    for (ga, gb), prob in matrix.items():
        if ga > gb:
            prob_a += prob
        elif ga == gb:
            prob_draw += prob
        else:
            prob_b += prob

    return prob_a, prob_draw, prob_b


def calculate_specials(matrix: Dict[Tuple[int, int], float]) -> Dict[str, float]:
    """计算特殊投注项概率"""
    over_15 = 0.0
    over_25 = 0.0
    over_35 = 0.0
    btts = 0.0

    for (ga, gb), prob in matrix.items():
        total = ga + gb
        if total > 1.5:
            over_15 += prob
        if total > 2.5:
            over_25 += prob
        if total > 3.5:
            over_35 += prob
        if ga > 0 and gb > 0:
            btts += prob

    return {
        'over_1.5': over_15,
        'over_2.5': over_25,
        'over_3.5': over_35,
        'btts': btts,
    }


# ============================================================
# 赔率分析
# ============================================================
def analyze_odds(odds_a_win: float, odds_draw: float, odds_b_win: float) -> OddsAnalysis:
    """
    分析博彩赔率

    1. 计算隐含概率: implied = 1/odds
    2. 计算抽水率: overround = sum(implied) - 1
    3. 去除抽水: fair_prob = implied / sum(implied)
    4. 识别价值投注 (与模型概率对比时在后续步骤进行)
    """
    raw_odds = {'home_win': odds_a_win, 'draw': odds_draw, 'away_win': odds_b_win}

    implied = {k: 1.0 / v for k, v in raw_odds.items()}
    overround = sum(implied.values()) - 1.0
    fair = {k: v / sum(implied.values()) for k, v in implied.items()}

    return OddsAnalysis(
        raw_odds=raw_odds,
        implied_probs=implied,
        fair_probs=fair,
        overround=overround,
        value_bets=[],
    )


# ============================================================
# 贝叶斯融合模型
# ============================================================
def blend_probabilities(model_probs: Dict[str, float],
                        market_probs: Dict[str, float],
                        model_weight: float = 0.40) -> Dict[str, float]:
    """
    融合模型概率与市场概率

    P_blended = w × P_model + (1-w) × P_market

    model_weight: 模型权重 (默认0.4, 即40%模型 + 60%市场)
    市场赔率通常更高效, 但模型能捕捉公开数据未反映的因素 (伤病等)
    """
    blended = {}
    for key in model_probs:
        blended[key] = (model_weight * model_probs[key] +
                        (1 - model_weight) * market_probs.get(key, model_probs[key]))
    return blended


# ============================================================
# 价值投注识别
# ============================================================
def find_value_bets(model_probs: Dict[str, float],
                    odds_analysis: OddsAnalysis,
                    threshold: float = 0.05) -> List[Dict]:
    """
    寻找价值投注

    如果模型认为某结果概率 > 赔率隐含的公允概率 + 阈值,
    则认为该投注有价值

    返回: [{outcome, model_prob, market_prob, edge, odds, recommendation}]
    """
    value_bets = []
    key_map = {'home_win': 'home_win', 'draw': 'draw', 'away_win': 'away_win'}

    for key, label in key_map.items():
        model_p = model_probs.get(key, 0)
        market_p = odds_analysis.fair_probs.get(key, 0)
        edge = model_p - market_p

        if edge > threshold:
            value_bets.append({
                'outcome': label,
                'model_prob': model_p,
                'market_prob': market_p,
                'edge': edge,
                'odds': odds_analysis.raw_odds[key],
                'recommendation': 'VALUE' if edge > 0.1 else 'LIGHT VALUE',
            })

    return sorted(value_bets, key=lambda x: x['edge'], reverse=True)


# ============================================================
# 主预测函数
# ============================================================
def predict_match(
    team_a: str,
    team_b: str,
    location: str = 'neutral',
    odds_a: Optional[float] = None,
    odds_draw: Optional[float] = None,
    odds_b: Optional[float] = None,
    a_attack_adj: float = 1.0,
    a_defense_adj: float = 1.0,
    b_attack_adj: float = 1.0,
    b_defense_adj: float = 1.0,
    model_weight: float = 0.40,
    max_goals: int = 8,
) -> MatchPrediction:
    """
    预测一场比赛

    参数:
        team_a: 球队A名称
        team_b: 球队B名称
        location: 'home' | 'neutral' | 'away' (从A的视角)
        odds_a, odds_draw, odds_b: 欧洲盘赔率 (胜/平/负, 可选)
        a_attack_adj, a_defense_adj: A队进攻/防守调整 (如主力缺席则<1.0)
        b_attack_adj, b_defense_adj: B队进攻/防守调整
        model_weight: 模型权重 (0-1), 仅当提供赔率时起作用
        max_goals: 比分矩阵的最大进球数
    """
    # 1. 构建球队实力
    strength_a = build_team_strength(team_a, a_attack_adj, a_defense_adj)
    strength_b = build_team_strength(team_b, b_attack_adj, b_defense_adj)

    if not strength_a:
        raise ValueError(f"未找到球队: {team_a}")
    if not strength_b:
        raise ValueError(f"未找到球队: {team_b}")

    # 2. 确定场地因素
    if location == 'home':
        loc_factor_a = LOCATION_FACTORS['home']
        loc_factor_b = LOCATION_FACTORS['away']
    elif location == 'away':
        loc_factor_a = LOCATION_FACTORS['away']
        loc_factor_b = LOCATION_FACTORS['home']
    else:  # neutral
        # 如果某队是主办国且在中立场地, 依然有轻微主场优势
        is_a_host = strength_a.name in HOST_NATIONS
        is_b_host = strength_b.name in HOST_NATIONS

        if is_a_host and not is_b_host:
            loc_factor_a = 1.10
            loc_factor_b = 0.92
        elif is_b_host and not is_a_host:
            loc_factor_a = 0.92
            loc_factor_b = 1.10
        else:
            loc_factor_a = 1.0
            loc_factor_b = 1.0

    # 3. 计算预期进球
    lambda_a = expected_goals(strength_a.effective_attack,
                              strength_b.effective_defense,
                              loc_factor_a)
    lambda_b = expected_goals(strength_b.effective_attack,
                              strength_a.effective_defense,
                              loc_factor_b)

    # 4. 计算比分概率矩阵
    score_matrix = calculate_score_matrix(lambda_a, lambda_b, max_goals)

    # 5. 计算胜平负概率
    prob_a_win, prob_draw, prob_b_win = calculate_outcome_probs(score_matrix)

    # 6. 最可能比分
    top_scores = get_top_scores(score_matrix, n=10)
    most_likely = f"{top_scores[0].home_goals}-{top_scores[0].away_goals}"

    # 6.5 计算条件期望比分 (若A胜/若B胜)
    exp_a_win = 0.0
    exp_a_win_concede = 0.0
    exp_b_win = 0.0
    exp_b_win_concede = 0.0
    total_a_win_prob = 0.0
    total_b_win_prob = 0.0

    for (ga, gb), prob in score_matrix.items():
        if ga > gb:
            exp_a_win += ga * prob
            exp_a_win_concede += gb * prob
            total_a_win_prob += prob
        elif gb > ga:
            exp_b_win_concede += ga * prob
            exp_b_win += gb * prob
            total_b_win_prob += prob

    # 条件期望 = 联合期望 / 条件概率
    if total_a_win_prob > 0:
        exp_a_goals_if_win = exp_a_win / total_a_win_prob
        exp_b_goals_if_win = exp_a_win_concede / total_a_win_prob
    else:
        exp_a_goals_if_win = lambda_a
        exp_b_goals_if_win = 0.0

    if total_b_win_prob > 0:
        exp_a_goals_if_lose = exp_b_win_concede / total_b_win_prob
        exp_b_goals_if_lose = exp_b_win / total_b_win_prob
    else:
        exp_a_goals_if_lose = 0.0
        exp_b_goals_if_lose = lambda_b

    # 7. 特殊项概率
    specials = calculate_specials(score_matrix)

    # 8. 预期总进球
    expected_total = lambda_a + lambda_b

    # 9. 构造基础预测
    prediction = MatchPrediction(
        team_a=strength_a.name,
        team_b=strength_b.name,
        lambda_a=lambda_a,
        lambda_b=lambda_b,
        prob_a_win=prob_a_win,
        prob_draw=prob_draw,
        prob_b_win=prob_b_win,
        top_scores=top_scores,
        expected_total_goals=expected_total,
        over_15_prob=specials['over_1.5'],
        over_25_prob=specials['over_2.5'],
        over_35_prob=specials['over_3.5'],
        btts_prob=specials['btts'],
        most_likely_score=most_likely,
        exp_a_goals_if_win=exp_a_goals_if_win,
        exp_b_goals_if_win=exp_b_goals_if_win,
        exp_a_goals_if_lose=exp_a_goals_if_lose,
        exp_b_goals_if_lose=exp_b_goals_if_lose,
        score_matrix=score_matrix,
        strength_a=strength_a,
        strength_b=strength_b,
    )

    # 10. 赔率分析 (如果提供)
    if odds_a and odds_draw and odds_b:
        odds_analysis = analyze_odds(odds_a, odds_draw, odds_b)
        prediction.odds_analysis = odds_analysis

        # 映射: prediction中的prob是A/B视角, odds是home/away视角 (home=A, away=B)
        # 因为输入时 odds_a = A胜, odds_draw = 平, odds_b = B胜
        model_probs = {
            'home_win': prob_a_win,
            'draw': prob_draw,
            'away_win': prob_b_win,
        }

        # 贝叶斯融合
        blended = blend_probabilities(model_probs, odds_analysis.fair_probs, model_weight)
        prediction.blended_probs = blended

        # 价值投注识别
        value_bets = find_value_bets(model_probs, odds_analysis)
        odds_analysis.value_bets = value_bets

    return prediction


# ============================================================
# 蒙特卡洛模拟 (可选备用方法)
# ============================================================
def monte_carlo_simulation(lambda_a: float, lambda_b: float,
                           n_simulations: int = 100000) -> Dict:
    """
    蒙特卡洛模拟比赛结果

    与解析Poisson方法互为验证
    """
    import random
    random.seed(42)

    results = {'home_win': 0, 'draw': 0, 'away_win': 0}
    scores = defaultdict(int)

    # 预计算累积分布以加速采样
    def poisson_cdf_table(lam: float, max_k: int = 15) -> List[float]:
        cdf = []
        cum = 0.0
        for k in range(max_k + 1):
            cum += poisson_pmf(k, lam)
            cdf.append(cum)
        return cdf

    def sample_poisson(cdf: List[float]) -> int:
        r = random.random()
        for k, cum in enumerate(cdf):
            if r <= cum:
                return k
        return len(cdf) - 1

    cdf_a = poisson_cdf_table(lambda_a)
    cdf_b = poisson_cdf_table(lambda_b)

    for _ in range(n_simulations):
        ga = sample_poisson(cdf_a)
        gb = sample_poisson(cdf_b)
        scores[(ga, gb)] += 1

        if ga > gb:
            results['home_win'] += 1
        elif ga == gb:
            results['draw'] += 1
        else:
            results['away_win'] += 1

    n = n_simulations
    return {
        'home_win': results['home_win'] / n,
        'draw': results['draw'] / n,
        'away_win': results['away_win'] / n,
        'top_scores': sorted(
            [{'score': f"{ga}-{gb}", 'prob': count / n}
             for (ga, gb), count in scores.items()],
            key=lambda x: x['prob'], reverse=True
        )[:10],
        'n_simulations': n,
    }
