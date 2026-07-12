[file name]: ai_engines.py
[file content begin]
# ai_engines.py
import numpy as np
import time
import random

# ==========================================================
# 🌟 Premium Emojis for AI Messages
# ==========================================================
P_AI_CHECK = '<tg-emoji emoji-id="5807868868886009920">✅</tg-emoji>'
P_AI_CROSS = '<tg-emoji emoji-id="5807461353799030682">❌</tg-emoji>'
P_AI_INFO = '<tg-emoji emoji-id="5877443460725739250">ℹ️</tg-emoji>'
P_AI_HOURGLASS = '<tg-emoji emoji-id="5890997763331591703">⏳</tg-emoji>'
P_AI_UP = '<tg-emoji emoji-id="5967574255670399788">⬆️</tg-emoji>'
P_AI_DOWN = '<tg-emoji emoji-id="5875180111744995604">⬇️</tg-emoji>'
P_AI_LEFT_RIGHT = '<tg-emoji emoji-id="5848119413041431362">↔️</tg-emoji>'
P_AI_SPARKLES = '<tg-emoji emoji-id="5884289942371401145">✨</tg-emoji>'
P_AI_PATTERN = '<tg-emoji emoji-id="5868656545634689320">🎯</tg-emoji>'
P_AI_MARTINGALE = '<tg-emoji emoji-id="5868108575387671725">🎲</tg-emoji>'
P_AI_ANTIMARTINGALE = '<tg-emoji emoji-id="5868665489092263539">🔄</tg-emoji>'
P_AI_TREND = '<tg-emoji emoji-id="5877652234091891383">📊</tg-emoji>'
P_AI_FIBONACCI = '<tg-emoji emoji-id="5877260593903177342">🔢</tg-emoji>'
P_AI_GOLDEN = '<tg-emoji emoji-id="5869547610204280761">🎯</tg-emoji>'
P_AI_MOMENTUM = '<tg-emoji emoji-id="5884248697980608904">📈</tg-emoji>'
P_AI_MONTECARLO = '<tg-emoji emoji-id="5884041323843955199">🎲</tg-emoji>'
P_AI_NEURAL = '<tg-emoji emoji-id="5875180111744995604">🧬</tg-emoji>'
P_AI_REVERSAL = '<tg-emoji emoji-id="5890997763331591703">⚡</tg-emoji>'
P_AI_WAVE = '<tg-emoji emoji-id="5967574255670399788">🌊</tg-emoji>'
P_AI_CHAOS = '<tg-emoji emoji-id="5877443460725739250">🎪</tg-emoji>'
P_AI_CHART_UP = '<tg-emoji emoji-id="5884248697980608904">📈</tg-emoji>'
P_AI_CHART_DOWN = '<tg-emoji emoji-id="5884289942371401145">📉</tg-emoji>'
P_AI_STAR = '<tg-emoji emoji-id="5807868868886009920">⭐</tg-emoji>'
P_AI_ROBOT = '<tg-emoji emoji-id="5877652234091891383">🤖</tg-emoji>'
P_AI_BRAIN = '<tg-emoji emoji-id="5868656545634689320">🧠</tg-emoji>'

class AIEmoji:
    CHECK = "✅"; CROSS = "❌"; INFO = "ℹ️"; HOURGLASS = "⏳"
    UP = "⬆️"; DOWN = "⬇️"; LEFT_RIGHT = "↔️"; SPARKLES = "✨"
    PATTERN = "🎯"; MARTINGALE = "🎲"; ANTIMARTINGALE = "🔄"
    TREND = "📊"; FIBONACCI = "🔢"; GOLDEN = "🎯"; MOMENTUM = "📈"
    MONTECARLO = "🎲"; NEURAL = "🧬"; REVERSAL = "⚡"; WAVE = "🌊"; CHAOS = "🎪"
    CHART_UP = "📈"; CHART_DOWN = "📉"; STAR = "⭐"
    ROBOT = "🤖"; BRAIN = "🧠"

