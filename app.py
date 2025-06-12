from flask import Flask, request, jsonify
from collections import defaultdict

app = Flask(__name__)

PAIR_TYPES = ['PP', 'BP']
PAIR_NOT_SEEN_THRESHOLD = 30
PAIR_PREDICTION_ZONE = range(31, 41)
PAIR_PAYOUT = 11
PAIR_LOSS = 1

@app.route('/get_bet', methods=['POST'])
def get_bet():
    data = request.get_json()
    shoe = data.get('shoe', [])  # 0=Player, 1=Banker, 2=Tie, 3=PP, 4=BP

    # История пар и ничьих
    pair_history = defaultdict(list)
    tie_indexes = []

    for idx, val in enumerate(shoe):
        if val == 3:
            pair_history['PP'].append(idx)
        elif val == 4:
            pair_history['BP'].append(idx)
        elif val == 2:
            tie_indexes.append(idx)

    stats = {
        'total_rounds': len(shoe),
        'tie_count': len(tie_indexes),
        'tie_indexes': tie_indexes,
        'pair_prediction_result': 'Нет прогноза'
    }

    for pair_type in PAIR_TYPES:
        last_seen = pair_history[pair_type][-1] if pair_history[pair_type] else -1
        since = len(shoe) - 1 - last_seen
        if since >= PAIR_NOT_SEEN_THRESHOLD:
            if since + 1 in PAIR_PREDICTION_ZONE:
                hit = len(pair_history[pair_type]) > 0 and pair_history[pair_type][-1] == len(shoe) - 1
                if hit:
                    stats['pair_prediction_result'] = f"{pair_type} выпала в раунде {len(shoe)} – +{PAIR_PAYOUT}"
                elif since + 1 == max(PAIR_PREDICTION_ZONE):
                    stats['pair_prediction_result'] = f"{pair_type} не выпала до раунда {len(shoe)} – завершение прогноза"
                else:
                    stats['pair_prediction_result'] = f"Прогноз: ждем {pair_type} (раунд {since + 1} из 10)"
            break

    return jsonify({
        'shoe': shoe,
        'stats': stats
    })

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 4005)))
