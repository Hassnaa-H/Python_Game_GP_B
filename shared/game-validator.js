(function () {
    const API_ENDPOINT = '/run';

    const COMMAND_MAP = {
        'move_right()': 'right',
        'move_left()': 'left',
        'move_up()': 'up',
        'move_down()': 'down'
    };

    const LEVEL_SEQUENCES = {
        Level_1: ['right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'left', 'down', 'down', 'right', 'right', 'right', 'right'],
        Level_2: ['right', 'right', 'right', 'down', 'down', 'right'],
        Level_3: ['right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'down', 'down', 'right', 'right', 'right'],
        Level_4: ['right', 'up', 'right', 'right', 'right', 'right', 'down', 'down', 'right', 'right'],
        Level_5: ['right', 'right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'left', 'left', 'down', 'down', 'right', 'right', 'right', 'right', 'right', 'down', 'down', 'right'],
        Level_6: ['right', 'right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'left', 'left', 'down', 'down'],
        Level_7: ['right', 'right', 'right', 'right', 'right', 'down', 'down', 'left', 'left', 'left', 'left', 'left', 'down', 'down', 'right', 'right', 'right', 'right', 'right', 'down', 'down'],
        Level_8: ['right', 'up', 'right', 'right', 'right', 'right', 'up', 'right', 'right', 'down'],
        Level_9: ['down', 'down', 'right', 'down', 'down', 'up', 'up', 'up', 'up', 'right', 'right', 'down', 'right', 'left', 'left', 'down', 'down', 'down', 'right', 'right', 'right', 'left', 'left', 'down', 'down', 'down', 'right', 'right'],
        Level_10: ['down', 'down', 'right', 'up', 'up', 'right', 'right', 'down', 'left', 'down', 'down', 'down', 'right', 'down', 'down', 'down', 'right', 'right', 'down']
    };

    function removeComments(code) {
        return code
            .replace(/\/\/.*$/gm, '')
            .replace(/\/\*[\s\S]*?\*\//g, '');
    }

    function skipWhitespace(code, pos) {
        while (pos < code.length && /\s/.test(code[pos])) {
            pos += 1;
        }
        return pos;
    }

    function skipSemicolon(code, pos) {
        pos = skipWhitespace(code, pos);
        if (pos < code.length && code[pos] === ';') {
            return pos + 1;
        }
        return pos;
    }

    function parseFor(code, pos) {
        const forPattern = /for\s*\(\s*let\s+([A-Za-z_$][\w$]*)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\d+)\s*;\s*\1\+\+\s*\)\s*\{/y;
        forPattern.lastIndex = pos;
        const match = forPattern.exec(code);

        if (!match) {
            throw new Error('Invalid for-loop syntax at position ' + pos);
        }

        const start = parseInt(match[2], 10);
        const end = parseInt(match[3], 10);
        const repeatCount = Math.max(0, end - start);

        let cursor = forPattern.lastIndex;
        const bodyResult = parseStatements(code, cursor);
        cursor = skipWhitespace(code, bodyResult.pos);

        if (cursor >= code.length || code[cursor] !== '}') {
            throw new Error('Missing closing brace for for-loop starting at position ' + pos);
        }

        return {
            moves: repeatCount > 0 ? Array.from({ length: repeatCount }, function () { return bodyResult.moves; }).flat() : [],
            pos: cursor + 1
        };
    }

    function parseIf(code, pos) {
        const ifPattern = /if\s*\(\s*(true|false)\s*\)\s*\{/y;
        ifPattern.lastIndex = pos;
        const match = ifPattern.exec(code);

        if (!match) {
            throw new Error('Invalid if-condition syntax at position ' + pos);
        }

        const shouldRunBody = match[1] === 'true';
        let cursor = ifPattern.lastIndex;
        const bodyResult = parseStatements(code, cursor);
        cursor = skipWhitespace(code, bodyResult.pos);

        if (cursor >= code.length || code[cursor] !== '}') {
            throw new Error('Missing closing brace for if-statement starting at position ' + pos);
        }

        return {
            moves: shouldRunBody ? bodyResult.moves : [],
            pos: cursor + 1
        };
    }

    function parseFunctionDefinition(code, pos, functions) {
        const functionPattern = /function\s+([A-Za-z_$][\w$]*)\s*\(\s*\)\s*\{/y;
        functionPattern.lastIndex = pos;
        const match = functionPattern.exec(code);

        if (!match) {
            throw new Error('Invalid function syntax at position ' + pos);
        }

        const functionName = match[1];
        let cursor = functionPattern.lastIndex;
        const bodyResult = parseStatements(code, cursor, functions);
        cursor = skipWhitespace(code, bodyResult.pos);

        if (cursor >= code.length || code[cursor] !== '}') {
            throw new Error('Missing closing brace for function starting at position ' + pos);
        }

        functions[functionName] = bodyResult.moves;
        return cursor + 1;
    }

    function parseListLiteral(listBody) {
        const raw = listBody.trim();
        if (!raw) {
            return [];
        }

        return raw.split(',').map(function (part) {
            const item = part.trim();
            const match = item.match(/^['\"](right|left|up|down)['\"]$/);
            if (!match) {
                throw new Error("List items must be one of: 'right', 'left', 'up', 'down'.");
            }
            return match[1];
        });
    }

    function parseStatements(code, pos, functions, lists) {
        const availableFunctions = functions || {};
        const availableLists = lists || {};
        const moves = [];
        let cursor = pos;

        while (true) {
            cursor = skipWhitespace(code, cursor);

            if (cursor >= code.length || code[cursor] === '}') {
                break;
            }

            if (code.startsWith('for', cursor)) {
                const loopResult = parseFor(code, cursor);
                moves.push.apply(moves, loopResult.moves);
                cursor = loopResult.pos;
                continue;
            }

            if (code.startsWith('if', cursor)) {
                const conditionResult = parseIf(code, cursor);
                moves.push.apply(moves, conditionResult.moves);
                cursor = conditionResult.pos;
                continue;
            }

            if (code.startsWith('function', cursor)) {
                cursor = parseFunctionDefinition(code, cursor, availableFunctions);
                continue;
            }

            const listDeclPattern = /let\s+([A-Za-z_$][\w$]*)\s*=\s*\[([^\]]*)\]\s*;?/y;
            listDeclPattern.lastIndex = cursor;
            const listDeclMatch = listDeclPattern.exec(code);
            if (listDeclMatch) {
                const listName = listDeclMatch[1];
                const listBody = listDeclMatch[2];
                availableLists[listName] = parseListLiteral(listBody);
                cursor = listDeclPattern.lastIndex;
                continue;
            }

            const runListPattern = /run_list\s*\(\s*([A-Za-z_$][\w$]*)\s*\)\s*;?/y;
            runListPattern.lastIndex = cursor;
            const runListMatch = runListPattern.exec(code);
            if (runListMatch) {
                const listName = runListMatch[1];
                if (!Object.prototype.hasOwnProperty.call(availableLists, listName)) {
                    throw new Error("List '" + listName + "' is used before it is declared.");
                }
                moves.push.apply(moves, availableLists[listName]);
                cursor = runListPattern.lastIndex;
                continue;
            }

            const callPattern = /([A-Za-z_$][\w$]*)\s*\(\s*\)/y;
            callPattern.lastIndex = cursor;
            const callMatch = callPattern.exec(code);
            if (callMatch) {
                const functionName = callMatch[1];
                if (Object.prototype.hasOwnProperty.call(availableFunctions, functionName)) {
                    moves.push.apply(moves, availableFunctions[functionName]);
                    cursor = skipSemicolon(code, callPattern.lastIndex);
                    continue;
                }
            }

            let matched = false;
            Object.keys(COMMAND_MAP).some(function (token) {
                if (code.startsWith(token, cursor)) {
                    moves.push(COMMAND_MAP[token]);
                    cursor += token.length;
                    cursor = skipSemicolon(code, cursor);
                    matched = true;
                    return true;
                }
                return false;
            });

            if (matched) {
                continue;
            }

            throw new Error('Invalid command or syntax at position ' + cursor);
        }

        return { moves: moves, pos: cursor };
    }

    function expandAxisMoves(axis, delta) {
        if (delta === 0) {
            return [];
        }

        let token = null;
        if (axis === 'x') token = delta > 0 ? 'right' : 'left';
        if (axis === 'y') token = delta > 0 ? 'down' : 'up';
        if (!token) {
            return [];
        }

        return Array.from({ length: Math.abs(delta) }, function () { return token; });
    }

    function parseVariableMoves(code) {
        const variables = {};
        const moves = [];
        const lines = code.split(/\r?\n/);

        for (let i = 0; i < lines.length; i += 1) {
            const lineNo = i + 1;
            let line = lines[i].trim();
            if (!line) {
                continue;
            }

            if (line.endsWith(';')) {
                line = line.slice(0, -1).trim();
            }

            let match = line.match(/^let\s+([A-Za-z_$][\w$]*)\s*=\s*(-?\d+)$/);
            if (match) {
                const name = match[1];
                const newValue = parseInt(match[2], 10);
                const oldValue = Object.prototype.hasOwnProperty.call(variables, name) ? variables[name] : 0;
                variables[name] = newValue;
                moves.push.apply(moves, expandAxisMoves(name, newValue - oldValue));
                continue;
            }

            match = line.match(/^([A-Za-z_$][\w$]*)\s*=\s*([A-Za-z_$][\w$]*)\s*([+-])\s*(\d+)$/);
            if (match) {
                const target = match[1];
                const source = match[2];
                const operator = match[3];
                const amount = parseInt(match[4], 10);

                if (!Object.prototype.hasOwnProperty.call(variables, source)) {
                    throw new Error("Variable '" + source + "' is used before it is declared (line " + lineNo + ").");
                }

                const sourceValue = variables[source];
                const newValue = operator === '+' ? sourceValue + amount : sourceValue - amount;
                const oldValue = Object.prototype.hasOwnProperty.call(variables, target) ? variables[target] : 0;
                variables[target] = newValue;
                moves.push.apply(moves, expandAxisMoves(target, newValue - oldValue));
                continue;
            }

            match = line.match(/^([A-Za-z_$][\w$]*)\s*=\s*(-?\d+)$/);
            if (match) {
                const name = match[1];
                const newValue = parseInt(match[2], 10);
                const oldValue = Object.prototype.hasOwnProperty.call(variables, name) ? variables[name] : 0;
                variables[name] = newValue;
                moves.push.apply(moves, expandAxisMoves(name, newValue - oldValue));
                continue;
            }

            throw new Error('Invalid variable statement on line ' + lineNo);
        }

        return moves;
    }

    function collectLevel9Rewards(moves) {
        const rewards = new Set(['2,1', '3,4']);
        const collected = new Set();
        let x = 0;
        let y = 0;

        moves.forEach(function (move) {
            if (move === 'right') x += 1;
            if (move === 'left') x -= 1;
            if (move === 'up') y -= 1;
            if (move === 'down') y += 1;

            const key = x + ',' + y;
            if (rewards.has(key)) {
                collected.add(key);
            }
        });

        return collected.size;
    }

    function validateLevel9Path(moves) {
        const walkable = new Set([
            '0,0', '0,1', '0,2',
            '1,2', '1,3', '1,4',
            '1,1', '1,0',
            '2,0', '3,0', '3,1',
            '4,1', '2,1',
            '2,2', '2,3', '2,4',
            '3,4', '3,5', '3,6', '3,7',
            '4,7', '5,7',
            '4,4', '5,4'
        ]);

        let x = 0;
        let y = 0;

        for (let i = 0; i < moves.length; i += 1) {
            const move = moves[i];
            if (move === 'right') x += 1;
            if (move === 'left') x -= 1;
            if (move === 'up') y -= 1;
            if (move === 'down') y += 1;

            const key = x + ',' + y;
            if (!walkable.has(key)) {
                return {
                    ok: false,
                    message: 'Step ' + (i + 1) + ' (' + move + ') hits a wall. Stay on the path tiles and try again 🧱'
                };
            }
        }

        if (x !== 5 || y !== 7) {
            return {
                ok: false,
                message: 'Nice path! Now keep moving until you reach the treasure 🏁'
            };
        }

        return { ok: true };
    }

    function validatePathByTargetSequence(level, moves) {
        const target = LEVEL_SEQUENCES[level] || [];
        let x = 0;
        let y = 0;
        const walkable = new Set(['0,0']);

        target.forEach(function (move) {
            if (move === 'right') x += 1;
            if (move === 'left') x -= 1;
            if (move === 'up') y -= 1;
            if (move === 'down') y += 1;
            walkable.add(x + ',' + y);
        });

        const treasureX = x;
        const treasureY = y;

        x = 0;
        y = 0;
        for (let i = 0; i < moves.length; i += 1) {
            const move = moves[i];
            if (move === 'right') x += 1;
            if (move === 'left') x -= 1;
            if (move === 'up') y -= 1;
            if (move === 'down') y += 1;

            const key = x + ',' + y;
            if (!walkable.has(key)) {
                return {
                    ok: false,
                    message: 'Step ' + (i + 1) + ' (' + move + ') hits a wall. Stay on the path tiles and try again 🧱'
                };
            }
        }

        if (x !== treasureX || y !== treasureY) {
            return {
                ok: false,
                message: 'Nice path! Now keep moving until you reach the treasure 🏁'
            };
        }

        return { ok: true };
    }

    function validateLocally(code, level) {
        if (!code || !code.trim()) {
            return {
                success: false,
                moves: [],
                message: 'Missing code'
            };
        }

        const cleanedCode = removeComments(code);
        const targetSequence = LEVEL_SEQUENCES[level] || LEVEL_SEQUENCES.Level_1;

        try {
            if (level === 'Level_2' && !/\blet\s+[A-Za-z_$][\w$]*\s*=/.test(cleanedCode)) {
                return {
                    success: false,
                    moves: [],
                    message: 'Great start! Try using a variable with let.'
                };
            }

            if (level === 'Level_4' && !/\bif\s*\(/.test(cleanedCode)) {
                return {
                    success: false,
                    moves: [],
                    message: 'Add an if condition to make your logic smarter 🔀'
                };
            }

            if (level === 'Level_5') {
                if (!/\bfunction\s+[A-Za-z_$][\w$]*\s*\(\s*\)\s*\{/.test(cleanedCode)) {
                    return {
                        success: false,
                        moves: [],
                        message: 'Create a function first, then call it 🧩'
                    };
                }

                if (!/\b(?!move_(?:right|left|up|down)\b)[A-Za-z_$][\w$]*\s*\(\s*\)\s*;/.test(cleanedCode)) {
                    return {
                        success: false,
                        moves: [],
                        message: 'Nice function! Now call your function to run the moves ▶️'
                    };
                }
            }

            if (level === 'Level_6' && !/\blet\s+[A-Za-z_$][\w$]*\s*=\s*\[[^\]]*\]\s*;?/.test(cleanedCode)) {
                return {
                    success: false,
                    moves: [],
                    message: 'Try using a list with [ ] to store your data 📚'
                };
            }

            if (level === 'Level_6' && !/\brun_list\s*\(\s*[A-Za-z_$][\w$]*\s*\)\s*;?/.test(cleanedCode)) {
                return {
                    success: false,
                    moves: [],
                    message: 'Great list! Now use it with run_list(yourList); ▶️'
                };
            }

            if (level === 'Level_10' && (!/\bif\s*\(/.test(cleanedCode) || !/\bfor\s*\(/.test(cleanedCode))) {
                return {
                    success: false,
                    moves: [],
                    message: 'Final level tip: use both a loop and an if condition ⚠️'
                };
            }

            let moves = [];
            if (level === 'Level_2' && /\blet\b/.test(cleanedCode)) {
                moves = parseVariableMoves(cleanedCode);
            } else {
                const parsed = parseStatements(cleanedCode, 0, {}, {});
                const endPos = skipWhitespace(cleanedCode, parsed.pos);
                if (endPos !== cleanedCode.length) {
                    throw new Error('Unexpected code after parsing at position ' + endPos);
                }
                moves = parsed.moves;
            }

            if (level === 'Level_9' && collectLevel9Rewards(moves) < 2) {
                return {
                    success: false,
                    moves: [],
                    message: 'Almost there! Collect both rewards before finishing 🎯'
                };
            }

            if (level === 'Level_9') {
                const level9PathCheck = validateLevel9Path(moves);
                if (!level9PathCheck.ok) {
                    return {
                        success: false,
                        moves: [],
                        message: level9PathCheck.message
                    };
                }
            }

            if (level === 'Level_10') {
                const level10PathCheck = validatePathByTargetSequence('Level_10', moves);
                if (!level10PathCheck.ok) {
                    return {
                        success: false,
                        moves: [],
                        message: level10PathCheck.message
                    };
                }

                const shortest = LEVEL_SEQUENCES.Level_10;
                if (moves.length > shortest.length) {
                    return {
                        success: false,
                        moves: [],
                        message: 'Hint: Use all you learned and choose the shortest path to the goal 🧠'
                    };
                }

                if (!(moves.length === shortest.length && moves.every(function (m, i) { return m === shortest[i]; }))) {
                    return {
                        success: false,
                        moves: [],
                        message: 'Not the shortest correct route yet. Refine your decisions and try again ✨'
                    };
                }
            }

            const correctMoves = [];
            for (let i = 0; i < moves.length; i += 1) {
                if (i < targetSequence.length && moves[i] === targetSequence[i]) {
                    correctMoves.push(moves[i]);
                } else {
                    break;
                }
            }

            if (moves.length === targetSequence.length && moves.every(function (move, i) { return move === targetSequence[i]; })) {
                return {
                    success: true,
                    moves: moves,
                    message: 'Perfect! You reached the treasure with the correct sequence!'
                };
            }

            return {
                success: false,
                moves: correctMoves,
                message: 'Incorrect sequence.'
            };
        } catch (error) {
            return {
                success: false,
                moves: [],
                message: error.message
            };
        }
    }

    async function validate(code, level) {
        const payload = {
            code: code,
            level: level
        };

        try {
            const response = await fetch(API_ENDPOINT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            return {
                success: Boolean(data.success),
                moves: Array.isArray(data.moves) ? data.moves : [],
                message: data.message || 'Validation failed.'
            };
        } catch (error) {
            // Fallback lets levels still run if backend is unavailable.
            return validateLocally(code, level);
        }
    }

    window.GameValidator = {
        validate: validate
    };
})();