# ==========================================
# 1. PATTERN AI (9 Patterns Only)
# ==========================================
def detect_active_pattern(history_list):
    if len(history_list) < 4:
        return None, None
    
    patterns = [
        ("BBSS", ["BIG", "BIG", "SMALL", "SMALL"]),
        ("BBS", ["BIG", "BIG", "SMALL"]),
        ("BSS", ["BIG", "SMALL", "SMALL"]),
        ("BSBS", ["BIG", "SMALL", "BIG", "SMALL"]),
        ("SBSB", ["SMALL", "BIG", "SMALL", "BIG"]),
        ("BSB", ["BIG", "SMALL", "BIG"]),
        ("SBS", ["SMALL", "BIG", "SMALL"]),
        ("BBB", ["BIG", "BIG", "BIG"]),
        ("SSS", ["SMALL", "SMALL", "SMALL"]),
    ]
    
    recent = history_list[-15:]
    best_pattern, best_score, best_next = None, 0, None
    
    for name, seq in patterns:
        plen = len(seq)
        matches = sum(1 for i in range(len(recent) - plen + 1) if recent[i:i+plen] == seq)
        
        if matches >= 2:
            next_map = {
                "BBSS": "BIG", "BBS": "BIG", "BSS": "BIG",
                "BSBS": "BIG", "SBSB": "SMALL",
                "BSB": "BIG", "SBS": "SMALL",
                "BBB": "BIG", "SSS": "SMALL",
            }
            nxt = next_map.get(name, "BIG")
            score = matches * plen
            
            if score > best_score:
                best_score, best_pattern, best_next = score, name, nxt
    
    return best_pattern, best_next


def pattern_predict(history_docs):
    if len(history_docs) < 10:
        return "BIG", f"{P_AI_PATTERN} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Pattern: Data စုဆောင်းဆဲ..."
    
    docs = list(reversed(history_docs))
    all_history = [d.get('size', 'BIG') for d in docs]
    
    active_pattern, next_pred = detect_active_pattern(all_history)
    
    if active_pattern:
        if next_pred == "BIG":
            return "BIG", f"{P_AI_PATTERN} BIG (အကြီး) 🔴", 75.0, f"{P_AI_PATTERN} Pattern: {active_pattern} {P_AI_UP} BIG"
        else:
            return "SMALL", f"{P_AI_PATTERN} SMALL (အသေး) 🟢", 75.0, f"{P_AI_PATTERN} Pattern: {active_pattern} {P_AI_DOWN} SMALL"
    else:
        b = all_history.count("BIG")
        s = all_history.count("SMALL")
        if b > s:
            return "BIG", f"{P_AI_PATTERN} BIG (အကြီး) 🔴", 55.0, f"{P_AI_INFO} Majority BIG ({b}:{s})"
        else:
            return "SMALL", f"{P_AI_PATTERN} SMALL (အသေး) 🟢", 55.0, f"{P_AI_INFO} Majority SMALL ({b}:{s})"

# ========== 2. MARTINGALE AI ==========
def martingale_predict(history_docs):
    if len(history_docs) < 5: 
        return "BIG", f"{P_AI_MARTINGALE} BIG (အကြီး) 🔴", 60.0, f"{P_AI_HOURGLASS} Martingale: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    recent_10 = all_history[-10:]; big = recent_10.count("BIG"); small = recent_10.count("SMALL")
    if big > small: 
        return "SMALL", f"{P_AI_MARTINGALE} SMALL (အသေး) 🟢", 65.0, f"{P_AI_MARTINGALE} Contrarian BIG:{big} SMALL:{small}"
    else: 
        return "BIG", f"{P_AI_MARTINGALE} BIG (အကြီး) 🔴", 65.0, f"{P_AI_MARTINGALE} Contrarian BIG:{big} SMALL:{small}"

# ========== 3. ANTI-MARTINGALE AI ==========
def anti_martingale_predict(history_docs):
    if len(history_docs) < 5: 
        return "BIG", f"{P_AI_ANTIMARTINGALE} BIG (အကြီး) 🔴", 60.0, f"{P_AI_HOURGLASS} Anti-Martingale: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    recent_5 = all_history[-5:]; big_streak = small_streak = 0
    for r in reversed(recent_5):
        if r == "BIG": big_streak += 1; small_streak = 0
        else: small_streak += 1; big_streak = 0
    if big_streak >= 2: 
        return "BIG", f"{P_AI_ANTIMARTINGALE} BIG (အကြီး) 🔴", 70.0, f"{P_AI_ANTIMARTINGALE} BIG streak {big_streak}"
    elif small_streak >= 2: 
        return "SMALL", f"{P_AI_ANTIMARTINGALE} SMALL (အသေး) 🟢", 70.0, f"{P_AI_ANTIMARTINGALE} SMALL streak {small_streak}"
    else:
        last = all_history[-1] if all_history else "BIG"; emoji = "🔴" if last == "BIG" else "🟢"
        return last, f"{P_AI_ANTIMARTINGALE} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 60.0, f"{P_AI_ANTIMARTINGALE} Follow last"

