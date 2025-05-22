from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import logging
from collections import defaultdict
import os

app = Flask(__name__)
CORS(app)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Конфигурации стратегий
STRATEGIES = [
    
    {'name': 'add3', 'window': 8, 'enter': 1, 'exit': 0.66}
]

BANKER_PAYOUT = 0.95
PLAYER_PAYOUT = 1.0

def calculate_full_profit(filtered_shoe):
    active_strategies = []
    total_bets = total_wins = 0
    total_profit = 0.0
    bets_history = []
    bet_log = []
    
    # Инициализация лога
    bet_log.append("\nЛог ставок для последовательности:")
    bet_log.append(f"{'Индекс':<8} {'Ставка':<8} {'Результат':<10} {'Прибыль':<10} {'Окно':<30} {'Данные окна':<30}")
    bet_log.append("-" * 86)
    
    next_bet_side = None  # Прогноз для следующей ставки
    
    for i in range(len(filtered_shoe)):
        # Определяем прогноз для текущего шага на основе предыдущих данных
        banker_bets = player_bets = 0
        windows_info = []
        temp_active = []
        
        # Анализ активных стратегий
        for strat_info in active_strategies:
            strat = strat_info['strat']
            window = filtered_shoe[max(0, i-strat['window']):i]
            
            if len(window) >= strat['window']//2:
                banker_ratio = sum(window)/len(window) if window else 0
                player_ratio = 1 - banker_ratio if window else 0
                
                if (strat_info['bet_type'] == 1 and banker_ratio <= strat['exit']) or \
                   (strat_info['bet_type'] == 0 and player_ratio <= strat['exit']):
                    continue
                else:
                    temp_active.append(strat_info)
                    if strat_info['bet_type'] == 1:
                        banker_bets += 1
                        windows_info.append(f"{strat['name']}({strat['window']})")
                    else:
                        player_bets += 1
                        windows_info.append(f"{strat['name']}({strat['window']})")
        
        # Активация новых стратегий
        for strat in STRATEGIES:
            if i >= strat['window']//2 and i < strat['window']:
                window = filtered_shoe[max(0, i-strat['window']):i]
                if len(window) < strat['window']//2:
                    continue
                banker_ratio = sum(window)/len(window) if window else 0
                player_ratio = 1 - banker_ratio if window else 0
                
                if banker_ratio >= strat['enter']:
                    temp_active.append({'strat': strat, 'bet_type': 1})
                    banker_bets += 1
                    windows_info.append(f"{strat['name']}({strat['window']})")
                elif player_ratio >= strat['enter']:
                    temp_active.append({'strat': strat, 'bet_type': 0})
                    player_bets += 1
                    windows_info.append(f"{strat['name']}({strat['window']})")
        
        # Определяем прогноз для текущего шага
        current_bet_side = 'Banker' if banker_bets > player_bets else 'Player' if player_bets > banker_bets else None
        
        # Формирование строки лога
        windows_str = ", ".join(windows_info) if windows_info else "Нет"
        window_data = str(filtered_shoe[max(0, i-max(s['window'] for s in STRATEGIES)):i]) if windows_info else "[]"
        
        # Расчёт прибыли для текущего шага, если есть ставка
        if i >= min(s['window'] for s in STRATEGIES)//2 and current_bet_side is not None:
            current_result = filtered_shoe[i]
            total_bets += 1
            if current_bet_side == 'Banker' and current_result == 1:
                total_wins += 1
                total_profit += BANKER_PAYOUT
                bets_history.append({'index': i, 'bet': 'Banker', 'outcome': 'Win', 'profit': BANKER_PAYOUT})
                bet_log.append(f"{i:<8} {'Banker':<8} {'Выигрыш':<10} {total_profit:>10.2f} {windows_str:<30} {window_data:<30}")
            elif current_bet_side == 'Player' and current_result == 0:
                total_wins += 1
                total_profit += PLAYER_PAYOUT
                bets_history.append({'index': i, 'bet': 'Player', 'outcome': 'Win', 'profit': PLAYER_PAYOUT})
                bet_log.append(f"{i:<8} {'Player':<8} {'Выигрыш':<10} {total_profit:>10.2f} {windows_str:<30} {window_data:<30}")
            else:
                total_profit -= 1
                bets_history.append({'index': i, 'bet': current_bet_side, 'outcome': 'Loss', 'profit': -1})
                bet_log.append(f"{i:<8} {current_bet_side:<8} {'Проигрыш':<10} {total_profit:>10.2f} {windows_str:<30} {window_data:<30}")
        else:
            bet_log.append(f"{i:<8} {'-':<8} {'-':<10} {total_profit:>10.2f} {windows_str:<30} {window_data:<30}")
        
        # Обновляем активные стратегии и прогноз для следующего шага
        active_strategies = temp_active
        next_bet_side = current_bet_side
    
    # Добавляем прогноз для следующего шага в лог
    banker_bets = player_bets = 0
    windows_info = []
    temp_active = []
    
    # Анализ активных стратегий для последнего шага
    for strat_info in active_strategies:
        strat = strat_info['strat']
        window = filtered_shoe[max(0, len(filtered_shoe)-strat['window']):len(filtered_shoe)]
        
        if len(window) >= strat['window']//2:
            banker_ratio = sum(window)/len(window) if window else 0
            player_ratio = 1 - banker_ratio if window else 0
            
            if (strat_info['bet_type'] == 1 and banker_ratio <= strat['exit']) or \
               (strat_info['bet_type'] == 0 and player_ratio <= strat['exit']):
                continue
            else:
                temp_active.append(strat_info)
                if strat_info['bet_type'] == 1:
                    banker_bets += 1
                    windows_info.append(f"{strat['name']}({strat['window']})")
                else:
                    player_bets += 1
                    windows_info.append(f"{strat['name']}({strat['window']})")
    
    # Активация новых стратегий для последнего шага
    for strat in STRATEGIES:
        if len(filtered_shoe) >= strat['window']//2 and len(filtered_shoe) < strat['window']:
            window = filtered_shoe[max(0, len(filtered_shoe)-strat['window']):len(filtered_shoe)]
            if len(window) < strat['window']//2:
                continue
            banker_ratio = sum(window)/len(window) if window else 0
            player_ratio = 1 - banker_ratio if window else 0
            
            if banker_ratio >= strat['enter']:
                temp_active.append({'strat': strat, 'bet_type': 1})
                banker_bets += 1
                windows_info.append(f"{strat['name']}({strat['window']})")
            elif player_ratio >= strat['enter']:
                temp_active.append({'strat': strat, 'bet_type': 0})
                player_bets += 1
                windows_info.append(f"{strat['name']}({strat['window']})")
    
    # Финальный прогноз
    next_bet_side = 'Banker' if banker_bets > player_bets else 'Player' if player_bets > banker_bets else None
    
    # Добавляем строку с прогнозом в лог
    windows_str = ", ".join(windows_info) if windows_info else "Нет"
    window_data = str(filtered_shoe[max(0, len(filtered_shoe)-max(s['window'] for s in STRATEGIES)):len(filtered_shoe)]) if windows_info else "[]"
    bet_log.append(f"{len(filtered_shoe):<8} {next_bet_side or '-':<8} {'Прогноз':<10} {total_profit:>10.2f} {windows_str:<30} {window_data:<30}")
    
    bet_log.append("-" * 86)
    win_rate = total_wins / total_bets if total_bets > 0 else 0
    return next_bet_side, round(total_profit, 2), bets_history, bet_log, {
        'total_profit': round(total_profit, 2),
        'total_bets': total_bets,
        'total_wins': total_wins,
        'win_rate': round(win_rate, 4)
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_bet', methods=['POST'])
def get_bet():
    try:
        data = request.get_json()
        if not data or 'shoe' not in data:
            return jsonify({'error': 'Missing shoe field'}), 400

        shoe = data['shoe']
        if not isinstance(shoe, list) or not all(x in [0, 1, 2] for x in shoe):
            return jsonify({'error': 'Invalid shoe format'}), 400

        filtered_shoe = [x for x in shoe if x != 2]
        
        # Минимальное требование - 4 элемента (window//2 для наименьшего окна 9)
        min_window = min(s['window'] for s in STRATEGIES) // 2
        if len(filtered_shoe) < min_window:
            return jsonify({
                'shoe': shoe,
                'bet_side': None,
                'profit': 0,
                'bets_history': [],
                'log': f"Ожидаем накопление {min_window} элементов (без Tie) для первого прогноза. Текущее количество: {len(filtered_shoe)}",
                'stats': {'total_profit': 0, 'total_bets': 0, 'total_wins': 0, 'win_rate': 0}
            })
        
        bet_side, total_profit, bets_history, bet_log, stats = calculate_full_profit(filtered_shoe)

        return jsonify({
            'shoe': shoe,
            'bet_side': bet_side,
            'profit': total_profit,
            'bets_history': bets_history,
            'log': "\n".join(bet_log),
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error in get_bet: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 4005)))
