from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import logging
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

PAIR_PAYOUT = 11  # Выплата за пару
PAIR_BET_AMOUNT = 1.0  # Размер ставки на пару
PAIR_THRESHOLD = 30  # Порог для ставки на пару (начинаем с 31 раунда)

def calculate_pair_profit(shoe, pairs):
    """Рассчитывает прибыль от ставок на пары"""
    total_profit = 0.0
    bet_log = []
    stats = {
        'player_pair_bets': 0,
        'banker_pair_bets': 0,
        'player_pair_wins': 0,
        'banker_pair_wins': 0
    }

    for i, (result, pair) in enumerate(zip(shoe, pairs)):
        # Проверяем, сколько раундов прошло без Player Pair
        last_player_pair = next((idx for idx in range(i-1, -1, -1) 
                            if pairs[idx]['playerPair']), None)
        rounds_since_player_pair = i - last_player_pair if last_player_pair is not None else i + 1

        # Проверяем, сколько раундов прошло без Banker Pair
        last_banker_pair = next((idx for idx in range(i-1, -1, -1) 
                            if pairs[idx]['bankerPair']), None)
        rounds_since_banker_pair = i - last_banker_pair if last_banker_pair is not None else i + 1

        # Делаем ставки на пары, если не было более PAIR_THRESHOLD раундов (начинаем с 31)
        player_pair_bet = rounds_since_player_pair > PAIR_THRESHOLD
        banker_pair_bet = rounds_since_banker_pair > PAIR_THRESHOLD

        if player_pair_bet:
            stats['player_pair_bets'] += 1
            if pair['playerPair']:
                profit = PAIR_BET_AMOUNT * PAIR_PAYOUT
                total_profit += profit
                stats['player_pair_wins'] += 1
                bet_log.append(f"Ранд {i+1}: Ставка на Player Pair - Выигрыш (+{profit:.2f})")
            else:
                total_profit -= PAIR_BET_AMOUNT
                bet_log.append(f"Ранд {i+1}: Ставка на Player Pair - Проигрыш (-{PAIR_BET_AMOUNT:.2f})")

        if banker_pair_bet:
            stats['banker_pair_bets'] += 1
            if pair['bankerPair']:
                profit = PAIR_BET_AMOUNT * PAIR_PAYOUT
                total_profit += profit
                stats['banker_pair_wins'] += 1
                bet_log.append(f"Ранд {i+1}: Ставка на Banker Pair - Выигрыш (+{profit:.2f})")
            else:
                total_profit -= PAIR_BET_AMOUNT
                bet_log.append(f"Ранд {i+1}: Ставка на Banker Pair - Проигрыш (-{PAIR_BET_AMOUNT:.2f})")

    # Определяем следующую ставку на пары
    bet_player_pair = False
    bet_banker_pair = False
    
    if len(shoe) > 0:
        last_player_pair = next((idx for idx in range(len(shoe)-1, -1, -1) 
                            if pairs[idx]['playerPair']), None)
        rounds_since_player_pair = len(shoe) - last_player_pair if last_player_pair is not None else len(shoe) + 1

        last_banker_pair = next((idx for idx in range(len(shoe)-1, -1, -1) 
                            if pairs[idx]['bankerPair']), None)
        rounds_since_banker_pair = len(shoe) - last_banker_pair if last_banker_pair is not None else len(shoe) + 1

        bet_player_pair = rounds_since_player_pair > PAIR_THRESHOLD
        bet_banker_pair = rounds_since_banker_pair > PAIR_THRESHOLD

    return total_profit, bet_log, stats, bet_player_pair, bet_banker_pair

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_bet', methods=['POST'])
def get_bet():
    try:
        data = request.get_json()
        if not data or 'shoe' not in data:
            return jsonify({'error': 'Отсутствует поле shoe'}), 400

        shoe = data['shoe']
        pairs = data.get('pairs', [{} for _ in shoe])  # Заполняем пустыми значениями если нет пар
        
        if not isinstance(shoe, list) or not all(x in [0, 1, 2] for x in shoe):
            return jsonify({'error': 'Неверный формат шуза'}), 400

        # Рассчитываем прибыль от ставок на пары
        pair_profit, pair_bet_log, pair_stats, bet_player_pair, bet_banker_pair = calculate_pair_profit(shoe, pairs)
        
        # Формируем полный лог
        full_log = ["=== Ставки на пары ==="] + pair_bet_log
        full_log.append("\n=== Статистика ===")
        full_log.append(f"Общая прибыль: {pair_profit:.2f}")
        full_log.append(f"Ставок на Player Pair: {pair_stats['player_pair_bets']}")
        full_log.append(f"Выигрышей Player Pair: {pair_stats['player_pair_wins']}")
        full_log.append(f"Ставок на Banker Pair: {pair_stats['banker_pair_bets']}")
        full_log.append(f"Выигрышей Banker Pair: {pair_stats['banker_pair_wins']}")

        return jsonify({
            'shoe': shoe,
            'pairs': pairs,
            'bet_player_pair': bet_player_pair,
            'bet_banker_pair': bet_banker_pair,
            'next_bet_amount': PAIR_BET_AMOUNT,
            'profit': pair_profit,
            'log': "\n".join(full_log),
            'stats': {
                'total_profit': pair_profit,
                'player_pair_bets': pair_stats['player_pair_bets'],
                'banker_pair_bets': pair_stats['banker_pair_bets'],
                'player_pair_wins': pair_stats['player_pair_wins'],
                'banker_pair_wins': pair_stats['banker_pair_wins']
            }
        })

    except Exception as e:
        logger.error(f"Ошибка в get_bet: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 4005)))