# ========== 4. TREND FOLLOWING AI ==========
def trend_following_predict(history_docs):
    if len(history_docs) < 8: 
        return "BIG", f"{P_AI_TREND} BIG (အကြီး) 🔴", 58.0, f"{P_AI_HOURGLASS} Trend: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    big_8 = all_history[-8:].count("BIG") / 8; big_4 = all_history[-4:].count("BIG") / 4; trend = big_4 - big_8
    if trend > 0.1: 
        return "BIG", f"{P_AI_TREND} BIG (အကြီး) 🔴", 72.0, f"{P_AI_TREND} BIG +{trend*100:.0f}%"
    elif trend < -0.1: 
        return "SMALL", f"{P_AI_TREND} SMALL (အသေး) 🟢", 72.0, f"{P_AI_TREND} SMALL +{abs(trend)*100:.0f}%"
    else:
        last = all_history[-1]; emoji = "🔴" if last == "BIG" else "🟢"
        return last, f"{P_AI_TREND} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 60.0, f"{P_AI_TREND} Sideways"

# ========== 5. FIBONACCI AI ==========
def fibonacci_predict(history_docs):
    if len(history_docs) < 10: 
        return "BIG", f"{P_AI_FIBONACCI} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Fibonacci: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    fib_levels = [3, 5, 8, 13, 21]; results = []
    for level in fib_levels:
        if len(all_history) >= level:
            segment = all_history[-level:]; big_pct = segment.count("BIG") / level
            if 0.38 <= big_pct <= 0.62: results.append("BIG" if big_pct < 0.5 else "SMALL")
            elif big_pct > 0.618: results.append("SMALL")
            else: results.append("BIG")
    if results:
        final = max(set(results), key=results.count); emoji = "🔴" if final == "BIG" else "🟢"
        return final, f"{P_AI_FIBONACCI} {final} ({'အကြီး' if final == 'BIG' else 'အသေး'}) {emoji}", 68.0, f"{P_AI_FIBONACCI} {len(results)} levels"
    return "BIG", f"{P_AI_FIBONACCI} BIG (အကြီး) 🔴", 55.0, f"{P_AI_FIBONACCI} Default"

# ========== 6. GOLDEN RATIO AI ==========
def golden_ratio_predict(history_docs):
    if len(history_docs) < 12: 
        return "BIG", f"{P_AI_GOLDEN} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Golden Ratio: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    lookback = min(21, len(all_history)); big_ratio = all_history[-lookback:].count("BIG") / lookback
    if big_ratio > 0.618: 
        return "SMALL", f"{P_AI_GOLDEN} SMALL (အသေး) 🟢", 70.0, f"{P_AI_GOLDEN} {big_ratio*100:.1f}% > 61.8% {P_AI_DOWN}"
    elif big_ratio < 0.382: 
        return "BIG", f"{P_AI_GOLDEN} BIG (အကြီး) 🔴", 70.0, f"{P_AI_GOLDEN} {big_ratio*100:.1f}% < 38.2% {P_AI_UP}"
    else:
        last = all_history[-1]; emoji = "🔴" if last == "BIG" else "🟢"
        return last, f"{P_AI_GOLDEN} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 65.0, f"{P_AI_GOLDEN} Zone: {big_ratio*100:.1f}%"

# ========== 7. MOMENTUM AI ==========
def momentum_predict(history_docs):
    if len(history_docs) < 6: 
        return "BIG", f"{P_AI_MOMENTUM} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Momentum: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    score = 0; weights = [5, 4, 3, 2, 1]
    for i, r in enumerate(all_history[-5:]):
        if r == "BIG": score += weights[i]
        else: score -= weights[i]
    if score > 3: 
        return "BIG", f"{P_AI_MOMENTUM} BIG (အကြီး) 🔴", 73.0, f"{P_AI_MOMENTUM} Strong BIG (+{score})"
    elif score < -3: 
        return "SMALL", f"{P_AI_MOMENTUM} SMALL (အသေး) 🟢", 73.0, f"{P_AI_MOMENTUM} Strong SMALL ({score})"
    else:
        last = all_history[-1]; emoji = "🔴" if last == "BIG" else "🟢"
        return last, f"{P_AI_MOMENTUM} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 58.0, f"{P_AI_MOMENTUM} Weak: {score}"

