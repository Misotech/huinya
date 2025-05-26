from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import logging
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Конфигурация стратегии Мартингейла
MARTINGALE_SEQUENCE = [0, 1, 1, 1, 0, 0]  # 0=Игрок, 1=Банкир
INITIAL_BANK = 110
INITIAL_BET = 0.2
RESET_SEQUENCE = False
RESET_AFTER_LOSSES = float('inf')

BANKER_PAYOUT = 0.95
PLAYER_PAYOUT = 1.0

def calculate_payout(bet, outcome, actual_result):
    """Рассчитывает выплату для ставки."""
    if outcome != actual_result:
        return -bet
    if outcome == 0:  # Игрок
        return bet
    else:  # Банкир
        return bet * 0.95

def calculate_full_profit(filtered_shoe):
    bank = INITIAL_BANK
    bet = INITIAL_BET
    seq_index = 0
    total_bets = 0
    total_wins = 0
    total_profit = 0.0
    bets_history = []
    bet_log = []
    bankrupt = False
    bankrupt_hand = None
    
    # Инициализация лога
    bet_log.append(f"{'Индекс':<8} {'Ставка':<8} {'Сумма':<10} {'Результат':<10} {'Прибыль':<10} {'Банкролл':<12} {'Поз. посл.':<12}")
    bet_log.append("-" * 70)
    
    for i, result in enumerate(filtered_shoe):
        # Проверяем на разорение
        if bank < bet:
            bankrupt = True
            bankrupt_hand = i
            bet_log.append(f"{i:<8} {'-':<8} {bet:>10.2f} {'Разорение':<10} {total_profit:>10.2f} {bank:>12.2f} {seq_index:<12}")
            break
        
        # Определяем сторону ставки
        outcome = MARTINGALE_SEQUENCE[seq_index]
        bet_side = 'Игрок' if outcome == 0 else 'Банкир'
        
        # Рассчитываем выплату
        total_bets += 1
        payout = calculate_payout(bet, outcome, result)
        total_profit += payout
        bank += payout
        
        # Логируем результат
        if payout > 0:
            total_wins += 1
            outcome_str = 'Выигрыш'
            bets_history.append({'index': i, 'bet': bet_side, 'bet_amount': bet, 'outcome': 'Выигрыш', 'profit': payout, 'bankroll': bank})
        else:
            outcome_str = 'Проигрыш'
            bets_history.append({'index': i, 'bet': bet_side, 'bet_amount': bet, 'outcome': 'Проигрыш', 'profit': payout, 'bankroll': bank})
        
        bet_log.append(f"{i:<8} {bet_side:<8} {bet:>10.2f} {outcome_str:<10} {total_profit:>10.2f} {bank:>12.2f} {seq_index:<12}")
        
        # Обновляем ставку и индекс последовательности
        if payout > 0:
            bet = INITIAL_BET
            seq_index = 0 if RESET_SEQUENCE else (seq_index + 1) % len(MARTINGALE_SEQUENCE)
        else:
            bet *= 2
            seq_index = (seq_index + 1) % len(MARTINGALE_SEQUENCE)
            if seq_index == 0 and (i + 1) % len(MARTINGALE_SEQUENCE) == 0:
                bet = INITIAL_BET if (i + 1) >= RESET_AFTER_LOSSES else bet
    
    # Прогноз для следующей ставки
    next_outcome = MARTINGALE_SEQUENCE[seq_index]
    next_bet_side = 'Игрок' if next_outcome == 0 else 'Банкир'
    next_bet_amount = bet  # Сохраняем сумму следующей ставки
    
    # Добавляем прогноз в лог
    bet_log.append(f"{len(filtered_shoe):<8} {next_bet_side:<8} {bet:>10.2f} {'Прогноз':<10} {total_profit:>10.2f} {bank:>12.2f} {seq_index:<12}")
    bet_log.append("-" * 70)
    
    win_rate = total_wins / total_bets if total_bets > 0 else 0
    return next_bet_side, round(total_profit, 2), bets_history, bet_log, {
        'total_profit': round(total_profit, 2),
        'total_bets': total_bets,
        'total_wins': total_wins,
        'win_rate': round(win_rate, 4),
        'bankrupt': bankrupt,
        'bankrupt_hand': bankrupt_hand,
        'final_bankroll': round(bank, 2)
    }, next_bet_amount

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
        if not isinstance(shoe, list) or not all(x in [0, 1, 2] for x in shoe):
            return jsonify({'error': 'Неверный формат шуза'}), 400

        filtered_shoe = [x for x in shoe if x != 2]
        
        bet_side, total_profit, bets_history, bet_log, stats, next_bet_amount = calculate_full_profit(filtered_shoe)

        return jsonify({
            'shoe': shoe,
            'bet_side': bet_side,
            'next_bet_amount': next_bet_amount,  # Добавляем сумму следующей ставки
            'profit': total_profit,
            'bets_history': bets_history,
            'log': "\n".join(bet_log),
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Ошибка в get_bet: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 4005)))
