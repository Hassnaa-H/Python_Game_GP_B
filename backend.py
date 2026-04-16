from flask import Flask, request, jsonify, send_from_directory, redirect
import re

app = Flask(__name__, static_folder='.', static_url_path='')

# =========================
# CONFIG
# =========================

COMMAND_MAP = {
    'move_right()': 'right',
    'move_left()': 'left',
    'move_up()': 'up',
    'move_down()': 'down'
}

LEVEL_CONFIG = {
    "Level_1": {"type": "sequence"},
    "Level_2": {"type": "variables"},
    "Level_3": {"type": "loops"},
    "Level_4": {"type": "conditions"},
    "Level_5": {"type": "functions"},
    "Level_6": {"type": "lists"},
    "Level_7": {"type": "smart_path"},
    "Level_8": {"type": "obstacles"},
    "Level_9": {"type": "goals_rewards"},
    "Level_10": {"type": "final"}
}

LEVEL_SEQUENCES = {
    'Level_1': ['right','right','right','right','down','down','left','left','left','left','down','down','right','right','right','right'],
    'Level_2': ['right', 'right','right','down','down', 'right'],
    'Level_3': ['right', 'right','right','right', 'down', 'down','left', 'left', 'left', 'down', 'down','right','right','right'],
    'Level_4': ['right', 'up','right','right','right','right','down', 'down','right', 'right'],
    'Level_5': ['right', 'right', 'right', 'right','right', 'down', 'down','left', 'left', 'left', 'left','left', 'down', 'down','right', 'right', 'right', 'right','right','down', 'down','right'],
    'Level_6': ['right', 'right', 'right', 'right','right','down', 'down','left', 'left', 'left','left','left','down', 'down'],
    'Level_7': ['right','right','right','right','right', 'down', 'down','left', 'left', 'left','left','left','down', 'down','right', 'right', 'right', 'right','right','down', 'down'],
    'Level_8': ['right','up', 'right', 'right', 'right','right','up', 'right', 'right','down'],
    'Level_9': ['down','down', 'right', 'down','down','up', 'up','up','up' ,'right', 'right','down', 'right', 'left', 'left','down','down','down', 'right','down','down','down', 'right', 'right'],
    'Level_10': ['down','down', 'right', 'down','down','up', 'up','up','up' ,'right', 'right','down', 'right', 'left', 'left','down','down','down', 'right','down','down','down', 'right', 'right','down']
}

# Optional full walkable-tile maps for levels that have extra branches
# not covered by the single canonical treasure route.
LEVEL_WALKABLE_POSITIONS = {
    "Level_8": {
        (0, 0), (1, 0), (1, -1),
        (2, -1), (3, -1), (4, -1), (5, -1),
        (5, -2), (6, -2), (7, -2), (7, -1),
        (5, 0), (5, 1)
    }
}

# =========================
# HELPERS
# =========================

def success(moves, msg):
    return jsonify({
        "success": True,
        "message": msg,
        "moves": moves,
        "type": "success"
    })

def error(msg, moves=[]):
    return jsonify({
        "success": False,
        "message": msg,
        "moves": moves,
        "type": "error"
    }), 400


def get_valid_path_prefix(level, moves):
    valid_moves, _, _, _ = trim_moves_inside_path(level, moves)
    return valid_moves


def build_path_positions(level):
    target = LEVEL_SEQUENCES.get(level, [])
    x, y = 0, 0
    positions = {(x, y)}

    for move in target:
        if move == "right":
            x += 1
        elif move == "left":
            x -= 1
        elif move == "up":
            y -= 1
        elif move == "down":
            y += 1
        positions.add((x, y))

    return positions


def get_walkable_positions(level):
    if level in LEVEL_WALKABLE_POSITIONS:
        return LEVEL_WALKABLE_POSITIONS[level]
    return build_path_positions(level)


def get_treasure_position(level):
    target = LEVEL_SEQUENCES.get(level, [])
    x, y = 0, 0

    for move in target:
        if move == "right":
            x += 1
        elif move == "left":
            x -= 1
        elif move == "up":
            y -= 1
        elif move == "down":
            y += 1

    return x, y