# ========== 8. MONTE CARLO AI ==========
def monte_carlo_predict(history_docs):
    if len(history_docs) < 15: 
        return "BIG", f"{P_AI_MONTECARLO} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Monte Carlo: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    np.random.seed(int(time.time())); big_prob = all_history.count("BIG") / len(all_history)
    big_wins = sum(1 for _ in range(1000) if np.random.choice(["BIG", "SMALL"], p=[big_prob, 1-big_prob]) == "BIG")
    if big_wins > 500:
        prob = (big_wins / 1000) * 100; return "BIG", f"{P_AI_MONTECARLO} BIG (အကြီး) 🔴", min(prob, 80), f"{P_AI_MONTECARLO} BIG {prob:.1f}%"
    else:
        prob = ((1000 - big_wins) / 1000) * 100; return "SMALL", f"{P_AI_MONTECARLO} SMALL (အသေး) 🟢", min(prob, 80), f"{P_AI_MONTECARLO} SMALL {prob:.1f}%"

# ========== 9. NEURAL PATTERN AI ==========
def neural_pattern_predict(history_docs):
    if len(history_docs) < 8: 
        return "BIG", f"{P_AI_NEURAL} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Neural: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    features = []
    for i in range(3, len(all_history)):
        window = all_history[i-3:i]; features.append({"big_ratio": window.count("BIG") / 3, "next": all_history[i]})
    current_ratio = all_history[-3:].count("BIG") / 3; similar_big = similar_small = 0
    for f in features:
        if abs(f["big_ratio"] - current_ratio) < 0.1:
            if f["next"] == "BIG": similar_big += 1
            else: similar_small += 1
    total = similar_big + similar_small
    if total > 0:
        big_prob = (similar_big / total) * 100
        if big_prob > 50: 
            return "BIG", f"{P_AI_NEURAL} BIG (အကြီး) 🔴", min(big_prob + 10, 85), f"{P_AI_NEURAL} {total} patterns BIG {big_prob:.0f}%"
        else: 
            return "SMALL", f"{P_AI_NEURAL} SMALL (အသေး) 🟢", min((100-big_prob) + 10, 85), f"{P_AI_NEURAL} {total} patterns SMALL {100-big_prob:.0f}%"
    return "BIG", f"{P_AI_NEURAL} BIG (အကြီး) 🔴", 55.0, f"{P_AI_NEURAL} No similar patterns"

# ========== 10. QUICK REVERSAL AI ==========
def quick_reversal_predict(history_docs):
    if len(history_docs) < 5: 
        return "BIG", f"{P_AI_REVERSAL} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Reversal: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    recent_5 = all_history[-5:]; alts = sum(1 for i in range(1, len(recent_5)) if recent_5[i] != recent_5[i-1])
    alt_rate = alts / (len(recent_5) - 1)
    if alt_rate > 0.75:
        last = recent_5[-1]; predicted = "SMALL" if last == "BIG" else "BIG"
        emoji = "🔴" if predicted == "BIG" else "🟢"
        return predicted, f"{P_AI_REVERSAL} {predicted} ({'အကြီး' if predicted == 'BIG' else 'အသေး'}) {emoji}", 72.0, f"{P_AI_REVERSAL} Alt {alt_rate*100:.0f}%"
    else:
        last = recent_5[-1]; emoji = "🔴" if last == "BIG" else "🟢"
        return last, f"{P_AI_REVERSAL} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 60.0, f"{P_AI_REVERSAL} Alt {alt_rate*100:.0f}%"

# ========== 11. WAVE ANALYSIS AI ==========
def wave_analysis_predict(history_docs):
    if len(history_docs) < 8: 
        return "BIG", f"{P_AI_WAVE} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Wave: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    waves = []; current = all_history[0]; count = 1
    for r in all_history[1:]:
        if r == current: count += 1
        else: waves.append((current, count)); current = r; count = 1
    waves.append((current, count))
    if len(waves) >= 3:
        last_wave = waves[-1]; prev_wave = waves[-2]
        if last_wave[1] >= 3 and prev_wave[0] != last_wave[0]:
            emoji = "🔴" if last_wave[0] == "BIG" else "🟢"
            return last_wave[0], f"{P_AI_WAVE} {last_wave[0]} ({'အကြီး' if last_wave[0] == 'BIG' else 'အသေး'}) {emoji}", 70.0, f"{P_AI_WAVE} Impulse {last_wave[1]}"
        elif last_wave[1] <= 2:
            predicted = "SMALL" if last_wave[0] == "BIG" else "BIG"
            emoji = "🔴" if predicted == "BIG" else "🟢"
            return predicted, f"{P_AI_WAVE} {predicted} ({'အကြီး' if predicted == 'BIG' else 'အသေး'}) {emoji}", 68.0, f"{P_AI_WAVE} Correction"
    last = all_history[-1]; emoji = "🔴" if last == "BIG" else "🟢"
    return last, f"{P_AI_WAVE} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 58.0, f"{P_AI_WAVE} Default"

