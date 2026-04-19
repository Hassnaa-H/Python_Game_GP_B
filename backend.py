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
    'Level_9': ['down','down', 'right', 'down','down','up', 'up','up','up' ,'right', 'right','down', 'right', 'left', 'left','down','down','down', 'right','right','right','left','left','down','down','down', 'right', 'right'],
    'Level_10': ['down','down', 'right', 'up','up', 'right', 'right','down', 'left', 'down','down','down', 'right', 'down','down','down', 'right', 'right','down']
}

# Optional full walkable-tile maps for levels that have extra branches
# not covered by the single canonical treasure route.
LEVEL_WALKABLE_POSITIONS = {
    "Level_8": {
        (0, 0), (1, 0), (1, -1),
        (2, -1), (3, -1), (4, -1), (5, -1),
        (5, -2), (6, -2), (7, -2), (7, -1),
        (5, 0), (5, 1)
    },
    "Level_9": {
        (0, 0), (0, 1), (0, 2),
        (1, 2), (1, 3), (1, 4),
        (1, 1), (1, 0),
        (2, 0), (3, 0), (3, 1),
        (4, 1), (2, 1),
        (2, 2), (2, 3), (2, 4),
        (3, 4), (3, 5), (3, 6), (3, 7),
        (4, 7), (5, 7),
        (4, 4), (5, 4)
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
        level_type = LEVEL_CONFIG.get(level, {}).get("type")

        if level_type == "sequence":
            moves, _ = parse_statements(code, 0)
            return check_sequence(level, moves)

        elif level_type == "variables":
            return check_variables(code)

        elif level_type == "loops":
            moves, _ = parse_statements(code, 0)
            return check_loops(code, moves)

        elif level_type == "conditions":
            moves, _ = parse_statements(code, 0)
            return check_conditions(code, moves)

        elif level_type == "functions":
            moves, _ = parse_statements(code, 0)
            return check_functions(code, level, moves)

        elif level_type == "lists":
            moves, _ = parse_statements(code, 0)
            return check_lists(code, level, moves)

        elif level_type == "smart_path":
            moves, _ = parse_statements(code, 0)
            return check_smart_path(moves)

        elif level_type == "obstacles":
            moves, _ = parse_statements(code, 0)
            return check_obstacles(moves)

        elif level_type == "goals_rewards":
            moves, _ = parse_statements(code, 0)
            return check_rewards(moves)

        elif level_type == "final":
            moves, _ = parse_statements(code, 0)
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

def check_variables(code):
    if "let" not in code:
        return error("Great start! Try using a variable with let.")

    moves = parse_variable_moves(code)

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
    if not re.search(r'\bif\s*\(', code):
        return error("Add an if condition to make your logic smarter 🔀")

    treasure_check = ensure_reached_treasure("Level_4", moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Well done! Condition used correctly ✅")

def check_functions(code, level, moves):
    if not re.search(r'\bfunction\s+[A-Za-z_$][\w$]*\s*\(\s*\)\s*\{', code):
        return error("Create a function first, then call it 🧩")

    if not re.search(r'\b(?!move_(?:right|left|up|down)\b)[A-Za-z_$][\w$]*\s*\(\s*\)\s*;', code):
        return error("Nice function! Now call your function to run the moves ▶️")

    treasure_check = ensure_reached_treasure(level, moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Great job! Function detected and path completed ✅")

def check_lists(code, level, moves):
    if not re.search(r'\blet\s+[A-Za-z_$][\w$]*\s*=\s*\[[^\]]*\]\s*;?', code):
        return error("Try using a list with [ ] to store your data 📚")

    if not re.search(r'\brun_list\s*\(\s*[A-Za-z_$][\w$]*\s*\)\s*;?', code):
        return error("Great list! Now use it with run_list(yourList); ▶️")

    treasure_check = ensure_reached_treasure(level, moves)
    if treasure_check:
        return treasure_check

    return success(moves, "Nice! List used correctly and treasure reached ✅")

def check_smart_path(moves):
    if len(moves) > 21:
        return error("Good thinking. Can you solve it with 21 moves or fewer? 🧠")

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
    expected_moves = LEVEL_SEQUENCES.get('Level_9', [])
    rewards = [(2,1), (3,4)]
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

    treasure_check = ensure_reached_treasure("Level_9", moves)
    if treasure_check:
        return treasure_check

    if collected < 2:
        return error("Almost there! Collect both rewards before finishing 🎯")

    if moves != expected_moves:
        return error("Incorrect sequence.")

    return success(moves, "Fantastic! All rewards collected 🎉")

def check_final(moves, code):
    if "for" not in code or "if" not in code:
        return error("Final level tip: use both a loop and an if condition ⚠️")

    treasure_check = ensure_reached_treasure("Level_10", moves)
    if treasure_check:
        return treasure_check

    shortest_moves = LEVEL_SEQUENCES.get("Level_10", [])
    if len(moves) > len(shortest_moves):
        return error("Hint: Use all you learned and choose the shortest path to the goal 🧠")

    if moves != shortest_moves:
        return error("Not the shortest correct route yet. Refine your decisions and try again ✨")

    return success(moves, "Legendary! You completed the final challenge 🏆")

# =========================
# PARSER
# =========================

FOR_PATTERN = re.compile(
    r'for\s*\(\s*let\s+([A-Za-z_$][\w$]*)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\d+)\s*;\s*\1\+\+\s*\)\s*\{'
)
IF_PATTERN = re.compile(
    r'if\s*\(\s*(true|false)\s*\)\s*\{'
)
FUNCTION_DEF_PATTERN = re.compile(
    r'function\s+([A-Za-z_$][\w$]*)\s*\(\s*\)\s*\{'
)
FUNCTION_CALL_PATTERN = re.compile(
    r'([A-Za-z_$][\w$]*)\s*\(\s*\)'
)
LIST_DECL_PATTERN = re.compile(
    r'let\s+([A-Za-z_$][\w$]*)\s*=\s*\[([^\]]*)\]\s*;?'
)
RUN_LIST_PATTERN = re.compile(
    r'run_list\s*\(\s*([A-Za-z_$][\w$]*)\s*\)\s*;?'
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

def parse_statements(code, pos, functions=None, lists=None):
    if functions is None:
        functions = {}
    if lists is None:
        lists = {}

    moves = []

    while True:
        pos = skip_whitespace(code, pos)

        if pos >= len(code) or code[pos] == '}':
            break

        if code.startswith('for', pos):
            loop_moves, pos = parse_for(code, pos, functions, lists)
            moves.extend(loop_moves)
            continue

        if code.startswith('if', pos):
            condition_moves, pos = parse_if(code, pos, functions, lists)
            moves.extend(condition_moves)
            continue

        if code.startswith('function', pos):
            pos = parse_function_definition(code, pos, functions, lists)
            continue

        list_decl_match = LIST_DECL_PATTERN.match(code, pos)
        if list_decl_match:
            list_name = list_decl_match.group(1)
            list_body = list_decl_match.group(2)
            lists[list_name] = parse_list_literal(list_body)
            pos = list_decl_match.end()
            continue

        run_list_match = RUN_LIST_PATTERN.match(code, pos)
        if run_list_match:
            list_name = run_list_match.group(1)
            if list_name not in lists:
                raise ValueError(f"List '{list_name}' is used before it is declared.")
            moves.extend(lists[list_name])
            pos = run_list_match.end()
            continue

        call_match = FUNCTION_CALL_PATTERN.match(code, pos)
        if call_match:
            function_name = call_match.group(1)
            if function_name in functions:
                moves.extend(functions[function_name])
                pos = call_match.end()
                pos = skip_semicolon(code, pos)
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

def parse_for(code, pos, functions, lists):
    match = FOR_PATTERN.match(code, pos)
    if not match:
        raise ValueError(f"Your for loop format looks incorrect near position {pos}.")

    start = int(match.group(2))
    end = int(match.group(3))
    repeat = max(0, end - start)

    pos = match.end()

    body_moves, pos = parse_statements(code, pos, functions, lists)

    pos = skip_whitespace(code, pos)
    if pos >= len(code) or code[pos] != '}':
        raise ValueError("Your for loop is missing a closing } brace.")

    pos += 1

    return body_moves * repeat, pos


def parse_if(code, pos, functions, lists):
    match = IF_PATTERN.match(code, pos)
    if not match:
        raise ValueError(f"Your if condition format looks incorrect near position {pos}.")

    condition_value = match.group(1) == 'true'
    pos = match.end()

    body_moves, pos = parse_statements(code, pos, functions, lists)

    pos = skip_whitespace(code, pos)
    if pos >= len(code) or code[pos] != '}':
        raise ValueError("Your if statement is missing a closing } brace.")

    pos += 1

    return (body_moves if condition_value else []), pos


def parse_function_definition(code, pos, functions, lists):
    match = FUNCTION_DEF_PATTERN.match(code, pos)
    if not match:
        raise ValueError(f"Your function format looks incorrect near position {pos}.")

    function_name = match.group(1)
    pos = match.end()

    body_moves, pos = parse_statements(code, pos, functions, lists)

    pos = skip_whitespace(code, pos)
    if pos >= len(code) or code[pos] != '}':
        raise ValueError("Your function is missing a closing } brace.")

    pos += 1
    functions[function_name] = body_moves
    return pos


def parse_list_literal(list_body):
    raw = list_body.strip()
    if not raw:
        return []

    values = []
    for part in raw.split(','):
        item = part.strip()
        token_match = re.fullmatch(r"['\"](right|left|up|down)['\"]", item)
        if not token_match:
            raise ValueError("List items must be one of: 'right', 'left', 'up', 'down'.")
        values.append(token_match.group(1))

    return values


def expand_axis_moves(axis, delta):
    if delta == 0:
        return []

    if axis == 'x':
        token = 'right' if delta > 0 else 'left'
    elif axis == 'y':
        token = 'down' if delta > 0 else 'up'
    else:
        return []

    return [token] * abs(delta)


def parse_variable_moves(code):
    variables = {}
    moves = []

    for line_no, raw_line in enumerate(code.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if line.endswith(';'):
            line = line[:-1].strip()

        decl_match = re.fullmatch(r'let\s+([A-Za-z_$][\w$]*)\s*=\s*(-?\d+)', line)
        if decl_match:
            name = decl_match.group(1)
            value = int(decl_match.group(2))
            old_value = variables.get(name, 0)
            variables[name] = value
            if name in ('x', 'y'):
                moves.extend(expand_axis_moves(name, value - old_value))
            continue

        assign_math_match = re.fullmatch(
            r'([A-Za-z_$][\w$]*)\s*=\s*([A-Za-z_$][\w$]*)\s*([+-])\s*(\d+)',
            line
        )
        if assign_math_match:
            target = assign_math_match.group(1)
            source = assign_math_match.group(2)
            operator = assign_math_match.group(3)
            amount = int(assign_math_match.group(4))

            if source not in variables:
                raise ValueError(f"Variable '{source}' is used before it is declared (line {line_no}).")

            source_value = variables[source]
            new_value = source_value + amount if operator == '+' else source_value - amount
            old_value = variables.get(target, 0)
            variables[target] = new_value

            if target in ('x', 'y'):
                moves.extend(expand_axis_moves(target, new_value - old_value))
            continue

        assign_value_match = re.fullmatch(r'([A-Za-z_$][\w$]*)\s*=\s*(-?\d+)', line)
        if assign_value_match:
            name = assign_value_match.group(1)
            new_value = int(assign_value_match.group(2))
            old_value = variables.get(name, 0)
            variables[name] = new_value
            if name in ('x', 'y'):
                moves.extend(expand_axis_moves(name, new_value - old_value))
            continue

        raise ValueError(f"I could not understand this variable statement on line {line_no}.")

    return moves

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