def trim_moves_inside_path(level, moves):
    walkable = get_walkable_positions(level)
    x, y = 0, 0
    valid_moves = []

    for i, move in enumerate(moves):
        next_x, next_y = x, y
        if move == "right":
            next_x += 1
        elif move == "left":
            next_x -= 1
        elif move == "up":
            next_y -= 1
        elif move == "down":
            next_y += 1

        if (next_x, next_y) not in walkable:
            return valid_moves, (x, y), i, move

        valid_moves.append(move)
        x, y = next_x, next_y

    return valid_moves, (x, y), None, None


def ensure_reached_treasure(level, moves):
    target = LEVEL_SEQUENCES.get(level)
    if not target:
        return None

    valid_moves, final_pos, invalid_index, invalid_move = trim_moves_inside_path(level, moves)

    if len(valid_moves) != len(moves):
        return error(
            f"Step {invalid_index + 1} ({invalid_move}) hits a wall. Stay on the path tiles and try again 🧱",
            valid_moves
        )

    if final_pos == get_treasure_position(level):
        return None

    return error("Nice path! Now keep moving until you reach the treasure 🏁", valid_moves)

# =========================
# MAIN ROUTE
# =========================

@app.route('/run', methods=['POST'])
def run_code():
    data = request.get_json(silent=True)
    if not data or 'code' not in data:
        return error("Please add some code first, then press Run.")

    code = remove_comments(data['code'])
    level = data.get('level', 'Level_1')

    try:
        moves, _ = parse_statements(code, 0)

        level_type = LEVEL_CONFIG.get(level, {}).get("type")

        if level_type == "sequence":
            return check_sequence(level, moves)

        elif level_type == "variables":
            return check_variables(code, moves)

        elif level_type == "loops":
            return check_loops(code, moves)

        elif level_type == "conditions":
            return check_conditions(code, moves)

        elif level_type == "functions":
            return check_functions(code, level, moves)

        elif level_type == "lists":
            return check_lists(code, level, moves)

        elif level_type == "smart_path":
            return check_smart_path(moves)

        elif level_type == "obstacles":
            return check_obstacles(moves)

        elif level_type == "goals_rewards":
            return check_rewards(moves)

        elif level_type == "final":
            return check_final(moves, code)

        else:
            return error("I could not identify this level. Please reload and try again.")

    except ValueError as e:
        return error(f"Almost there! {str(e)}")

# =========================
# LEVEL LOGIC
# =========================