# ========== 12. CHAOS THEORY AI ==========
def chaos_theory_predict(history_docs):
    if len(history_docs) < 10: 
        return "BIG", f"{P_AI_CHAOS} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Chaos: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    def entropy(seg):
        total = len(seg); big_p = seg.count("BIG") / total; small_p = seg.count("SMALL") / total
        e = 0
        for p in [big_p, small_p]:
            if p > 0: e -= p * np.log2(p)
        return e
    e3 = entropy(all_history[-3:]); e5 = entropy(all_history[-5:]); e10 = entropy(all_history[-10:])
    if e3 > e5 > e10:
        last = all_history[-3:][-1]; predicted = "SMALL" if last == "BIG" else "BIG"
        emoji = "🔴" if predicted == "BIG" else "🟢"
        return predicted, f"{P_AI_CHAOS} {predicted} ({'အကြီး' if predicted == 'BIG' else 'အသေး'}) {emoji}", 67.0, f"{P_AI_CHAOS} Entropy {P_AI_LEFT_RIGHT}"
    elif e3 < e5:
        majority = "BIG" if all_history[-5:].count("BIG") > all_history[-5:].count("SMALL") else "SMALL"
        emoji = "🔴" if majority == "BIG" else "🟢"
        return majority, f"{P_AI_CHAOS} {majority} ({'အကြီး' if majority == 'BIG' else 'အသေး'}) {emoji}", 65.0, f"{P_AI_CHAOS} Pattern {P_AI_SPARKLES}"
    last = all_history[-1]; emoji = "🔴" if last == "BIG" else "🟢"
    return last, f"{P_AI_CHAOS} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 55.0, f"{P_AI_CHAOS} Stable"

# ========== 13. ENSEMBLE AI ==========
def ensemble_predict(history_docs):
    if len(history_docs) < 10: 
        return "BIG", f"{P_AI_ROBOT} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Ensemble: Data စုဆောင်းဆဲ..."
    predictors = [pattern_predict, martingale_predict, anti_martingale_predict, trend_following_predict, fibonacci_predict, golden_ratio_predict, momentum_predict, monte_carlo_predict, neural_pattern_predict, quick_reversal_predict, wave_analysis_predict, chaos_theory_predict]
    predictions = []
    for predictor in predictors:
        try:
            size, _, prob, _ = predictor(history_docs); predictions.append((size, prob))
        except: pass
    if not predictions: 
        return "BIG", f"{P_AI_ROBOT} BIG (အကြီး) 🔴", 55.0, f"{P_AI_ROBOT} Ensemble: Error"
    big_votes = sum(1 for p in predictions if p[0] == "BIG"); small_votes = sum(1 for p in predictions if p[0] == "SMALL")
    total = big_votes + small_votes
    if big_votes > small_votes:
        confidence = (big_votes / total) * 100; return "BIG", f"{P_AI_ROBOT} BIG (အကြီး) 🔴", min(confidence + 10, 90), f"{P_AI_ROBOT} Ensemble: {big_votes}/{total} votes BIG ({confidence:.0f}%)"
    else:
        confidence = (small_votes / total) * 100; return "SMALL", f"{P_AI_ROBOT} SMALL (အသေး) 🟢", min(confidence + 10, 90), f"{P_AI_ROBOT} Ensemble: {small_votes}/{total} votes SMALL ({confidence:.0f}%)"

# ========== 14. BAYESIAN AI ==========
def bayesian_predict(history_docs):
    if len(history_docs) < 10: 
        return "BIG", f"{P_AI_BRAIN} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Bayesian: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    recent = all_history[-20:]; big_after_big = small_after_small = 0; big_total = small_total = 0
    for i in range(1, len(recent)):
        if recent[i-1] == "BIG": big_total += 1
        else: small_total += 1
    for i in range(1, len(recent)):
        if recent[i-1] == "BIG" and recent[i] == "BIG": big_after_big += 1
        elif recent[i-1] == "SMALL" and recent[i] == "SMALL": small_after_small += 1
    p_big_after_big = big_after_big / big_total if big_total > 0 else 0.5
    p_small_after_small = small_after_small / small_total if small_total > 0 else 0.5
    last = recent[-1]
    if last == "BIG":
        if p_big_after_big > 0.5: 
            return "BIG", f"{P_AI_BRAIN} BIG (အကြီး) 🔴", min(p_big_after_big * 100 + 15, 80), f"{P_AI_BRAIN} Bayesian: P(BIG|BIG)={p_big_after_big*100:.0f}%"
        else: 
            return "SMALL", f"{P_AI_BRAIN} SMALL (အသေး) 🟢", min((1-p_big_after_big) * 100 + 15, 80), f"{P_AI_BRAIN} Bayesian: P(SMALL|BIG)={(1-p_big_after_big)*100:.0f}%"
    else:
        if p_small_after_small > 0.5: 
            return "SMALL", f"{P_AI_BRAIN} SMALL (အသေး) 🟢", min(p_small_after_small * 100 + 15, 80), f"{P_AI_BRAIN} Bayesian: P(SMALL|SMALL)={p_small_after_small*100:.0f}%"
        else: 
            return "BIG", f"{P_AI_BRAIN} BIG (အကြီး) 🔴", min((1-p_small_after_small) * 100 + 15, 80), f"{P_AI_BRAIN} Bayesian: P(BIG|SMALL)={(1-p_small_after_small)*100:.0f}%"

# ========== 15. MARKOV CHAIN AI ==========
def markov_chain_predict(history_docs):
    if len(history_docs) < 8: 
        return "BIG", f"{P_AI_INFO} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} Markov: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    transitions = {}
    for i in range(2, len(all_history)):
        state = (all_history[i-2], all_history[i-1]); next_val = all_history[i]
        if state not in transitions: transitions[state] = {"BIG": 0, "SMALL": 0}
        transitions[state][next_val] += 1
    current_state = (all_history[-2], all_history[-1])
    if current_state in transitions:
        counts = transitions[current_state]; total = counts["BIG"] + counts["SMALL"]
        if total > 0:
            big_prob = (counts["BIG"] / total) * 100
            if big_prob > 50: 
                return "BIG", f"{P_AI_INFO} BIG (အကြီး) 🔴", min(big_prob + 10, 82), f"{P_AI_INFO} Markov: {current_state} → BIG {big_prob:.0f}%"
            else: 
                return "SMALL", f"{P_AI_INFO} SMALL (အသေး) 🟢", min((100-big_prob) + 10, 82), f"{P_AI_INFO} Markov: {current_state} → SMALL {100-big_prob:.0f}%"
    last = all_history[-1]; emoji = "🔴" if last == "BIG" else "🟢"
    return last, f"{P_AI_INFO} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 58.0, f"{P_AI_INFO} Markov: 1st order"

# ========== 16. ML STYLE AI ==========
def ml_style_predict(history_docs):
    if len(history_docs) < 12: 
        return "BIG", f"{P_AI_SPARKLES} BIG (အကြီး) 🔴", 55.0, f"{P_AI_HOURGLASS} ML Style: Data စုဆောင်းဆဲ..."
    docs = list(reversed(history_docs)); all_history = [d.get('size', 'BIG') for d in docs]
    recent = all_history[-12:]
    features = {
        "last_3_big_ratio": recent[-3:].count("BIG") / 3,
        "last_5_big_ratio": recent[-5:].count("BIG") / 5,
        "last_8_big_ratio": recent[-8:].count("BIG") / 8,
        "trend": recent[-4:].count("BIG") / 4 - recent[-8:].count("BIG") / 8,
    }
    score = 0
    score += (features["last_3_big_ratio"] - 0.5) * 0.4
    score += (features["last_5_big_ratio"] - 0.5) * 0.3
    score += (features["last_8_big_ratio"] - 0.5) * 0.2
    score += features["trend"] * 0.1
    if score > 0.05: 
        return "BIG", f"{P_AI_SPARKLES} BIG (အကြီး) 🔴", min(55 + abs(score) * 100, 78), f"{P_AI_SPARKLES} ML Style: Score +{score:.3f} → BIG"
    elif score < -0.05: 
        return "SMALL", f"{P_AI_SPARKLES} SMALL (အသေး) 🟢", min(55 + abs(score) * 100, 78), f"{P_AI_SPARKLES} ML Style: Score {score:.3f} → SMALL"
    else:
        last = recent[-1]; emoji = "🔴" if last == "BIG" else "🟢"
        return last, f"{P_AI_SPARKLES} {last} ({'အကြီး' if last == 'BIG' else 'အသေး'}) {emoji}", 55.0, f"{P_AI_SPARKLES} ML Style: Neutral {score:.3f}"