def check_sequence(level, moves):
    treasure_check = ensure_reached_treasure(level, moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Awesome! You stayed on the path and reached the treasure 🎉")

def check_variables(code, moves):
    if "let" not in code:
        return error("Great start! Try using a variable with let.")

    if len(moves) < 3:
        return error("You are close. Add a few more moves.")

    treasure_check = ensure_reached_treasure("Level_2", moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Nice work! Great use of variables ✅")

def check_loops(code, moves):
    if "for" not in code:
        return error("Try using a for loop to repeat moves more easily 🔁")

    treasure_check = ensure_reached_treasure("Level_3", moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Excellent! Your loop works great 🚀")

def check_conditions(code, moves):
    if "if" not in code:
        return error("Add an if condition to make your logic smarter 🔀")

    treasure_check = ensure_reached_treasure("Level_4", moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Well done! Condition used correctly ✅")

def check_functions(code, level, moves):
    if "function" not in code:
        return error("Create a function first, then call it 🧩")

    treasure_check = ensure_reached_treasure(level, moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Great job! Function detected and path completed ✅")

def check_lists(code, level, moves):
    if "[" not in code or "]" not in code:
        return error("Try using a list with [ ] to store your data 📚")

    treasure_check = ensure_reached_treasure(level, moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Nice! List used correctly and treasure reached ✅")

def check_smart_path(moves):
    if len(moves) > 20:
        return error("Good thinking. Can you solve it with fewer than 20 moves? 🧠")

    treasure_check = ensure_reached_treasure("Level_7", moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Brilliant! Smart and efficient path 🚀")

def check_obstacles(moves):
    obstacles = [(2,2), (3,3)]
    x, y = 0, 0

    for move in moves:
        if move == "right": x += 1
        if move == "left": x -= 1
        if move == "up": y -= 1
        if move == "down": y += 1

        if (x, y) in obstacles:
            return error("Oops, you bumped into an obstacle. Try a safer route 🚧")

    treasure_check = ensure_reached_treasure("Level_8", moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Excellent! You avoided all obstacles ✅")

def check_rewards(moves):
    rewards = [(2,1), (4,3)]
    x, y = 0, 0
    collected = 0
    collected_rewards = set()

    for move in moves:
        if move == "right": x += 1
        if move == "left": x -= 1
        if move == "up": y -= 1
        if move == "down": y += 1

        if (x, y) in rewards and (x, y) not in collected_rewards:
            collected += 1
            collected_rewards.add((x, y))

    if collected < 2:
        return error("Almost there! Collect both rewards before finishing 🎯")

    treasure_check = ensure_reached_treasure("Level_9", moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Fantastic! All rewards collected 🎉")

def check_final(moves, code):
    if "for" not in code or "if" not in code:
        return error("Final level tip: use both a loop and an if condition ⚠️")

    if len(moves) < 10:
        return error("Nice attempt! Try a more complete solution.")

    treasure_check = ensure_reached_treasure("Level_10", moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Legendary! You completed the final challenge 🏆")

# =========================
# PARSER
# =========================

FOR_PATTERN = re.compile(
    r'for\s*\(\s*let\s+([A-Za-z_$][\w$]*)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\d+)\s*;\s*\1\+\+\s*\)\s*\{'
)

def remove_comments(code):
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
    return code

def skip_whitespace(code, pos):
    while pos < len(code) and code[pos].isspace():
        pos += 1
    return pos

def skip_semicolon(code, pos):
    pos = skip_whitespace(code, pos)
    if pos < len(code) and code[pos] == ';':
        pos += 1
    return pos

def parse_statements(code, pos):
    moves = []

    while True:
        pos = skip_whitespace(code, pos)

        if pos >= len(code) or code[pos] == '}':
            break

        if code.startswith('for', pos):
            loop_moves, pos = parse_for(code, pos)
            moves.extend(loop_moves)
            continue

        matched = False
        for token, direction in COMMAND_MAP.items():
            if code.startswith(token, pos):
                moves.append(direction)
                pos += len(token)
                pos = skip_semicolon(code, pos)
                matched = True
                break

        if matched:
            continue

        raise ValueError(f"I could not understand this part of your code near position {pos}.")

    return moves, pos

def parse_for(code, pos):
    match = FOR_PATTERN.match(code, pos)
    if not match:
        raise ValueError(f"Your for loop format looks incorrect near position {pos}.")

    start = int(match.group(2))
    end = int(match.group(3))
    repeat = max(0, end - start)

    pos = match.end()

    body_moves, pos = parse_statements(code, pos)

    pos = skip_whitespace(code, pos)
    if pos >= len(code) or code[pos] != '}':
        raise ValueError("Your for loop is missing a closing } brace.")

    pos += 1

    return body_moves * repeat, pos

# =========================
# STATIC
# =========================

@app.before_request
def normalize_trailing_slash():
    # Keep root as-is, but canonicalize file-like URLs such as /index.html/.
    if request.path != '/' and request.path.endswith('/'):
        target = request.path.rstrip('/')
        if request.query_string:
            return redirect(f"{target}?{request.query_string.decode()}", code=301)
        return redirect(target, code=301)


@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def static_file(path):
    if path == 'run':
        return 'Not Found', 404
    try:
        return send_from_directory('.', path)
    except:
        return 'Not Found', 404

# =========================
# RUN
# =========================

if __name__ == '__main__':
    app.run(debug=True)