# ========== 17. CIRCLE RND AI (Wheel Spinner) ==========
def circle_rnd_predict(history_docs):
    # စက်ဝိုင်းထဲတွင် ပါဝင်မည့် အကွက်များ
    wheel = ["BIG", "SMALL", "BIG", "SMALL", "BIG", "SMALL", "BIG", "SMALL"]
    
    # Random လှည့်ပြီး တစ်ခုကို ရွေးချယ်ခြင်း
    predicted = random.choice(wheel)
    
    emoji = "🔴" if predicted == "BIG" else "🟢"
    
    # 50/50 ကံစမ်းတာဖြစ်လို့ Confidence ကို 50% ဝန်းကျင် Random ပြပေးပါမည်
    confidence = round(random.uniform(50.0, 65.0), 1)
    
    return predicted, f"{P_AI_STAR} {predicted} ({'အကြီး' if predicted == 'BIG' else 'အသေး'}) {emoji}", confidence, f"🎡 Circle Rnd: Spinner"

# ========== AI MODES DICTIONARY ==========
# ✅ AI Mode Names with Emojis (For Reply Keyboard)
AI_MODE_NAMES = {
    "pattern": "🎯 Pattern AI",
    "martingale": "🎲 Martingale AI",
    "anti_martingale": "🔄 Anti-Martingale AI",
    "trend_following": "📊 Trend Following",
    "fibonacci": "🔢 Fibonacci AI",
    "golden_ratio": "🎯 Golden Ratio",
    "momentum": "📈 Momentum AI",
    "monte_carlo": "🎲 Monte Carlo",
    "neural_pattern": "🧬 Neural Pattern",
    "quick_reversal": "⚡ Quick Reversal",
    "wave_analysis": "🌊 Wave Analysis",
    "chaos_theory": "🎪 Chaos Theory",
    "ensemble": "🤖 Ensemble AI",
    "bayesian": "📐 Bayesian AI",
    "markov_chain": "🔗 Markov Chain",
    "ml_style": "🧪 ML Style AI",
    "circle_rnd": "🎡 Circle Rnd",
}

AI_MODES = {
    "pattern": {"func": pattern_predict, "name": AI_MODE_NAMES["pattern"], "desc": "Pattern Auto-Switch"},
    "martingale": {"func": martingale_predict, "name": AI_MODE_NAMES["martingale"], "desc": "Contrarian Strategy"},
    "anti_martingale": {"func": anti_martingale_predict, "name": AI_MODE_NAMES["anti_martingale"], "desc": "Trend Follow"},
    "trend_following": {"func": trend_following_predict, "name": AI_MODE_NAMES["trend_following"], "desc": "MA Trend Analysis"},
    "fibonacci": {"func": fibonacci_predict, "name": AI_MODE_NAMES["fibonacci"], "desc": "Fib Retracement"},
    "golden_ratio": {"func": golden_ratio_predict, "name": AI_MODE_NAMES["golden_ratio"], "desc": "61.8% Rule"},
    "momentum": {"func": momentum_predict, "name": AI_MODE_NAMES["momentum"], "desc": "Weighted Momentum"},
    "monte_carlo": {"func": monte_carlo_predict, "name": AI_MODE_NAMES["monte_carlo"], "desc": "1000x Simulation"},
    "neural_pattern": {"func": neural_pattern_predict, "name": AI_MODE_NAMES["neural_pattern"], "desc": "Pattern Similarity"},
    "quick_reversal": {"func": quick_reversal_predict, "name": AI_MODE_NAMES["quick_reversal"], "desc": "Alternation Detection"},
    "wave_analysis": {"func": wave_analysis_predict, "name": AI_MODE_NAMES["wave_analysis"], "desc": "Elliott Wave"},
    "chaos_theory": {"func": chaos_theory_predict, "name": AI_MODE_NAMES["chaos_theory"], "desc": "Entropy Analysis"},
    "ensemble": {"func": ensemble_predict, "name": AI_MODE_NAMES["ensemble"], "desc": "12 AI Voting System"},
    "bayesian": {"func": bayesian_predict, "name": AI_MODE_NAMES["bayesian"], "desc": "Conditional Probability"},
    "markov_chain": {"func": markov_chain_predict, "name": AI_MODE_NAMES["markov_chain"], "desc": "Transition Matrix"},
    "ml_style": {"func": ml_style_predict, "name": AI_MODE_NAMES["ml_style"], "desc": "Weighted Features"},
    "circle_rnd": {"func": circle_rnd_predict, "name": AI_MODE_NAMES["circle_rnd"], "desc": "Random Wheel Spin"},
}

def get_prediction(history_docs, mode):
    mode_info = AI_MODES.get(mode)
    if mode_info: return mode_info["func"](history_docs)
    return AI_MODES["pattern"]["func"](history_docs)

# ==========================================================
# 🎨 AI Mode Emoji IDs for Reply Keyboard (xxx.py အတွက်)
# ==========================================================
from aiogram.types import KeyboardButton

AI_MODE_BUTTONS = {
    "pattern": KeyboardButton(
        text=AI_MODE_NAMES["pattern"],
        icon_custom_emoji_id="5868656545634689320",
        style="primary"
    ),
    "martingale": KeyboardButton(
        text=AI_MODE_NAMES["martingale"],
        icon_custom_emoji_id="5868108575387671725",
        style="primary"
    ),
    "anti_martingale": KeyboardButton(
        text=AI_MODE_NAMES["anti_martingale"],
        icon_custom_emoji_id="5868665489092263539",
        style="primary"
    ),
    "trend_following": KeyboardButton(
        text=AI_MODE_NAMES["trend_following"],
        icon_custom_emoji_id="5877652234091891383",
        style="primary"
    ),
    "fibonacci": KeyboardButton(
        text=AI_MODE_NAMES["fibonacci"],
        icon_custom_emoji_id="5877260593903177342",
        style="primary"
    ),
    "golden_ratio": KeyboardButton(
        text=AI_MODE_NAMES["golden_ratio"],
        icon_custom_emoji_id="5869547610204280761",
        style="primary"
    ),
    "momentum": KeyboardButton(
        text=AI_MODE_NAMES["momentum"],
        icon_custom_emoji_id="5884248697980608904",
        style="primary"
    ),
    "monte_carlo": KeyboardButton(
        text=AI_MODE_NAMES["monte_carlo"],
        icon_custom_emoji_id="5884041323843955199",
        style="primary"
    ),
    "neural_pattern": KeyboardButton(
        text=AI_MODE_NAMES["neural_pattern"],
        icon_custom_emoji_id="5875180111744995604",
        style="primary"
    ),
    "quick_reversal": KeyboardButton(
        text=AI_MODE_NAMES["quick_reversal"],
        icon_custom_emoji_id="5890997763331591703",
        style="primary"
    ),
    "wave_analysis": KeyboardButton(
        text=AI_MODE_NAMES["wave_analysis"],
        icon_custom_emoji_id="5967574255670399788",
        style="primary"
    ),
    "chaos_theory": KeyboardButton(
        text=AI_MODE_NAMES["chaos_theory"],
        icon_custom_emoji_id="5877443460725739250",
        style="primary"
    ),
    "ensemble": KeyboardButton(
        text=AI_MODE_NAMES["ensemble"],
        icon_custom_emoji_id="5877652234091891383",
        style="primary"
    ),
    "bayesian": KeyboardButton(
        text=AI_MODE_NAMES["bayesian"],
        icon_custom_emoji_id="5868656545634689320",
        style="primary"
    ),
    "markov_chain": KeyboardButton(
        text=AI_MODE_NAMES["markov_chain"],
        icon_custom_emoji_id="5848119413041431362",
        style="primary"
    ),
    "ml_style": KeyboardButton(
        text=AI_MODE_NAMES["ml_style"],
        icon_custom_emoji_id="5884289942371401145",
        style="primary"
    ),
    "circle_rnd": KeyboardButton(
        text=AI_MODE_NAMES["circle_rnd"],
        icon_custom_emoji_id="5807868868886009920",
        style="primary"
    ),
}

def get_ai_mode_buttons():
    """Return list of all AI mode buttons for keyboard"""
    return list(AI_MODE_BUTTONS.values())
[file content end]
